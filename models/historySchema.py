from typing import List, Literal

from pydantic import BaseModel


class HistoryAIOutputSchema(BaseModel):
    description: str
    need_type: str
    urgency: Literal["Low", "Medium", "High", "Critical", "Unknown"]
    resources: List[str]


class HistoryNeedItemSchema(BaseModel):
    need_id: str
    submitted_by: str
    location: str
    people_affected: Literal["1-10", "10-50", "50-100", "100+"]
    time_sensitivity: Literal[
        "Immediate (within 24 hrs)",
        "Within 2-3 days",
        "Within a week",
    ]
    status: Literal["pending", "assigned", "completed"]
    ai_output: HistoryAIOutputSchema
    created_at: str


class HistoryListResponseSchema(BaseModel):
    total: int
    items: List[HistoryNeedItemSchema]