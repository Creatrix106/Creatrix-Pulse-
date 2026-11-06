import asyncio
import datetime
import logging
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from app.config import settings
from app.core.compat import model_to_dict
from app.db.database import db
from app.schemas.dataset import (
    DatasetProfile,
    ProcessingStage,
    ProcessingStatus,
    ProfiledColumn,
)
from app.services import ingest
from app.services.errors import DatasetNotFoundError, IngestError

logger = logging.getLogger("creatrix.datasets")

DATE_RE = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}([T ].*)?$|^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$")
NUMBER_RE = re.compile(r"^[-+]?[₹$€£]?\s?[\d,]*\.?\d+$")

PROCESSING_STAGES = [
    {"id": "upload", "label": "Uploading dataset"},
    {"id": "validate", "label": "Validating columns"},
    {"id": "process", "label": "Processing records"},
    {"id": "analytics", "label": "Generating analytics"},
    {"id": "prepare", "label": "Preparing dashboard"},
]

# Columns of the dataset_rows table (raw_payload is kept in SQLite only, never in parquet).
ROW_COLUMNS = [
    "id", "dataset_id", "order_id", "transaction_date", "product_id", "product_name",
    "product_category", "region", "customer_identifier", "quantity", "unit_price",
    "revenue", "cost", "raw_payload",
]


def normalise_header(header: str) -> str:
    return ingest.normalise_header(header)


def infer_column_type(values: List[Any]) -> str:
    cleaned = [str(v).strip() for v in values if pd.notna(v) and str(v).strip() != ""]
    if not cleaned:
        return "string"
    total = len(cleaned)
    if sum(1 for v in cleaned if DATE_RE.match(v)) / total > 0.85:
        return "date"
    if sum(1 for v in cleaned if NUMBER_RE.match(v)) / total > 0.85:
        return "number"
    if sum(1 for v in cleaned if v.lower() in ["true", "false", "yes", "no", "1", "0"]) / total > 0.9:
        return "boolean"
    return "string"


def _rows_for_sqlite(rows: pd.DataFrame) -> List[Dict[str, Any]]:
    """Python-native values only (sqlite3 cannot bind numpy scalars); NaN -> NULL."""
    clean = rows[ROW_COLUMNS].astype(object).where(rows[ROW_COLUMNS].notna(), None)
    return clean.to_dict("records")


