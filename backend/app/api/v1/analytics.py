from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas.filters import AnalyticsFilters, DatePreset, ComparisonMode, GroupBy
from app.schemas.analytics import (
    OverviewData,
    SalesData,
    ProductsData,
    CustomersResponse,
    FinanceResponse,
    ExplorerData,
)
from app.schemas.insight import Insight
from app.services.analytics_service import AnalyticsService
from app.services.insights_service import InsightsService

router = APIRouter(prefix="/datasets/{dataset_id}", tags=["Analytics"])

def get_filters(
    datePreset: DatePreset = Query("all", alias="datePreset"),
    dateFrom: Optional[str] = Query(None, alias="dateFrom"),
    dateTo: Optional[str] = Query(None, alias="dateTo"),
    comparison: ComparisonMode = Query("none"),
    groupBy: GroupBy = Query("month", alias="groupBy"),
    categories: Optional[List[str]] = Query(None),
    regions: Optional[List[str]] = Query(None),
    productId: Optional[str] = Query(None, alias="productId"),
    customerId: Optional[str] = Query(None, alias="customerId"),
    limit: Optional[int] = Query(100),
    offset: Optional[int] = Query(0),
    sortBy: Optional[str] = Query(None, alias="sortBy"),
) -> AnalyticsFilters:
    # Handle comma-separated query parameters if passed as a single string
    clean_cats = []
    if categories:
        for c in categories:
            clean_cats.extend([item.strip() for item in c.split(",") if item.strip()])

    clean_regs = []
    if regions:
        for r in regions:
            clean_regs.extend([item.strip() for item in r.split(",") if item.strip()])

    return AnalyticsFilters(
        datePreset=datePreset,
        dateFrom=dateFrom,
        dateTo=dateTo,
        comparison=comparison,
        groupBy=groupBy,
        categories=clean_cats,
        regions=clean_regs,
        productId=productId,
        customerId=customerId,
        limit=limit,
        offset=offset,
        sortBy=sortBy,
    )

@router.get("/analytics/overview", response_model=OverviewData)
async def get_overview(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    try:
        data = await AnalyticsService.get_overview(dataset_id, filters)
        res = data.dict()
        res.update({"success": True, "data": data.dict(), "error": None})
        return JSONResponse(content=res)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )

@router.get("/analytics/sales", response_model=SalesData)
async def get_sales(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    try:
        data = await AnalyticsService.get_sales(dataset_id, filters)
        res = data.dict()
        res.update({"success": True, "data": data.dict(), "error": None})
        return JSONResponse(content=res)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )

@router.get("/analytics/products", response_model=ProductsData)
async def get_products(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    try:
        data = await AnalyticsService.get_products(dataset_id, filters)
        res = data.dict()
        res.update({"success": True, "data": data.dict(), "error": None})
        return JSONResponse(content=res)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )

@router.get("/analytics/customers", response_model=CustomersResponse)
async def get_customers(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    try:
        data = await AnalyticsService.get_customers(dataset_id, filters)
        res = data.dict()
        res.update({"success": True, "error": None})
        return JSONResponse(content=res)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )

@router.get("/analytics/finance", response_model=FinanceResponse)
async def get_finance(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    try:
        data = await AnalyticsService.get_finance(dataset_id, filters)
        res = data.dict()
        res.update({"success": True, "error": None})
        return JSONResponse(content=res)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )

@router.get("/analytics/insights", response_model=List[Insight])
async def get_insights(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    try:
        df, dataset = await AnalyticsService.load_dataframe(dataset_id)
        cur_df, prev_df, _, _ = AnalyticsService.slice_dataframe(df, filters)
        has_cost = dataset.get("capabilities", {}).get("cost", False)
        has_customers = dataset.get("capabilities", {}).get("customers", False)
        insights = InsightsService.generate_insights(cur_df, prev_df, has_cost, has_customers)
        return JSONResponse(content=[i.dict() for i in insights])
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )

# Direct endpoints matching prompt Section 2
@router.get("/analytics/kpis")
async def get_kpis(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    try:
        overview = await AnalyticsService.get_overview(dataset_id, filters)
        return {
            "success": True,
            "data": {
                "period": overview.period,
                "kpis": [k.dict() for k in overview.kpis]
            },
            "error": None
        }
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )

@router.get("/analytics/timeseries")
async def get_timeseries(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    try:
        sales = await AnalyticsService.get_sales(dataset_id, filters)
        return {
            "success": True,
            "data": {
                "trend": [t.dict() for t in sales.trend],
                "previousTrend": [t.dict() for t in sales.previousTrend] if sales.previousTrend else None,
                "categoryTrend": [ct.dict() for ct in sales.categoryTrend]
            },
            "error": None
        }
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )

@router.get("/records", response_model=ExplorerData)
@router.get("/analytics/explorer", response_model=ExplorerData)
async def get_records(
    dataset_id: str,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sortBy: Optional[str] = Query(None, alias="sortBy")
):
    try:
        data = await AnalyticsService.get_explorer_data(dataset_id, limit=limit, offset=offset, sort_by=sortBy)
        res = data.dict()
        res.update({
            "success": True,
            "data": data.dict(),
            "error": None,
            "meta": {"total": data.total, "limit": limit, "offset": offset}
        })
        return JSONResponse(content=res)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "dataset_not_found", "message": "This dataset does not exist."}
        )
