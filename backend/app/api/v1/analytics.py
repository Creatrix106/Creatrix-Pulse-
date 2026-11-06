import re
from typing import List, Optional

from fastapi import APIRouter, Depends, Query

from app.config import settings
from app.core.compat import model_to_dict
from app.core.exceptions import BadRequestException
from app.core.response import json_response
from app.schemas.analytics import (
    CustomersResponse,
    ExplorerData,
    FinanceResponse,
    OverviewData,
    ProductsData,
    SalesData,
)
from app.schemas.filters import AnalyticsFilters, ComparisonMode, DatePreset, GroupBy
from app.schemas.insight import Insight
from app.services.analytics_service import AnalyticsService
from app.services.insights_service import InsightsService

router = APIRouter(prefix="/datasets/{dataset_id}", tags=["Analytics"])

ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _split(values: Optional[List[str]]) -> List[str]:
    """Accept both repeated params (?categories=a&categories=b) and comma-separated ones."""
    out: List[str] = []
    for v in values or []:
        out.extend(item.strip() for item in v.split(",") if item.strip())
    return out


def get_filters(
    datePreset: DatePreset = Query("all"),
    dateFrom: Optional[str] = Query(None),
    dateTo: Optional[str] = Query(None),
    comparison: ComparisonMode = Query("none"),
    groupBy: GroupBy = Query("month"),
    categories: Optional[List[str]] = Query(None),
    regions: Optional[List[str]] = Query(None),
    productId: Optional[str] = Query(None),
    customerId: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    offset: Optional[int] = Query(0),
    sortBy: Optional[str] = Query(None),
) -> AnalyticsFilters:
    for name, value in (("dateFrom", dateFrom), ("dateTo", dateTo)):
        if value and not ISO_DATE.match(value):
            raise BadRequestException(f"'{name}' must be an ISO date (YYYY-MM-DD).", code="invalid_date")

    return AnalyticsFilters(
        datePreset=datePreset,
        dateFrom=dateFrom,
        dateTo=dateTo,
        comparison=comparison,
        groupBy=groupBy,
        categories=_split(categories),
        regions=_split(regions),
        productId=productId,
        customerId=customerId,
        limit=limit,
        offset=offset,
        sortBy=sortBy,
    )


def _wrap(data) -> dict:
    d = model_to_dict(data)
    return {**d, "success": True, "data": d, "error": None}


@router.get("/analytics/overview", response_model=OverviewData)
async def get_overview(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    return json_response(_wrap(await AnalyticsService.get_overview(dataset_id, filters)))


@router.get("/analytics/sales", response_model=SalesData)
async def get_sales(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    return json_response(_wrap(await AnalyticsService.get_sales(dataset_id, filters)))


@router.get("/analytics/products", response_model=ProductsData)
async def get_products(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    return json_response(_wrap(await AnalyticsService.get_products(dataset_id, filters)))


@router.get("/analytics/customers", response_model=CustomersResponse)
async def get_customers(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    # `{available, data | reason}` is the frontend's Capability<T>; `data` must stay the payload itself.
    d = model_to_dict(await AnalyticsService.get_customers(dataset_id, filters))
    return json_response({**d, "success": True, "error": None})


@router.get("/analytics/finance", response_model=FinanceResponse)
async def get_finance(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    d = model_to_dict(await AnalyticsService.get_finance(dataset_id, filters))
    return json_response({**d, "success": True, "error": None})


@router.get("/analytics/insights", response_model=List[Insight])
async def get_insights(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    df, dataset = await AnalyticsService.load_dataframe(dataset_id)
    cur_df, prev_df, _, _ = AnalyticsService.slice_dataframe(df, filters)
    caps = dataset.get("capabilities", {})
    insights = InsightsService.generate_insights(cur_df, prev_df, caps.get("cost", False), caps.get("customers", False))
    return json_response([model_to_dict(i) for i in insights])


@router.get("/analytics/kpis")
async def get_kpis(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    overview = await AnalyticsService.get_overview(dataset_id, filters)
    return json_response({
        "success": True,
        "data": {"period": overview.period, "kpis": [model_to_dict(k) for k in overview.kpis]},
        "error": None,
    })


@router.get("/analytics/timeseries")
async def get_timeseries(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    sales = await AnalyticsService.get_sales(dataset_id, filters)
    return json_response({
        "success": True,
        "data": {
            "trend": [model_to_dict(t) for t in sales.trend],
            "previousTrend": [model_to_dict(t) for t in sales.previousTrend] if sales.previousTrend else None,
            "categoryTrend": [model_to_dict(ct) for ct in sales.categoryTrend],
        },
        "error": None,
    })


@router.get("/records", response_model=ExplorerData)
@router.get("/analytics/explorer", response_model=ExplorerData, include_in_schema=False)
async def get_records(
    dataset_id: str,
    limit: Optional[int] = Query(None, ge=1, description="Omit to return every row (up to MAX_EXPLORER_ROWS)."),
    offset: int = Query(0, ge=0),
    sortBy: Optional[str] = Query(None),
):
    data = await AnalyticsService.get_explorer_data(dataset_id, limit=limit, offset=offset, sort_by=sortBy)
    d = model_to_dict(data)
    return json_response({
        **d,
        "success": True,
        "data": d,
        "error": None,
        "meta": {"total": data.total, "returned": len(data.rows), "limit": limit, "offset": offset,
                 "truncated": data.total is not None and offset + len(data.rows) < data.total},
    })
