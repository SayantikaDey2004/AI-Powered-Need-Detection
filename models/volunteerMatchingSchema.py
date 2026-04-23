from typing import List, Literal, Optional

from pydantic import BaseModel


class NeedForMatchingSchema(BaseModel):
    need_id: str
    submitted_by: str
    need_type: str
    urgency: Literal["Low", "Medium", "High", "Critical", "Unknown"]
    resources: List[str]
    description: str
    location: str
    processing_status: Literal["pending", "processed", "failed"]


class RankedVolunteerSchema(BaseModel):
    volunteer_id: str
    volunteer_name: str
    volunteer_email: Optional[str] = None
    volunteer_phone: Optional[str] = None
    volunteer_location: Optional[str] = None
    skills: List[str]
    score: int
    explanation: str


class VolunteerMatchResponseSchema(BaseModel):
    message: str
    total_volunteers_considered: int
    need: NeedForMatchingSchema
    ranked_volunteers: List[RankedVolunteerSchema]
