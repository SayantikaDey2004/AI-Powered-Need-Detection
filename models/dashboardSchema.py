from pydantic import BaseModel


class DashboardSchema(BaseModel):
    total_active_needs: int
    available_volunteer_number: int
    urgent_cases: int
    auto_match_now_button: bool = True


class AutoMatchResultSchema(BaseModel):
    message: str
    matched_count: int
    dry_run: bool
