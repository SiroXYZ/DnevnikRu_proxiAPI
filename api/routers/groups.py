"""Router для endpoints /groups и /group-students"""
from fastapi import APIRouter, Header, Query
from typing import Dict, Any, Optional
from handlers.groups_handler import GroupsHandler
from handlers.group_students_handler import GroupStudentsHandler

router = APIRouter(tags=["Groups"])


@router.get("/groups", summary="Получить список групп")
async def get_groups(
    access_token: str = Header(..., description="Токен доступа"),
    group_ids: Optional[str] = Query(None, description="ID группы для определения параллели (опционально)"),
    parallel: bool = Query(True, description="Возвращать группы параллели (true) или всей школы (false)"),
    school_id: Optional[str] = Query(None, description="ID школы (опционально)"),
    edu_group_id: Optional[str] = Query(None, description="ID учебной группы (опционально)")
) -> Dict[str, Any]:
    """
    Получить список групп параллели или всей школы
    
    Возвращает список учебных групп в зависимости от указанных параметров.
    
    **Параметры:**
    - **access_token**: Токен доступа (в заголовке) - обязательно
    - **group_ids**: ID группы для определения её параллели - опционально
    - **parallel**: Возвращать группы параллели (true) или всей школы (false) - default: true
    - **school_id**: ID школы - опционально (если не указан, берется из контекста)
    - **edu_group_id**: ID учебной группы - опционально (если не указан, берется из контекста)
    
    **Примеры:**
    ```
    GET /groups
    GET /groups?group_ids=123
    GET /groups?parallel=false
    GET /groups?school_id=12345
    ```
    
    """
    handler = GroupsHandler()
    return await handler.handle(
        token=access_token, 
        parallel=parallel, 
        group_ids=group_ids,
        school_id=school_id,
        edu_group_id=edu_group_id
    )


@router.get("/group-students", summary="Получить список учеников групп")
async def get_group_students(
    access_token: str = Header(..., description="Токен доступа"),
    group_ids: Optional[str] = Query(None, description="ID группы (опционально)"),
    parallel: bool = Query(False, description="Получить учеников параллели"),
    school: bool = Query(False, description="Получить учеников всей школы"),
    school_id: Optional[str] = Query(None, description="ID школы (опционально)")
) -> Dict[str, Any]:
    """
    Получить список учеников групп
    
    Возвращает информацию об учениках в указанных группах или во всей школе.
    
    **Параметры:**
    - **access_token**: Токен доступа (в заголовке) - обязательно
    - **group_ids**: ID конкретной группы - опционально
    - **parallel**: Получить учеников всей параллели, если указан group_ids вернет параллель этой группы- default: false
    - **school**: Получить учеников всей школы - default: false (игнорирует остальные параметры)
    - **school_id**: ID школы - опционально (если не указан, берется из контекста)
    
    **Примеры:**
    ```
    GET /group-students?group_ids=123
    GET /group-students?parallel=true
    GET /group-students?school=true
    GET /group-students?school=true&school_id=12345
    ```

    """
    

    handler = GroupStudentsHandler()
    return await handler.handle(
        token=access_token,
        group_ids=group_ids,
        parallel=parallel,
        school=school,
        school_id=school_id
    )
