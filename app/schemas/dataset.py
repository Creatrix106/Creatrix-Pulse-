from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field

DatasetStatus = Literal["uploading", "validating", "processing", "generating", "ready", "failed"]

CanonicalField = Literal[
    "date",
    "orderId",
    "product",
    "category",
    "region",
    "customer",
    "quantity",
    "revenue",
    "cost"
]

ColumnType = Literal["string", "number", "date", "boolean"]
ColumnMapping = Dict[str, str]

class DatasetCapabilities(BaseModel):
    customers: bool = False
    cost: bool = False
    regions: bool = False

class DatasetColumn(BaseModel):
    name: str
    type: ColumnType
    mappedTo: Optional[str] = None

class DateRange(BaseModel):
    from_date: str = Field(alias="from")
    to_date: str = Field(alias="to")

    class Config:
        allow_population_by_field_name = True

class FilterOptions(BaseModel):
    categories: List[str] = Field(default_factory=list)
    regions: List[str] = Field(default_factory=list)

class Dataset(BaseModel):
    id: str
    name: str
    fileName: str
    fileSize: int
    rowCount: int
    columnCount: int
    status: DatasetStatus
    uploadedAt: str
    dateRange: Optional[Dict[str, str]] = None
    capabilities: DatasetCapabilities
    columns: List[DatasetColumn]
    filterOptions: FilterOptions
    errorMessage: Optional[str] = None
    schema_metadata: Optional[Dict[str, Any]] = None

    class Config:
        allow_population_by_field_name = True

class ProcessingStage(BaseModel):
    id: str
    label: str
    status: Literal["pending", "active", "complete", "failed"]

class ProcessingStatus(BaseModel):
    datasetId: str
    status: DatasetStatus
    stages: List[ProcessingStage]
    progress: Optional[float] = None
    message: Optional[str] = None

class ProfiledColumn(BaseModel):
    name: str
    type: ColumnType
    missing: int
    unique: int
    sample: List[str]

class DatasetProfile(BaseModel):
    fileKind: Literal["csv", "excel"]
    headers: List[str]
    rowCount: int
    columns: List[ProfiledColumn]
    missingCells: int
    missingPercent: float
    duplicateRows: int
    previewRows: List[List[str]]

class UploadResult(BaseModel):
    datasetId: str
