from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel, Field
from app.schemas.insight import Insight

KpiFormat = Literal["currency", "number", "percent"]

class Kpi(BaseModel):
    id: str
    label: str
    value: float
    format: KpiFormat
    change: Optional[float] = None
    inverse: Optional[bool] = None
    hint: Optional[str] = None

class TimeSeriesPoint(BaseModel):
    date: str
    revenue: float
    orders: int
    units: int
    aov: float
    cost: Optional[float] = None
    profit: Optional[float] = None
    margin: Optional[float] = None

class BreakdownItem(BaseModel):
    name: str
    value: float
    share: float
    change: Optional[float] = None
    secondary: Optional[float] = None

class ProductPerformance(BaseModel):
    id: str
    name: str
    category: str
    revenue: float
    units: int
    orders: int
    share: float
    change: Optional[float] = None
    margin: Optional[float] = None

class DatePeriod(BaseModel):
    from_date: str = Field(alias="from")
    to_date: str = Field(alias="to")

    class Config:
        allow_population_by_field_name = True

class OverviewData(BaseModel):
    period: Dict[str, str]
    kpis: List[Kpi]
    revenueTrend: List[TimeSeriesPoint]
    topProducts: List[ProductPerformance]
    categories: List[BreakdownItem]
    regions: List[BreakdownItem]
    insights: List[Insight]

class CategoryTrendPoint(BaseModel):
    date: str
    values: Dict[str, float]

class SalesData(BaseModel):
    kpis: List[Kpi]
    trend: List[TimeSeriesPoint]
    previousTrend: Optional[List[TimeSeriesPoint]] = None
    categories: List[BreakdownItem]
    regions: List[BreakdownItem]
    categoryNames: List[str]
    categoryTrend: List[CategoryTrendPoint]

class ProductsData(BaseModel):
    top: List[ProductPerformance]
    low: List[ProductPerformance]
    all: List[ProductPerformance]
    categories: List[BreakdownItem]

class CustomerSegment(BaseModel):
    name: str
    description: str
    customers: int
    revenue: float
    share: float

class NewVsReturningPoint(BaseModel):
    date: str
    newCustomers: int
    returningCustomers: int

class FrequencyBin(BaseModel):
    label: str
    count: int

class CustomersData(BaseModel):
    kpis: List[Kpi]
    newVsReturning: List[NewVsReturningPoint]
    distribution: List[BreakdownItem]
    frequency: List[FrequencyBin]
    segments: List[CustomerSegment]

class CustomersResponse(BaseModel):
    available: bool
    data: Optional[CustomersData] = None
    reason: Optional[str] = None

class FinanceData(BaseModel):
    kpis: List[Kpi]
    trend: List[TimeSeriesPoint]
    categoryMargins: List[BreakdownItem]

class FinanceResponse(BaseModel):
    available: bool
    data: Optional[FinanceData] = None
    reason: Optional[str] = None

class ExplorerColumn(BaseModel):
    key: str
    label: str
    type: Literal["string", "number", "date"]
    format: Optional[Literal["currency"]] = None

class ExplorerData(BaseModel):
    columns: List[ExplorerColumn]
    rows: List[Dict[str, Any]]
    total: Optional[int] = None
