"""Router для endpoint /schedules"""
from fastapi import APIRouter, Header, Query
from typing import Dict, Any, Optional
from handlers.schedules_handler import SchedulesHandler

router = APIRouter(prefix="/schedules", tags=["Schedules"])


@router.get("", summary="Получить расписание уроков")
async def get_schedules(
    access_token: str = Header(..., description="Токен доступа"),
    start_date: str = Query(..., description="Начальная дата (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Конечная дата (YYYY-MM-DD), опционально"),
    person_id: Optional[str] = Query(None, description="ID ученика (опционально)"),
    group_id: Optional[str] = Query(None, description="ID группы (опционально)")
) -> Dict[str, Any]:
    """
    Получить расписание текущего пользователя за период
    
    Возвращает полное расписание уроков с учетом времени, предмета,
    кабинета и информацией об учителе.
    
    **Параметры:**
    - **access_token**: Токен доступа (в заголовке) - обязательно
    - **start_date**: Начальная дата (YYYY-MM-DD) - обязательно
    - **end_date**: Конечная дата (YYYY-MM-DD) - опционально (если не указана, используется start_date)
    - **person_id**: ID ученика - опционально (если не указан, берется из контекста)
    - **group_id**: ID группы - опционально (если не указан, берется из контекста)
    
    **Примеры:**
    ```
    GET /schedules?start_date=2025-12-10
    GET /schedules?start_date=2025-12-10&end_date=2025-12-15
    GET /schedules?start_date=2025-12-10&person_id=12345&group_id=67890
    ```
    
    **Примечание:**
    Расписание выдается для текущего пользователя из контекста, если параметры не указаны.
    """
    handler = SchedulesHandler()
    return await handler.handle(
        token=access_token, 
        start_date=start_date, 
        end_date=end_date,
        person_id=person_id,
        group_id=group_id
    )
