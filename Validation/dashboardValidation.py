from pydantic import BaseModel, Field


class AutoMatchNowValidationSchema(BaseModel):
    dry_run: bool = False
    max_matches: int = Field(default=20, ge=1, le=500)
