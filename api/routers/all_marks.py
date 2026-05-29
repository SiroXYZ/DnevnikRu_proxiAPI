"""Router для endpoint /all_marks"""
from fastapi import APIRouter, Header, Query
from typing import Dict, Any, Optional, List
from handlers.all_marks_handler import AllMarksHandler

router = APIRouter(prefix="/all_marks", tags=["All Marks"])


@router.get("", summary="Получить все оценки с расчетом среднего балла")
async def get_all_marks(
    access_token: str = Header(..., description="Токен доступа"),
    person: Optional[str] = Query(None, description="ID ученика (опционально)"),
    periods_id: Optional[str] = Query(None, description="ID периода отчетности (опционально)"),
    subjects_id: Optional[str] = Query(None, description="ID предметов через запятую (опционально)"),
    edu_group_id: Optional[str] = Query(None, description="ID учебной группы (опционально)"),
    school_id: Optional[str] = Query(None, description="ID школы (опционально)")
) -> Dict[str, Any]:
    """
    Получить все оценки за период с расчетом среднего балла
    
    Возвращает все оценки за указанный период, сгруппированные по предметам,
    с автоматическим расчетом среднего балла по каждому предмету.
    
    **Параметры:**
    - **access_token**: Токен доступа (в заголовке) - обязательно
    - **person**: ID ученика - опционально (если не указан, берется из контекста)
    - **periods_id**: ID периода отчетности - опционально (если не указан, берется текущий период)
    - **subjects_id**: ID предметов через запятую для фильтра - опционально (если не указан, берутся все)
    - **edu_group_id**: ID учебной группы - опционально (если не указан, берется из контекста)
    - **school_id**: ID школы - опционально (если не указан, берется из контекста)
    
    **Примеры:**
    ```
    GET /all_marks
    GET /all_marks?person=1000014719355
    GET /all_marks?periods_id=12345
    GET /all_marks?subjects_id=123,456,789
    GET /all_marks?person=1000014719355&subjects_id=123,456
    GET /all_marks?edu_group_id=2392148420039838219
    GET /all_marks?school_id=12345
    ```
    
    """
    subjects_list = None
    if subjects_id:
        subjects_list = [s.strip() for s in subjects_id.split(",")]
    
    handler = AllMarksHandler()
    return await handler.handle(
        token=access_token,
        person_id=person,
        periods_id=periods_id,
        subjects_id=subjects_list,
        edu_group_id=edu_group_id,
        school_id=school_id
    )
