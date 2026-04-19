from fastapi import APIRouter

from app.Validation.dashboardValidation import AutoMatchNowValidationSchema
from app.models.dashboardSchema import AutoMatchResultSchema, DashboardSchema
from app.services.dashboard.Dashboard import auto_match_now, get_dashboard_summary

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardSchema)
async def dashboard_overview_controller():
    return await get_dashboard_summary()


@router.post("/auto-match-now", response_model=AutoMatchResultSchema)
async def auto_match_now_controller(data: AutoMatchNowValidationSchema):
    return await auto_match_now(data)
