"""Router для endpoint /marks"""
from fastapi import APIRouter, Header, Query
from typing import Dict, Any, Optional
from handlers.marks_handler import MarksHandler

router = APIRouter(prefix="/marks", tags=["Marks"])


@router.get("", summary="Получить оценки за период")
async def get_marks(
    access_token: str = Header(..., description="Токен доступа"),
    start_date: str = Query(..., description="Начальная дата (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Конечная дата (YYYY-MM-DD), опционально"),
    person_id: Optional[str] = Query(None, description="ID ученика (опционально)"),
    school_id: Optional[str] = Query(None, description="ID школы (опционально)"),
    subject: Optional[str] = Query(None, description="Фильтр по названию предмета (опционально)"),
    by_mark_date: bool = Query(False, description="Фильтр по дате выставления вместо даты урока")
) -> Dict[str, Any]:
    """
    Получить оценки за период, сгруппированные по предметам
    
    Возвращает все оценки за указанный период, сгруппированные по предметам.
    Может фильтроваться по предмету и дате.
    
    **Параметры:**
    - **access_token**: Токен доступа (в заголовке) - обязательно
    - **start_date**: Начальная дата (YYYY-MM-DD) - обязательно
    - **end_date**: Конечная дата (YYYY-MM-DD) - опционально (если не указана, используется start_date)
    - **person_id**: ID ученика - опционально (если не указан, берется из контекста)
    - **school_id**: ID школы - опционально (если не указан, берется из контекста)
    - **subject**: Название предмета для фильтра - опционально
    - **by_mark_date**: Фильтр по дате выставления оценки вместо даты урока - default: false
    
    **Примеры:**
    ```
    GET /marks?start_date=2026-01-12
    GET /marks?start_date=2026-01-01&end_date=2026-01-31
    GET /marks?start_date=2026-01-12&subject=Алгебра
    GET /marks?start_date=2026-01-12&person_id=1000014719355
    GET /marks?start_date=2026-01-12&school_id=12345
    GET /marks?start_date=2026-01-12&by_mark_date=true
    ```

    """
    handler = MarksHandler()
    return await handler.handle(
        token=access_token, 
        start_date=start_date, 
        end_date=end_date,
        person_id=person_id,
        school_id=school_id,
        subject=subject,
        by_mark_date=by_mark_date
    )
