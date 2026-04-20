from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class HistoryQueryValidationSchema(BaseModel):
    submitted_by: Optional[str] = Field(default=None, min_length=1, max_length=128)
    status: Optional[Literal["pending", "assigned", "completed"]] = None
    limit: int = Field(default=50, ge=1, le=200)

    @field_validator("submitted_by", mode="before")
    @classmethod
    def normalize_submitted_by(cls, value):
        if value is None:
            return None

        cleaned_value = value.strip()
        if not cleaned_value:
            return None

        return cleaned_value