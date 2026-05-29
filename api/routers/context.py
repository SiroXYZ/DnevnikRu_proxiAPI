"""Router для endpoint /me/context"""
from fastapi import APIRouter, Header
from typing import Dict, Any
from handlers.context_handler import ContextHandler

router = APIRouter(tags=["Context"])


@router.get("/me/context", summary="Получить контекст текущего пользователя")
async def get_current_context(access_token: str = Header(..., description="Токен доступа")) -> Dict[str, Any]:
    """
    Получить полный контекст текущего пользователя
    
    Включает информацию о:
    - Текущем пользователе
    - Его учебных группах
    - Организации
    - День рождения 
    - часовом поясе 
    - дети
    
    **Параметры:**
    - **access_token**: Токен доступа (в заголовке) - обязательно
    
    **Примеры:**
    ```
    GET /me/context
    ```
    
    """
    handler = ContextHandler()
    return await handler.handle(token=access_token)
