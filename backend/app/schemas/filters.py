from typing import List, Optional, Literal
from pydantic import BaseModel, Field

DatePreset = Literal["all", "last_30d", "last_90d", "last_180d", "ytd", "custom"]
ComparisonMode = Literal["none", "previous_period"]
GroupBy = Literal["day", "week", "month"]
MetricKey = Literal["revenue", "orders", "units", "aov", "cost", "profit"]

class AnalyticsFilters(BaseModel):
    date_preset: DatePreset = Field(default="all", alias="datePreset")
    date_from: Optional[str] = Field(default=None, alias="dateFrom")
    date_to: Optional[str] = Field(default=None, alias="dateTo")
    comparison: ComparisonMode = Field(default="none")
    group_by: GroupBy = Field(default="month", alias="groupBy")
    categories: List[str] = Field(default_factory=list)
    regions: List[str] = Field(default_factory=list)
    product_id: Optional[str] = Field(default=None, alias="productId")
    customer_id: Optional[str] = Field(default=None, alias="customerId")
    limit: Optional[int] = 50
    offset: Optional[int] = 0
    sort_by: Optional[str] = Field(default=None, alias="sortBy")

    class Config:
        allow_population_by_field_name = True
