"""Router для endpoint /lessons/{lesson_id}"""
from fastapi import APIRouter, Header, Path, Query
from typing import Dict, Any, Optional
from handlers.lessons_handler import LessonsHandler

router = APIRouter(prefix="/lessons", tags=["Lessons"])


@router.get("/{lesson_id}", summary="Получить информацию об уроке")
async def get_lesson(
    lesson_id: str = Path(..., description="ID урока"),
    access_token: str = Header(..., description="Токен доступа"),
    school_id: Optional[str] = Query(None, description="ID школы (опционально)")
) -> Dict[str, Any]:
    """
    Получить детальную информацию об уроке по ID
    
    Возвращает полную информацию об уроке, включая тему, предмет, 
    домашнее задание и другую информацию.
    
    **Параметры:**
    - **lesson_id**: ID урока (в пути) - обязательно
    - **access_token**: Токен доступа (в заголовке) - обязательно
    - **school_id**: ID школы - опционально (если не указан, берется из контекста)
    
    **Примеры:**
    ```
    GET /lessons/2437771422378810496
    GET /lessons/2437771422378810496?school_id=12345
    ```
    
    """
    handler = LessonsHandler()
    return await handler.handle(
        token=access_token,
        lesson_id=lesson_id,
        school_id=school_id
    )
