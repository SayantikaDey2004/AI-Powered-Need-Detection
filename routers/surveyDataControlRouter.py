from fastapi import APIRouter, Depends, Query

from app.Validation.surveyDataControlValidation import SurveyDataControlValidationSchema
from app.core.dependencies import get_current_ngo_id
from app.models.surveyDataControlSchema import (
    SurveyDataControlCreateResponseSchema,
    SurveyDataControlListResponseSchema,
)
from app.services.survey.SurveyDataControl import (
    create_survey_data_control,
    get_latest_survey_data_control_for_user,
    get_survey_data_controls,
)

router = APIRouter(prefix="/survey-data-control", tags=["Survey Data Control"])


@router.post("", response_model=SurveyDataControlCreateResponseSchema)
async def create_survey_data_control_controller(
    data: SurveyDataControlValidationSchema,
    ngo_id: str = Depends(get_current_ngo_id),
):
    return await create_survey_data_control(data, ngo_id)


@router.get("", response_model=SurveyDataControlListResponseSchema)
async def get_survey_data_control_controller(
    limit: int = Query(default=50, ge=1, le=200),
    ngo_id: str = Depends(get_current_ngo_id),
):
    return await get_survey_data_controls(limit, ngo_id)


@router.get("/result/{submitted_by}", response_model=SurveyDataControlCreateResponseSchema)
async def get_latest_survey_result_controller(
    submitted_by: str,
    ngo_id: str = Depends(get_current_ngo_id),
):
    return await get_latest_survey_data_control_for_user(submitted_by, ngo_id)