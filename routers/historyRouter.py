from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query

from app.Validation.historyValidation import HistoryQueryValidationSchema
from app.core.dependencies import get_current_ngo_id
from app.models.historySchema import HistoryListResponseSchema, HistoryNeedItemSchema
from app.services.history.History import get_history_need_by_id, get_history_needs

router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=HistoryListResponseSchema)
async def get_history_controller(
    submitted_by: Optional[str] = Query(default=None),
    status: Optional[Literal["pending", "assigned", "completed"]] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    ngo_id: str = Depends(get_current_ngo_id),
):
    data = HistoryQueryValidationSchema(
        submitted_by=submitted_by,
        status=status,
        limit=limit,
    )
    return await get_history_needs(data, ngo_id)


@router.get("/{need_id}", response_model=HistoryNeedItemSchema)
async def get_history_need_controller(
    need_id: str,
    ngo_id: str = Depends(get_current_ngo_id),
):
    return await get_history_need_by_id(need_id, ngo_id)