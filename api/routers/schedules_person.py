"""Router для расписания ученика с деталями уроков"""
from fastapi import APIRouter, Query, Path, Header
from typing import Optional, Dict, Any
from handlers.schedules_person_handler import SchedulesPersonHandler

router = APIRouter(prefix="/schedules-person", tags=["Schedules"])


@router.get("/{person_id}/{group_id}/{start_date}", summary="Получить расписание ученика с деталями уроков")
async def get_schedules_person(
    person_id: str = Path(..., description="ID ученика"),
    group_id: str = Path(..., description="ID группы"),
    start_date: str = Path(..., description="Дата начала (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Дата конца (YYYY-MM-DD), если не указана - используется start_date"),
    access_token: str = Header(..., description="Токен доступа к API"),
    school_id: Optional[str] = Query(None, description="ID школы (опционально)")
) -> Dict[str, Any]:
    """
    Получить расписание ученика на определенную дату(ы) с деталями об уроках.
    
    Возвращает полное расписание с информацией о каждом уроке:
    - Название и описание урока
    - Учитель
    - Номер урока и время
    - Домашнее задание с файлами
    - Выполненные работы
    - Информация о посещаемости
    
    **Параметры:**
    - `person_id` - ID ученика (в пути)
    - `group_id` - ID группы (в пути)
    - `start_date` - дата начала (YYYY-MM-DD) (в пути)
    - `end_date` - дата конца (опционально в query)
    - `access_token` - токен доступа (в заголовке)
    - `school_id` - ID школы (опционально в query)
    
    **Пример запроса:**
    ```
    GET /schedules-person/12345/67890/2026-01-12?end_date=2026-01-13&school_id=12345
    Header: access-token: токен
    ```
    """
    handler = SchedulesPersonHandler()
    result = await handler.handle(
        token=access_token,
        person_id=person_id,
        group_id=group_id,
        start_date=start_date,
        end_date=end_date,
        school_id=school_id
    )
    return result
