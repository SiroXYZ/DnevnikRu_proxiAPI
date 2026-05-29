"""Router для endpoint /reporting-periods"""
from fastapi import APIRouter, Header, Query
from typing import Dict, Any, Optional
from handlers.reporting_periods_handler import ReportingPeriodsHandler

router = APIRouter(prefix="/reporting-periods", tags=["Reporting Periods"])


@router.get("", summary="Получить периоды отчётности")
async def get_reporting_periods(
    access_token: str = Header(..., description="Токен доступа"),
    edu_group_id: Optional[str] = Query(None, description="ID учебной группы (опционально)")
) -> Dict[str, Any]:
    """
    Получить список периодов отчётности в группе
    
    Возвращает учебные периоды (четверти, триместры и т.д.) в указанной группе.
    
    **Параметры:**
    - **access_token**: Токен доступа (в заголовке) - обязательно
    - **edu_group_id**: ID учебной группы - опционально (если не указан, берется из контекста)
    
    **Примеры:**
    ```
    GET /reporting-periods
    GET /reporting-periods?edu_group_id=2392148420039838219
    ```

    """
    handler = ReportingPeriodsHandler()
    return await handler.handle(token=access_token, edu_group_id=edu_group_id)
