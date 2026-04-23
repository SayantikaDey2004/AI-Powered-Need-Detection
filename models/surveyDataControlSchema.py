from typing import List, Literal, Optional

from pydantic import BaseModel

from app.models.volunteerMatchingSchema import VolunteerMatchResponseSchema


class SurveyDataControlStatusSchema(BaseModel):
    urgency: Literal["Low", "Medium", "High", "Critical", "Unknown"]
    description: str


class SurveyDataControlAIOutputSchema(BaseModel):
    submitted_by: str
    processing_status: Literal["pending", "processed", "failed"]
    location: str
    need_type: str
    urgency: Literal["Low", "Medium", "High", "Critical", "Unknown"]
    people_affected: Literal["1-10", "10-50", "50-100", "100+"]
    time_sensitivity: Literal[
        "Immediate (within 24 hrs)",
        "Within 2-3 days",
        "Within a week",
    ]
    resources: List[str]
    status: SurveyDataControlStatusSchema
    auto_match_result: VolunteerMatchResponseSchema


class SurveyDataControlCreateResponseSchema(SurveyDataControlAIOutputSchema):
    pass


class SurveyDataControlItemSchema(SurveyDataControlAIOutputSchema):
    created_at: str


class SurveyDataControlListResponseSchema(BaseModel):
    total: int
    items: List[SurveyDataControlItemSchema]