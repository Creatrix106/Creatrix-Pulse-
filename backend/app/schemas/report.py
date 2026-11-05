from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

ReportFormat = Literal["csv", "json", "xlsx", "pdf"]

class ReportConfig(BaseModel):
    title: str
    metrics: List[str]
    datePreset: str
    format: ReportFormat = "csv"

class ReportSummaryItem(BaseModel):
    label: str
    value: float
    format: Literal["currency", "number", "percent"]

class ReportColumn(BaseModel):
    key: str
    label: str
    format: Literal["date", "currency", "number"]

class ReportPreview(BaseModel):
    title: str
    generatedAt: str
    period: Dict[str, str]
    summary: List[ReportSummaryItem]
    columns: List[ReportColumn]
    rows: List[Dict[str, Any]]

class ReportRecord(BaseModel):
    id: str
    datasetId: str
    title: str
    format: ReportFormat
    createdAt: str
    rowCount: int
    sizeBytes: int
    content: Optional[str] = None
    downloadUrl: Optional[str] = None
