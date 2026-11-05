import io
import re
import os
import json
import time
import uuid
import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import numpy as np

from app.config import settings
from app.db.database import db
from app.schemas.dataset import (
    DatasetProfile,
    ProfiledColumn,
    DatasetColumn,
    DatasetCapabilities,
    ProcessingStatus,
    ProcessingStage,
)

DATE_RE = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}([T ].*)?$|^\d{1,2}[/-]\d{1,2}[/-]\d{2,4}$")
NUMBER_RE = re.compile(r"^[-+]?[₹$€£]?\s?[\d,]*\.?\d+$")

PROCESSING_STAGES = [
    {"id": "upload", "label": "Uploading dataset"},
    {"id": "validate", "label": "Validating columns"},
    {"id": "process", "label": "Processing records"},
    {"id": "analytics", "label": "Generating analytics"},
    {"id": "prepare", "label": "Preparing dashboard"},
]

def normalise_header(header: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(header).lower()).strip()

def infer_column_type(values: List[Any]) -> str:
    cleaned = [str(v).strip() for v in values if pd.notna(v) and str(v).strip() != ""]
    if not cleaned:
        return "string"
    total = len(cleaned)
    date_matches = sum(1 for v in cleaned if DATE_RE.match(v))
    if date_matches / total > 0.85:
        return "date"
    num_matches = sum(1 for v in cleaned if NUMBER_RE.match(v))
    if num_matches / total > 0.85:
        return "number"
    bool_matches = sum(1 for v in cleaned if v.lower() in ["true", "false", "yes", "no", "1", "0"])
    if bool_matches / total > 0.9:
        return "boolean"
    return "string"

