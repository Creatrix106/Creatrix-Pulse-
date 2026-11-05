import json
import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, Response, Request
from fastapi.responses import JSONResponse

from app.db.database import db
from app.schemas.dataset import (
    Dataset,
    DatasetProfile,
    ProcessingStatus,
    UploadResult,
    ColumnMapping,
)
from app.schemas.auth import User
from app.api.deps import get_current_user
from app.services.dataset_service import DatasetService

router = APIRouter(prefix="/datasets", tags=["Datasets"])

@router.get("", response_model=List[Dataset])
async def list_datasets(request: Request, envelope: bool = False):
    datasets_raw = await db.list_datasets()
    result = []
    for d in datasets_raw:
        # Match Dataset schema
        result.append({
            "id": d["id"],
            "name": d["name"],
            "fileName": d["file_name"],
            "fileSize": d["file_size"],
            "rowCount": d["row_count"],
            "columnCount": d["column_count"],
            "status": d["status"],
            "uploadedAt": d["uploaded_at"],
            "dateRange": d.get("date_range"),
            "capabilities": d.get("capabilities", {}),
            "columns": d.get("columns", []),
            "filterOptions": d.get("filter_options", {"categories": [], "regions": []}),
            "errorMessage": d.get("error_message"),
            "schema_metadata": d.get("schema_metadata")
        })

    if envelope:
        return JSONResponse(content={
            "success": True,
            "data": result,
            "error": None,
            "meta": {"total": len(result)}
        })
    return JSONResponse(content=result)

@router.post("", response_model=UploadResult)
@router.post("/upload", response_model=UploadResult)
async def upload_dataset(
    file: UploadFile = File(...),
    mapping: Optional[str] = Form(None),
    replaceDatasetId: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user)
):
    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "empty_file", "message": "Uploaded file is empty."}
        )

    parsed_mapping: Dict[str, str] = {}
    if mapping:
        try:
            parsed_mapping = json.loads(mapping) if isinstance(mapping, str) else mapping
        except Exception:
            parsed_mapping = {}

    dataset_id = f"ds-{uuid.uuid4().hex[:8]}"
    clean_name = file.filename.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()

    await DatasetService.process_and_save_dataset(
        dataset_id=dataset_id,
        name=clean_name,
        filename=file.filename,
        file_bytes=content,
        user_id=current_user.id if current_user else None,
        mapping=parsed_mapping,
        replace_dataset_id=replaceDatasetId
    )

    res = {
        "datasetId": dataset_id,
        "dataset_id": dataset_id,
        "success": True,
        "data": {"datasetId": dataset_id},
        "error": None
    }
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=res)

@router.get("/{dataset_id}", response_model=Dataset)
async def get_dataset(dataset_id: str):
    d = await db.get_dataset(dataset_id)
    if not d:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist or was deleted."}
        )

    dataset_dict = {
        "id": d["id"],
        "name": d["name"],
        "fileName": d["file_name"],
        "fileSize": d["file_size"],
        "rowCount": d["row_count"],
        "columnCount": d["column_count"],
        "status": d["status"],
        "uploadedAt": d["uploaded_at"],
        "dateRange": d.get("date_range"),
        "capabilities": d.get("capabilities", {}),
        "columns": d.get("columns", []),
        "filterOptions": d.get("filter_options", {"categories": [], "regions": []}),
        "errorMessage": d.get("error_message"),
        "schema_metadata": d.get("schema_metadata"),
        "success": True,
        "data": d,
        "error": None
    }
    return JSONResponse(content=dataset_dict)

@router.delete("/{dataset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_dataset(dataset_id: str):
    exists = await db.get_dataset(dataset_id)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )
    await db.delete_dataset(dataset_id)
    await db.delete_rows(dataset_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.get("/{dataset_id}/processing", response_model=ProcessingStatus)
@router.get("/{dataset_id}/status", response_model=ProcessingStatus)
async def get_processing_status(dataset_id: str):
    try:
        status_obj = await DatasetService.get_processing_status(dataset_id)
        res = status_obj.dict()
        res.update({
            "success": True,
            "data": status_obj.dict(),
            "error": None
        })
        return JSONResponse(content=res)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )

@router.get("/{dataset_id}/preview", response_model=DatasetProfile)
async def get_dataset_preview(dataset_id: str):
    d = await db.get_dataset(dataset_id)
    if not d:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )
    meta = d.get("schema_metadata")
    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "no_metadata", "message": "Metadata not available for this dataset."}
        )
    res = dict(meta)
    res.update({
        "success": True,
        "data": meta,
        "error": None
    })
    return JSONResponse(content=res)

@router.post("/{dataset_id}/map-columns")
async def map_columns(dataset_id: str, mapping: Dict[str, str]):
    d = await db.get_dataset(dataset_id)
    if not d:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )

    # Update columns mappedTo
    existing_columns = d.get("columns", [])
    for col in existing_columns:
        cname = col.get("name")
        col["mappedTo"] = None
        for canonical, src in mapping.items():
            if src == cname:
                col["mappedTo"] = canonical
                break

    caps = {
        "customers": bool(mapping.get("customer")),
        "cost": bool(mapping.get("cost")),
        "regions": bool(mapping.get("region"))
    }

    updated = await db.update_dataset(dataset_id, {
        "columns": existing_columns,
        "capabilities": caps
    })

    return {
        "success": True,
        "message": "Column mappings updated successfully.",
        "data": updated
    }
