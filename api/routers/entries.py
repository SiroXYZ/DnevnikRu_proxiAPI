"""Router для endpoint /entries"""
from fastapi import APIRouter, Header, Query
from typing import Dict, Any, Optional
from handlers.entries_handler import EntriesHandler

router = APIRouter(prefix="/entries", tags=["Entries"])


@router.get("", summary="Получить записи логов (пропуски и посещения)")
async def get_entries(
    access_token: str = Header(..., description="Токен доступа"),
    start_date: str = Query(..., description="Начальная дата (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Конечная дата (YYYY-MM-DD), опционально"),
    person_id: Optional[str] = Query(None, description="ID ученика (опционально)"),
    school_id: Optional[str] = Query(None, description="ID школы (опционально)")
) -> Dict[str, Any]:
    """
    Получить записи логов за период (посещаемость, пропуски)
    
    Возвращает информацию о посещаемости ученика: пропуски, болезни и т.д.

    
    **Параметры:**
    - **access_token**: Токен доступа (в заголовке) - обязательно
    - **start_date**: Начальная дата (YYYY-MM-DD) - обязательно
    - **end_date**: Конечная дата (YYYY-MM-DD) - опционально (если не указана, используется start_date)
    - **person_id**: ID ученика - опционально (если не указан, используется текущий пользователь)
    - **school_id**: ID школы - опционально (если не указан, берется из контекста)
    
    **Примеры:**
    ```
    GET /entries?start_date=2025-12-22
    GET /entries?start_date=2025-12-01&end_date=2026-01-13
    GET /entries?start_date=2025-12-22&person_id=12345
    GET /entries?start_date=2025-12-22&school_id=12345
    ```
    
    """
    handler = EntriesHandler()
    
    return await handler.handle(
        token=access_token, 
        start_date=start_date, 
        end_date=end_date,
        person_id=person_id,
        school_id=school_id
    )
