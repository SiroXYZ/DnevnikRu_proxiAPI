"""Router для endpoint /relatives"""
from fastapi import APIRouter, Header
from typing import Dict, Any
from handlers.relatives_handler import RelativesHandler

router = APIRouter(prefix="/relatives", tags=["Relatives"])


@router.get("", summary="Получить список родителей/опекунов")
async def get_relatives(access_token: str = Header(..., description="Токен доступа")) -> Dict[str, Any]:
    """
    Получить список родителей/опекунов текущего пользователя
    
    Возвращает информацию об всех родителях и опекунах ученика.
    
    **Параметры:**
    - **access_token**: Токен доступа (в заголовке) - обязательно
    
    **Примеры:**
    ```
    GET /relatives
    ```
    
    """
    handler = RelativesHandler()
    return await handler.handle(token=access_token)

