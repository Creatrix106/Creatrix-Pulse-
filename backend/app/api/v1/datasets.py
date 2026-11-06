import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status

from app.api.deps import get_current_user
from app.config import settings
from app.core.compat import model_to_dict
from app.core.exceptions import AppException, BadRequestException, NotFoundException
from app.core.response import json_response
from app.db.database import db
from app.schemas.auth import User
from app.schemas.dataset import Dataset, DatasetProfile, ProcessingStatus, UploadResult
from app.services.dataset_service import DatasetService
from app.services.errors import DatasetNotFoundError, IngestError

logger = logging.getLogger("creatrix.datasets")

router = APIRouter(prefix="/datasets", tags=["Datasets"])

ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def dataset_payload(d: Dict[str, Any]) -> Dict[str, Any]:
    """DB row -> the `Dataset` shape the frontend declares (src/types/dataset.ts).
    Optional fields are omitted rather than sent as null, matching `mappedTo?` / `errorMessage?`."""
    columns = []
    for c in d.get("columns") or []:
        col = {"name": c.get("name"), "type": c.get("type")}
        if c.get("mappedTo"):
            col["mappedTo"] = c["mappedTo"]
        columns.append(col)

    caps = d.get("capabilities") or {}
    payload: Dict[str, Any] = {
        "id": d["id"],
        "name": d["name"],
        "fileName": d["file_name"],
        "fileSize": d["file_size"],
        "rowCount": d["row_count"],
        "columnCount": d["column_count"],
        "status": d["status"],
        "uploadedAt": d["uploaded_at"],
        "dateRange": d.get("date_range"),
        "capabilities": {
            "customers": bool(caps.get("customers")),
            "cost": bool(caps.get("cost")),
            "regions": bool(caps.get("regions")),
        },
        "columns": columns,
        "filterOptions": d.get("filter_options") or {"categories": [], "regions": []},
    }
    if d.get("error_message"):
        payload["errorMessage"] = d["error_message"]
    return payload


@router.get("", response_model=list[Dataset])
async def list_datasets(envelope: bool = False):
    result = [dataset_payload(d) for d in await db.list_datasets()]
    if envelope:
        return json_response({"success": True, "data": result, "error": None, "meta": {"total": len(result)}})
    return json_response(result)


@router.post("", response_model=UploadResult, status_code=status.HTTP_201_CREATED)
@router.post("/upload", response_model=UploadResult, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def upload_dataset(
    file: UploadFile = File(...),
    mapping: Optional[str] = Form(None),
    replaceDatasetId: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    filename = Path(file.filename or "upload.csv").name
    if Path(filename).suffix.lower() not in ALLOWED_EXTENSIONS:
        raise AppException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "unsupported_file_type",
            "Unsupported file type. Please upload a .csv, .xlsx or .xls file.",
        )

    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if not content:
        raise BadRequestException("Uploaded file is empty.", code="empty_file")
    if len(content) > max_bytes:
        raise AppException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "file_too_large",
            f"This file is larger than {settings.MAX_FILE_SIZE_MB} MB.",
        )

    parsed_mapping: Dict[str, Any] = {}
    if mapping:
        try:
            parsed_mapping = json.loads(mapping)
            if not isinstance(parsed_mapping, dict):
                raise ValueError("mapping must be an object")
        except ValueError:
            raise BadRequestException(
                "The column mapping is not valid JSON (expected an object like {\"date\": \"Order Date\"}).",
                code="invalid_mapping",
            )

    dataset_id = f"ds-{uuid.uuid4().hex[:8]}"
    clean_name = Path(filename).stem.replace("_", " ").replace("-", " ").title()

    try:
        await DatasetService.process_and_save_dataset(
            dataset_id=dataset_id,
            name=clean_name,
            filename=filename,
            file_bytes=content,
            user_id=current_user.id if current_user else None,
            mapping=parsed_mapping,
            replace_dataset_id=replaceDatasetId,
        )
    except IngestError as exc:
        # 422 + {code, message}: the frontend shows `message` in its "Upload failed" toast.
        raise AppException(status.HTTP_422_UNPROCESSABLE_ENTITY, exc.code, exc.message)

    return json_response(
        {
            "datasetId": dataset_id,
            "dataset_id": dataset_id,
            "success": True,
            "data": {"datasetId": dataset_id},
            "error": None,
        },
        status_code=status.HTTP_201_CREATED,
    )


async def _require_dataset(dataset_id: str) -> Dict[str, Any]:
    d = await db.get_dataset(dataset_id)
    if not d:
        raise DatasetNotFoundError(dataset_id)
    return d


@router.get("/{dataset_id}", response_model=Dataset)
async def get_dataset(dataset_id: str):
    d = await _require_dataset(dataset_id)
    payload = dataset_payload(d)
    return json_response({**payload, "success": True, "data": payload, "error": None})


@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(dataset_id: str):
    await _require_dataset(dataset_id)
    await db.delete_dataset(dataset_id)  # rows and reports go with it (ON DELETE CASCADE)
    DatasetService.purge_files(dataset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{dataset_id}/processing", response_model=ProcessingStatus)
@router.get("/{dataset_id}/status", response_model=ProcessingStatus, include_in_schema=False)
async def get_processing_status(dataset_id: str):
    status_obj = model_to_dict(await DatasetService.get_processing_status(dataset_id))
    return json_response({**status_obj, "success": True, "data": status_obj, "error": None})


@router.get("/{dataset_id}/preview", response_model=DatasetProfile)
async def get_dataset_preview(dataset_id: str):
    d = await _require_dataset(dataset_id)
    meta = d.get("schema_metadata")
    if not meta:
        raise NotFoundException("Metadata not available for this dataset.", code="no_metadata")
    return json_response({**meta, "success": True, "data": meta, "error": None})


@router.post("/{dataset_id}/map-columns")
async def map_columns(dataset_id: str, mapping: Dict[str, str]):
    """Re-ingest the stored original file with a new `{canonicalField: sourceColumn}` mapping."""
    await _require_dataset(dataset_id)
    try:
        updated = await DatasetService.remap_dataset(dataset_id, mapping)
    except IngestError as exc:
        raise AppException(status.HTTP_422_UNPROCESSABLE_ENTITY, exc.code, exc.message)
    return json_response({
        "success": True,
        "message": "Column mappings updated successfully.",
        "data": dataset_payload(updated),
    })
