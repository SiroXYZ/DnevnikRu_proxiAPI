"""Router для endpoint /work-types"""
from fastapi import APIRouter, Header, Query
from typing import Dict, Any, Optional
from handlers.work_types_handler import WorkTypesHandler

router = APIRouter(prefix="/work-types", tags=["Work Types"])


@router.get("", summary="Получить типы работ школы")
async def get_work_types(
    access_token: str = Header(..., description="Токен доступа"),
    school_id: Optional[str] = Query(None, description="ID школы (опционально)")
) -> Dict[str, Any]:
    """
    Получить список типов работ школы
    
    Возвращает все доступные типы учебных работ (контрольная, самостоятельная и т.д.),
    которые используются в школе.
    
    **Параметры:**
    - **access_token**: Токен доступа (в заголовке) - обязательно
    - **school_id**: ID школы - опционально (если не указан, берется из контекста)
    
    **Примеры:**
    ```
    GET /work-types
    GET /work-types?school_id=12345
    ```
    

    """
    handler = WorkTypesHandler()
    return await handler.handle(token=access_token, school_id=school_id)
