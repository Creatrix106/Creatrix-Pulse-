from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.schemas.insight import Insight
from app.schemas.filters import AnalyticsFilters
from app.api.v1.analytics import get_filters
from app.services.analytics_service import AnalyticsService
from app.services.insights_service import InsightsService

router = APIRouter(prefix="/datasets/{dataset_id}/insights", tags=["Insights"])

@router.get("", response_model=List[Insight])
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
