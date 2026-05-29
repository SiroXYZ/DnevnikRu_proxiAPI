"""Router для endpoint /works/{work_id}"""
from fastapi import APIRouter, Header, Path, Query
from typing import Dict, Any, Optional
from handlers.works_handler import WorksHandler

router = APIRouter(prefix="/works", tags=["Works"])


@router.get("/{work_id}", summary="Получить информацию о работе и оценки")
async def get_work(
    work_id: str = Path(..., description="ID работы"),
    access_token: str = Header(..., description="Токен доступа"),
    person: Optional[str] = Query(None, description="ID ученика (опционально)"),
    school_id: Optional[str] = Query(None, description="ID школы (опционально)")
) -> Dict[str, Any]:
    """
    Получить информацию о работе и распределение оценок по классу
    
    Возвращает детальную информацию о работе (тест, контрольная и т.д.),
    включая распределение оценок по классу и информацию об оценке текущего ученика.
    
    **Параметры:**
    - **work_id**: ID работы (в пути) - обязательно
    - **access_token**: Токен доступа (в заголовке) - обязательно
    - **person**: ID ученика для отображения его оценки (опционально)
    - **school_id**: ID школы - опционально (если не указан, берется из контекста)
    
    **Примеры:**
    ```
    GET /works/2437842791850343569
    GET /works/2437842791850343569?person=1000014719355
    GET /works/2437842791850343569?school_id=12345
    ```

    
    **Примечание:**
    Параметр `person` позволяет получить информацию об оценке конкретного ученика.
    """
    handler = WorksHandler()
    return await handler.handle(
        token=access_token,
        work_id=work_id,
        person_id=person,
        school_id=school_id
    )    
