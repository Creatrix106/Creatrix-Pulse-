from typing import List

from fastapi import APIRouter, Depends

from app.api.v1.analytics import get_filters
from app.core.compat import model_to_dict
from app.core.response import json_response
from app.schemas.filters import AnalyticsFilters
from app.schemas.insight import Insight
from app.services.analytics_service import AnalyticsService
from app.services.insights_service import InsightsService

router = APIRouter(prefix="/datasets/{dataset_id}/insights", tags=["Insights"])


@router.get("", response_model=List[Insight])
async def get_insights(dataset_id: str, filters: AnalyticsFilters = Depends(get_filters)):
    df, dataset = await AnalyticsService.load_dataframe(dataset_id)
    cur_df, prev_df, _, _ = AnalyticsService.slice_dataframe(df, filters)
    caps = dataset.get("capabilities", {})
    insights = InsightsService.generate_insights(cur_df, prev_df, caps.get("cost", False), caps.get("customers", False))
    return json_response([model_to_dict(i) for i in insights])
