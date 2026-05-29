"""Router для endpoint /subjects"""
from fastapi import APIRouter, Header, Query
from typing import Dict, Any, Optional
from handlers.subjects_handler import SubjectsHandler

router = APIRouter(prefix="/subjects", tags=["Subjects"])


@router.get("", summary="Получить список предметов")
async def get_subjects(
    access_token: str = Header(..., description="Токен доступа"),
    edu_group_id: Optional[str] = Query(None, description="ID учебной группы (опционально)"),
    all: bool = Query(False, description="Получить все предметы школы (default: false)"),
    school_id: Optional[str] = Query(None, description="ID школы (опционально)")
) -> Dict[str, Any]:
    """
    Получить список предметов в группе или во всей школе
    
    Возвращает список всех предметов, которые изучаются в указанной группе
    или во всей школе в зависимости от параметров.
    
    **Параметры:**
    - **access_token**: Токен доступа (в заголовке) - обязательно
    - **edu_group_id**: ID учебной группы - опционально (если не указан, берется из контекста)
    - **all**: Получить все предметы школы - опционально (default: false)
    - **school_id**: ID школы - опционально (если не указан, берется из контекста)
    
    **Примеры:**
    ```
    GET /subjects
    GET /subjects?edu_group_id=2392148420039838219
    GET /subjects?all=true
    GET /subjects?all=true&school_id=12345
    ```
    
        """
    handler = SubjectsHandler()
    return await handler.handle(
        token=access_token, 
        edu_group_id=edu_group_id, 
        all=all,
        school_id=school_id
    )