class DatasetService:
    # ---------------------------------------------------------------- profiling

    @staticmethod
    def profile_dataframe(df: pd.DataFrame, file_kind: str = "csv") -> DatasetProfile:
        headers = [str(c) for c in df.columns]
        row_count = len(df)
        columns: List[ProfiledColumn] = []
        total_missing = 0

        for col in df.columns:
            vals = df[col].tolist()
            non_nulls = [v for v in vals if pd.notna(v) and str(v).strip() != ""]
            missing = row_count - len(non_nulls)
            total_missing += missing
            columns.append(
                ProfiledColumn(
                    name=str(col),
                    type=infer_column_type(vals),
                    missing=missing,
                    unique=len(set(non_nulls)),
                    sample=[str(v) for v in non_nulls[:3]],
                )
            )

        total_cells = max(1, row_count * len(headers))
        preview_df = df.head(settings.PREVIEW_ROW_COUNT).fillna("")
        return DatasetProfile(
            fileKind="excel" if file_kind in ["xlsx", "excel"] else "csv",
            headers=headers,
            rowCount=row_count,
            columns=columns,
            missingCells=total_missing,
            missingPercent=round((total_missing / total_cells) * 100.0, 2),
            duplicateRows=int(df.astype(str).duplicated().sum()),
            previewRows=[[str(val) for val in row] for row in preview_df.values],
        )

    @staticmethod
    def auto_suggest_mapping(headers: List[str]) -> Dict[str, str]:
        return ingest.suggest_mapping(headers)

    @staticmethod
    def parse_file_to_dataframe(file_bytes: bytes, filename: str) -> Tuple[pd.DataFrame, str]:
        return ingest.read_table(file_bytes, filename)

    # ---------------------------------------------------------------- files

    @staticmethod
    def purge_files(dataset_id: str) -> None:
        """Remove the parquet cache and the stored original upload of a dataset."""
        try:
            (settings.PARQUET_DIR / f"{dataset_id}.parquet").unlink(missing_ok=True)
            for p in settings.UPLOAD_DIR.glob(f"{dataset_id}_*"):
                p.unlink(missing_ok=True)
        except OSError:
            logger.warning("Could not remove files for dataset %s", dataset_id, exc_info=True)

    @staticmethod
    def find_original_upload(dataset_id: str) -> Optional[Any]:
        matches = sorted(settings.UPLOAD_DIR.glob(f"{dataset_id}_*"))
        return matches[0] if matches else None

    # ---------------------------------------------------------------- ingestion

    @staticmethod
    def _ingest_sync(
        dataset_id: str,
        filename: str,
        file_bytes: bytes,
        mapping: Optional[Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], pd.DataFrame]:
        """CPU-bound work (parse, validate, normalise, write parquet). Runs in a worker thread
        so a large upload does not freeze every other request."""
        df, kind = ingest.read_table(file_bytes, filename)
        profile = DatasetService.profile_dataframe(df, file_kind=kind)
        effective = ingest.resolve_mapping(list(df.columns), mapping)
        rows, meta = ingest.normalise(df, effective, dataset_id)

        inverse = {src: field for field, src in effective.items()}
        columns = [
            {"name": c.name, "type": c.type, "mappedTo": inverse.get(c.name)}
            for c in profile.columns
        ]
        caps = {
            "customers": bool(rows["customer_identifier"].notna().any()),
            "cost": bool(rows["cost"].notna().any()),
            "regions": bool(rows["region"].notna().any()),
        }
        dates = rows["transaction_date"]
        schema_metadata = model_to_dict(profile)
        schema_metadata["ingest"] = meta

        record = {
            "id": dataset_id,
            "name": "",  # filled by caller
            "file_name": filename,
            "file_size": len(file_bytes),
            "status": "ready",
            "row_count": len(rows),
            "column_count": len(columns),
            "capabilities": caps,
            "columns": columns,
            "date_range": {"from": str(dates.min()), "to": str(dates.max())},
            "filter_options": {
                "categories": sorted(rows["product_category"].dropna().unique().tolist()),
                "regions": sorted(rows["region"].dropna().unique().tolist()),
            },
            "error_message": None,
            "schema_metadata": schema_metadata,
            "uploaded_at": datetime.datetime.utcnow().isoformat() + "Z",
            "started_at": int(time.time() * 1000),
        }

        (settings.UPLOAD_DIR / f"{dataset_id}_{re.sub(r'[^A-Za-z0-9._-]+', '_', filename)}").write_bytes(file_bytes)
        rows.drop(columns=["raw_payload"]).to_parquet(settings.PARQUET_DIR / f"{dataset_id}.parquet", index=False)
        return record, rows

    @classmethod
    async def process_and_save_dataset(
        cls,
        dataset_id: str,
        name: str,
        filename: str,
        file_bytes: bytes,
        user_id: Optional[str] = None,
        mapping: Optional[Dict[str, str]] = None,
        replace_dataset_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            record, rows = await asyncio.to_thread(cls._ingest_sync, dataset_id, filename, file_bytes, mapping)
        except Exception:
            cls.purge_files(dataset_id)
            raise

        record["name"] = name or filename.rsplit(".", 1)[0].replace("_", " ").title()
        record["user_id"] = user_id

        created = False
        try:
            await db.create_dataset(record)
            created = True
            await db.insert_rows(dataset_id, await asyncio.to_thread(_rows_for_sqlite, rows))
        except Exception:
            if created:  # never leave a half-written "ready" dataset behind (but never touch one we did not create)
                await db.delete_dataset(dataset_id)
                cls.purge_files(dataset_id)
            raise

        # Only now that the new dataset is safely stored do we remove the one it replaces.
        if replace_dataset_id and replace_dataset_id != dataset_id:
            await db.delete_dataset(replace_dataset_id)
            cls.purge_files(replace_dataset_id)
        return record

    @classmethod
    async def remap_dataset(cls, dataset_id: str, mapping: Dict[str, str]) -> Dict[str, Any]:
        """Re-run ingestion of the stored original file with a new column mapping."""
        existing = await db.get_dataset(dataset_id)
        if not existing:
            raise DatasetNotFoundError(dataset_id)
        original = cls.find_original_upload(dataset_id)
        if original is None:
            raise IngestError(
                "The original file for this dataset is not available, so its columns cannot be re-mapped. "
                "Upload the file again instead.",
                "source_unavailable",
            )
        file_bytes = original.read_bytes()
        record, rows = await asyncio.to_thread(cls._ingest_sync, dataset_id, existing["file_name"], file_bytes, mapping)
        await db.delete_rows(dataset_id)
        await db.insert_rows(dataset_id, await asyncio.to_thread(_rows_for_sqlite, rows))
        updates = {k: record[k] for k in (
            "row_count", "column_count", "capabilities", "columns", "date_range",
            "filter_options", "schema_metadata", "status", "error_message",
        )}
        return await db.update_dataset(dataset_id, updates)

    # ---------------------------------------------------------------- status

    @classmethod
    async def get_processing_status(cls, dataset_id: str) -> ProcessingStatus:
        dataset = await db.get_dataset(dataset_id)
        if not dataset:
            raise DatasetNotFoundError(dataset_id)
        status = dataset.get("status", "ready")

        if status == "failed":
            stages = [
                ProcessingStage(id="upload", label=PROCESSING_STAGES[0]["label"], status="complete"),
                ProcessingStage(id="validate", label=PROCESSING_STAGES[1]["label"], status="failed"),
                ProcessingStage(id="process", label=PROCESSING_STAGES[2]["label"], status="pending"),
                ProcessingStage(id="analytics", label=PROCESSING_STAGES[3]["label"], status="pending"),
                ProcessingStage(id="prepare", label=PROCESSING_STAGES[4]["label"], status="pending"),
            ]
            return ProcessingStatus(datasetId=dataset_id, status="failed", stages=stages, progress=None,
                                    message=dataset.get("error_message"))

        done = status == "ready"
        stages = [
            ProcessingStage(id=s["id"], label=s["label"], status="complete" if done else "pending")
            for s in PROCESSING_STAGES
        ]
        # The frontend never invents progress, so report a real number only when we have one.
        return ProcessingStatus(datasetId=dataset_id, status=status, stages=stages,
                                progress=100.0 if done else None, message=None)