class DatasetService:
    @staticmethod
    def profile_dataframe(df: pd.DataFrame, file_kind: str = "csv") -> DatasetProfile:
        headers = [str(c).strip() or f"Column {i+1}" for i, c in enumerate(df.columns)]
        row_count = len(df)
        columns: List[ProfiledColumn] = []
        total_missing = 0

        for col in df.columns:
            vals = df[col].tolist()
            non_nulls = [v for v in vals if pd.notna(v) and str(v).strip() != ""]
            missing = row_count - len(non_nulls)
            total_missing += missing
            unique_count = len(set(non_nulls))
            sample = [str(v) for v in non_nulls[:3]]
            col_type = infer_column_type(vals)
            columns.append(
                ProfiledColumn(
                    name=str(col),
                    type=col_type,
                    missing=missing,
                    unique=unique_count,
                    sample=sample
                )
            )

        total_cells = max(1, row_count * len(headers))
        missing_percent = (total_missing / total_cells) * 100.0
        duplicate_rows = int(df.duplicated().sum())
        
        # Preview rows (top N)
        preview_df = df.head(settings.PREVIEW_ROW_COUNT).fillna("")
        preview_rows = [[str(val) for val in row] for row in preview_df.values]

        return DatasetProfile(
            fileKind="excel" if file_kind in ["xlsx", "excel"] else "csv",
            headers=headers,
            rowCount=row_count,
            columns=columns,
            missingCells=total_missing,
            missingPercent=round(missing_percent, 2),
            duplicateRows=duplicate_rows,
            previewRows=preview_rows
        )

    @staticmethod
    def auto_suggest_mapping(headers: List[str]) -> Dict[str, str]:
        canonical_aliases = {
            "date": ["date", "order date", "orderdate", "invoice date", "transaction date", "day", "created at"],
            "product": ["product", "product name", "item", "item name", "sku", "title"],
            "revenue": ["revenue", "sales", "amount", "total", "total sales", "net sales", "order value", "line total"],
            "quantity": ["quantity", "qty", "units", "units sold"],
            "orderId": ["order id", "orderid", "order no", "invoice", "invoice no", "transaction id"],
            "category": ["category", "product category", "department", "type"],
            "region": ["region", "state", "zone", "area", "city", "location"],
            "customer": ["customer", "customer id", "customerid", "client", "buyer", "customer name"],
            "cost": ["cost", "cogs", "total cost", "expense", "unit cost"],
        }
        mapping: Dict[str, str] = {}
        normalised_headers = {h: normalise_header(h) for h in headers}

        for canonical, aliases in canonical_aliases.items():
            for raw_h, norm_h in normalised_headers.items():
                if norm_h in aliases and canonical not in mapping:
                    mapping[canonical] = raw_h
                    break
        return mapping

    @staticmethod
    def parse_file_to_dataframe(file_bytes: bytes, filename: str) -> Tuple[pd.DataFrame, str]:
        ext = filename.lower().split(".")[-1]
        if ext in ["xlsx", "xls"]:
            df = pd.read_excel(io.BytesIO(file_bytes))
            kind = "excel"
        else:
            try:
                df = pd.read_csv(io.BytesIO(file_bytes))
            except Exception:
                df = pd.read_csv(io.BytesIO(file_bytes), encoding="latin1")
            kind = "csv"
        return df, kind

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
        # Save raw file
        raw_path = settings.UPLOAD_DIR / f"{dataset_id}_{filename}"
        with open(raw_path, "wb") as f:
            f.write(file_bytes)

        df, kind = cls.parse_file_to_dataframe(file_bytes, filename)
        profile = cls.profile_dataframe(df, file_kind=kind)

        # Merge or generate column mapping
        effective_mapping = cls.auto_suggest_mapping(profile.headers)
        if mapping:
            effective_mapping.update(mapping)

        # Build columns list with mappedTo
        columns: List[Dict[str, Any]] = []
        for col_prof in profile.columns:
            mapped_to = None
            for can_field, src_col in effective_mapping.items():
                if src_col == col_prof.name:
                    mapped_to = can_field
                    break
            columns.append({
                "name": col_prof.name,
                "type": col_prof.type,
                "mappedTo": mapped_to
            })

        # Capabilities
        caps = {
            "customers": bool(effective_mapping.get("customer")),
            "cost": bool(effective_mapping.get("cost")),
            "regions": bool(effective_mapping.get("region"))
        }

        # Normalize rows into standard format
        normalized_rows: List[Dict[str, Any]] = []
        date_col = effective_mapping.get("date")
        prod_col = effective_mapping.get("product")
        rev_col = effective_mapping.get("revenue")
        qty_col = effective_mapping.get("quantity")
        ord_col = effective_mapping.get("orderId")
        cat_col = effective_mapping.get("category")
        reg_col = effective_mapping.get("region")
        cust_col = effective_mapping.get("customer")
        cost_col = effective_mapping.get("cost")

        all_dates = []
        all_categories = set()
        all_regions = set()

        for idx, row in df.iterrows():
            # Date parsing
            raw_date = row.get(date_col) if date_col else None
            try:
                parsed_date = pd.to_datetime(raw_date).strftime("%Y-%m-%d")
            except Exception:
                parsed_date = "2026-01-01"

            all_dates.append(parsed_date)

            # Revenue
            raw_rev = row.get(rev_col) if rev_col else 0.0
            try:
                rev = float(re.sub(r"[^\d.-]", "", str(raw_rev))) if pd.notna(raw_rev) else 0.0
            except Exception:
                rev = 0.0

            # Quantity
            raw_qty = row.get(qty_col) if qty_col else 1
            try:
                qty = int(float(re.sub(r"[^\d.-]", "", str(raw_qty)))) if pd.notna(raw_qty) else 1
            except Exception:
                qty = 1

            # Cost
            cost = None
            if cost_col and pd.notna(row.get(cost_col)):
                try:
                    cost = float(re.sub(r"[^\d.-]", "", str(row[cost_col])))
                except Exception:
                    cost = None

            # Category & Region
            cat = str(row.get(cat_col)).strip() if cat_col and pd.notna(row.get(cat_col)) else "General"
            reg = str(row.get(reg_col)).strip() if reg_col and pd.notna(row.get(reg_col)) else None
            if cat:
                all_categories.add(cat)
            if reg:
                all_regions.add(reg)

            # Customer & Product & Order
            prod = str(row.get(prod_col)).strip() if prod_col and pd.notna(row.get(prod_col)) else f"Item-{idx+1}"
            ord_id = str(row.get(ord_col)).strip() if ord_col and pd.notna(row.get(ord_col)) else f"ORD-{idx+1000}"
            cust_id = str(row.get(cust_col)).strip() if cust_col and pd.notna(row.get(cust_col)) else None

            # Unit Price
            unit_price = rev / qty if qty > 0 else rev

            # Raw unmapped custom payload
            raw_payload = {str(k): (None if pd.isna(v) else v) for k, v in row.to_dict().items()}

            normalized_rows.append({
                "id": f"{dataset_id}-row-{idx+1}",
                "dataset_id": dataset_id,
                "order_id": ord_id,
                "transaction_date": parsed_date,
                "product_id": f"P-{normalise_header(prod).replace(' ', '-')[:20]}",
                "product_name": prod,
                "product_category": cat,
                "region": reg,
                "customer_identifier": cust_id,
                "quantity": qty,
                "unit_price": unit_price,
                "revenue": rev,
                "cost": cost,
                "raw_payload": json.dumps(raw_payload)
            })

        # Date range
        all_dates.sort()
        date_range = {"from": all_dates[0], "to": all_dates[-1]} if all_dates else None

        filter_options = {
            "categories": sorted(list(all_categories)),
            "regions": sorted(list(all_regions))
        }

        # Save Parquet for fast analytics
        norm_df = pd.DataFrame(normalized_rows)
        parquet_path = settings.PARQUET_DIR / f"{dataset_id}.parquet"
        norm_df.to_parquet(parquet_path, index=False)

        # Insert dataset metadata
        clean_name = name or filename.rsplit(".", 1)[0].replace("_", " ").title()
        dataset_record = {
            "id": dataset_id,
            "user_id": user_id,
            "name": clean_name,
            "file_name": filename,
            "file_size": len(file_bytes),
            "status": "ready",
            "row_count": len(normalized_rows),
            "column_count": len(columns),
            "capabilities": caps,
            "columns": columns,
            "date_range": date_range,
            "filter_options": filter_options,
            "error_message": None,
            "schema_metadata": profile.dict(),
            "uploaded_at": datetime.datetime.utcnow().isoformat() + "Z",
            "started_at": int(time.time() * 1000)
        }

        if replace_dataset_id:
            await db.delete_dataset(replace_dataset_id)
            await db.delete_rows(replace_dataset_id)

        await db.create_dataset(dataset_record)
        await db.insert_rows(dataset_id, normalized_rows)
        return dataset_record

    @classmethod
    async def get_processing_status(cls, dataset_id: str) -> ProcessingStatus:
        dataset = await db.get_dataset(dataset_id)
        if not dataset:
            raise KeyError("Dataset not found")
        status = dataset.get("status", "ready")
        err = dataset.get("error_message")

        if status == "failed":
            stages = [
                ProcessingStage(id="upload", label="Uploading dataset", status="complete"),
                ProcessingStage(id="validate", label="Validating columns", status="failed"),
                ProcessingStage(id="process", label="Processing records", status="pending"),
                ProcessingStage(id="analytics", label="Generating analytics", status="pending"),
                ProcessingStage(id="prepare", label="Preparing dashboard", status="pending"),
            ]
            return ProcessingStatus(
                datasetId=dataset_id,
                status="failed",
                stages=stages,
                progress=None,
                message=err
            )

        stages = [
            ProcessingStage(id="upload", label="Uploading dataset", status="complete"),
            ProcessingStage(id="validate", label="Validating columns", status="complete"),
            ProcessingStage(id="process", label="Processing records", status="complete"),
            ProcessingStage(id="analytics", label="Generating analytics", status="complete"),
            ProcessingStage(id="prepare", label="Preparing dashboard", status="complete"),
        ]
        return ProcessingStatus(
            datasetId=dataset_id,
            status=status,
            stages=stages,
            progress=100.0 if status == "ready" else 50.0,
            message=None
        )
