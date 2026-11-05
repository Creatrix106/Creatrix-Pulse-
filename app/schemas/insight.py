from typing import List, Optional, Literal
from pydantic import BaseModel

InsightType = Literal["positive", "negative", "anomaly", "observation", "recommendation"]

class InsightEvidence(BaseModel):
    label: str
    value: str

class Insight(BaseModel):
    id: str
    type: InsightType
    title: str
    summary: str
    metric: Optional[str] = None
    evidence: List[InsightEvidence]
