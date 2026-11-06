import re
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse, Response

from app.api.deps import get_current_user
from app.core.compat import model_to_dict
from app.core.exceptions import NotFoundException
from app.core.response import json_response
from app.db.database import db
from app.schemas.auth import User
from app.schemas.report import ReportConfig, ReportPreview, ReportRecord
from app.services.errors import DatasetNotFoundError
from app.services.report_service import ReportService

router = APIRouter(prefix="/datasets/{dataset_id}/reports", tags=["Reports"])

MEDIA_TYPES = {
    "csv": "text/csv",
    "json": "application/json",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pdf": "application/pdf",
}


def _safe_filename(title: str, fmt: str) -> str:
    """ASCII-only, no quotes/newlines: titles are user input and end up in a response header."""
    stem = re.sub(r"[^A-Za-z0-9._-]+", "_", title).strip("._") or "report"
    return f"{stem[:80]}.{fmt}"


@router.post("/preview", response_model=ReportPreview)
async def preview_report(dataset_id: str, config: ReportConfig):
    preview = model_to_dict(await ReportService.build_preview(dataset_id, config))
    return json_response({**preview, "success": True, "data": preview, "error": None})


@router.get("", response_model=List[ReportRecord])
async def list_reports(dataset_id: str, envelope: bool = False):
    if not await db.get_dataset(dataset_id):
        raise DatasetNotFoundError(dataset_id)
    records = [
        {
            "id": r["id"],
            "datasetId": r["dataset_id"],
            "title": r["title"],
            "format": r["format"],
            "createdAt": r["created_at"],
            "rowCount": r["row_count"],
            "sizeBytes": r["file_size_bytes"],
            "content": r.get("content"),  # the frontend downloads CSV/JSON from this field
            "downloadUrl": r.get("download_url"),
        }
        for r in await db.list_reports(dataset_id)
    ]
    if envelope:
        return json_response({"success": True, "data": records, "error": None, "meta": {"total": len(records)}})
    return json_response(records)


@router.post("", response_model=ReportRecord, status_code=status.HTTP_201_CREATED)
@router.post("/generate", response_model=ReportRecord, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_report(dataset_id: str, config: ReportConfig, current_user: User = Depends(get_current_user)):
    record = model_to_dict(await ReportService.create_report(dataset_id, config, user_id=current_user.id))
    return json_response({**record, "success": True, "data": record, "error": None}, status_code=status.HTTP_201_CREATED)


@router.get("/{report_id}/download")
async def download_report(dataset_id: str, report_id: str):
    rep = await db.get_report(report_id)
    if not rep or rep["dataset_id"] != dataset_id:
        raise NotFoundException("This report does not exist.", code="report_not_found")

    fmt = (rep.get("format") or "csv").lower()
    media_type = MEDIA_TYPES.get(fmt, "application/octet-stream")
    filename = _safe_filename(rep["title"], fmt)

    file_path = rep.get("file_path")
    if file_path and Path(file_path).exists():
        return FileResponse(path=file_path, filename=filename, media_type=media_type)
    if rep.get("content"):
        return Response(
            content=rep["content"],
            media_type=media_type,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    raise NotFoundException("Report file artifact not found on disk.", code="file_not_found")
