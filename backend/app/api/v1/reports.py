from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse, FileResponse, Response

from app.db.database import db
from app.schemas.report import ReportConfig, ReportPreview, ReportRecord
from app.schemas.auth import User
from app.api.deps import get_current_user
from app.services.report_service import ReportService

router = APIRouter(prefix="/datasets/{dataset_id}/reports", tags=["Reports"])

@router.post("/preview", response_model=ReportPreview)
async def preview_report(dataset_id: str, config: ReportConfig):
    try:
        preview = await ReportService.build_preview(dataset_id, config)
        res = preview.dict()
        res.update({"success": True, "data": preview.dict(), "error": None})
        return JSONResponse(content=res)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )

@router.get("", response_model=List[ReportRecord])
async def list_reports(dataset_id: str, envelope: bool = False):
    reports_raw = await db.list_reports(dataset_id)
    records = []
    for r in reports_raw:
        records.append({
            "id": r["id"],
            "datasetId": r["dataset_id"],
            "title": r["title"],
            "format": r["format"],
            "createdAt": r["created_at"],
            "rowCount": r["row_count"],
            "sizeBytes": r["file_size_bytes"],
            "content": r.get("content"),
            "downloadUrl": r.get("download_url")
        })

    if envelope:
        return JSONResponse(content={
            "success": True,
            "data": records,
            "error": None,
            "meta": {"total": len(records)}
        })
    return JSONResponse(content=records)

@router.post("", response_model=ReportRecord)
@router.post("/generate", response_model=ReportRecord)
async def create_report(
    dataset_id: str,
    config: ReportConfig,
    current_user: User = Depends(get_current_user)
):
    try:
        record = await ReportService.create_report(dataset_id, config, user_id=current_user.id if current_user else None)
        res = record.dict()
        res.update({"success": True, "data": record.dict(), "error": None})
        return JSONResponse(status_code=status.HTTP_201_CREATED, content=res)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )

@router.get("/{report_id}/download")
async def download_report(dataset_id: str, report_id: str):
    rep = await db.get_report(report_id)
    if not rep or rep["dataset_id"] != dataset_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "report_not_found", "message": "This report does not exist."}
        )

    file_path = rep.get("file_path")
    fmt = rep.get("format", "csv").lower()

    media_types = {
        "csv": "text/csv",
        "json": "application/json",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "pdf": "application/pdf"
    }
    media_type = media_types.get(fmt, "application/octet-stream")
    filename = f"{rep['title'].replace(' ', '_')}.{fmt}"

    if file_path and Path(file_path).exists():
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type=media_type
        )
    elif rep.get("content"):
        return Response(
            content=rep["content"],
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "file_not_found", "message": "Report file artifact not found on disk."}
        )
