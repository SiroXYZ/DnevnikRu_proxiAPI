"""Обработчик для endpoint /groups"""
from typing import Any, Dict, List, Optional
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler


# ==================== КОНСТАНТЫ ====================
GROUP_TYPE_FILTER = "Group"
# ==================================================


class GroupsHandler:
    """Обработчик данных групп в параллели или школе"""
    
    async def handle(
        self, 
        token: str, 
        parallel: bool = True, 
        group_ids: Optional[str] = None,
        school_id: Optional[str] = None,
        edu_group_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить список групп параллели или всей школы
        
        Args:
            token: токен доступа
            parallel: если True, возвращает группы параллели; если False, возвращает все группы школы
            group_ids: опционально, ID группы для получения её параллели
            school_id: ID школы, опционально (если не указан, берется из контекста)
            edu_group_id: ID учебной группы, опционально (если не указан, берется из контекста)
        """
        try:
            client = DnevnikAPIClient(token=token)
            request_handler = RequestHandler(client)
            
            async with client:
                context_data = await request_handler.get_context()
                
                if parallel:
                    groups = await self._get_parallel_groups(
                        request_handler,
                        context_data,
                        group_ids,
                        edu_group_id
                    )
                else:
                    groups = await self._get_all_school_groups(
                        request_handler,
                        context_data,
                        school_id
                    )
                
                if groups is None:
                    return {
                        "success": False,
                        "error": "Failed to retrieve groups"
                    }
            
            logger.info("Groups data processed successfully")
            return {
                "success": True,
                "data": {
                    "groups": groups
                }
            }
        except Exception as e:
            logger.error(f"Error in GroupsHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_parallel_groups(
        self,
        request_handler: RequestHandler,
        context_data: Dict[str, Any],
        group_ids: Optional[str],
        edu_group_id: Optional[str]
    ) -> Optional[List[Dict[str, str]]]:
        if group_ids:
            endpoint = f"edu-groups/{group_ids}/parallel"
        else:
            edu_validation = DataValidator.get_edu_group_id(context_data, edu_group_id)
            if not edu_validation[0]:
                return None
            
            edu_group_id_to_use = edu_validation[1]
            endpoint = f"edu-groups/{edu_group_id_to_use}/parallel"
        
        groups_data = await request_handler.client.get(endpoint)
        return self._filter_groups_by_type(groups_data)
    
    async def _get_all_school_groups(
        self,
        request_handler: RequestHandler,
        context_data: Dict[str, Any],
        school_id: Optional[str]
    ) -> Optional[List[Dict[str, str]]]:
        """Получает все группы школы через учителей"""
        school_validation = DataValidator.get_school_id(context_data, school_id)
        if not school_validation[0]:
            return None
        
        school_id_to_use = school_validation[1]
        
        teachers_endpoint = f"schools/{school_id_to_use}/teachers"
        teachers_data = await request_handler.client.get(teachers_endpoint)
        
        endpoints = [
            f"persons/{teacher.get('Id')}/edu-groups"
            for teacher in teachers_data
        ]
        
        results = await request_handler.execute_parallel_requests(endpoints)
        
        all_groups_set = set()
        for teacher, result in zip(teachers_data, results):
            if isinstance(result, Exception):
                logger.warning(f"Error getting groups for teacher {teacher.get('Id')}: {result}")
                continue
            
            for group in result:
                if group.get("type") == GROUP_TYPE_FILTER:
                    all_groups_set.add((group.get("id_str"), group.get("name")))
        
        return [{"id": g[0], "name": g[1]} for g in sorted(all_groups_set)]
    
    def _filter_groups_by_type(self, groups_data: List[Dict]) -> List[Dict[str, str]]:
        """Фильтрует группы по типу Group"""
        return [
            {
                "id": group.get("id_str"),
                "name": group.get("name")
            }
            for group in groups_data
            if group.get("type") == GROUP_TYPE_FILTER
        ]
