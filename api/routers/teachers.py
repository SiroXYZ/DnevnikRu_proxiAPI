"""Router для endpoint /teachers"""
from fastapi import APIRouter, Header, Query
from typing import Dict, Any, Optional
from handlers.teachers_handler import TeachersHandler

router = APIRouter(prefix="/teachers", tags=["Teachers"])


@router.get("", summary="Получить список всех учителей")
async def get_teachers(
    access_token: str = Header(..., description="Токен доступа"),
    school_id: Optional[str] = Query(None, description="ID школы (опционально)")
) -> Dict[str, Any]:
    """
    Получить полный список учителей школы
    
    Возвращает информацию об всех учителях организации.
    
    **Параметры:**
    - **access_token**: Токен доступа (в заголовке) - обязательно
    - **school_id**: ID школы - опционально (если не указан, берется из контекста)
    
    **Примеры:**
    ```
    GET /teachers
    GET /teachers?school_id=12345
    ```
    

    """
    handler = TeachersHandler()
    return await handler.handle(token=access_token, school_id=school_id)
