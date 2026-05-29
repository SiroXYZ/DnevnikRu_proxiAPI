"""Обработчик для endpoint /context"""
from typing import Any, Dict
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.request_handler import RequestHandler


class ContextHandler:
    """Обработчик данных контекста пользователя"""
    
    async def handle(self, token: str) -> Dict[str, Any]:
        try:
            client = DnevnikAPIClient(token=token)
            request_handler = RequestHandler(client)
            
            async with client:
                raw_data = await request_handler.get_context()
                user_id = raw_data.get("userId")
                
                user_data = await request_handler.client.get(f"users/{user_id}")
                timezone = user_data.get("timezone")
                birthday = user_data.get("birthday")
            
            processed = self._format_context_data(raw_data, timezone, birthday)
            
            logger.info("Context data processed successfully")
            return {
                "success": True,
                "data": processed
            }
        except Exception as e:
            logger.error(f"Error in ContextHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_context_data(
        self,
        raw_data: Dict[str, Any],
        timezone: Any,
        birthday: Any
    ) -> Dict[str, Any]:
        school_names = [
            school.get("name")
            for school in raw_data.get("schools", [])
            if school.get("name")
        ]
        group_names = [
            group.get("name")
            for group in raw_data.get("eduGroups", [])
            if group.get("name")
        ]
        group_ids_str = [
            group.get("id_str")
            for group in raw_data.get("eduGroups", [])
            if group.get("id_str")
        ]
        
        return {
            "children": raw_data.get("children", []),
            "userId": raw_data.get("userId"),
            "personId": raw_data.get("personId"),
            "groupIds": group_ids_str,
            "schoolId": raw_data.get("schoolIds", []),
            "shortName": raw_data.get("shortName"),
            "schoolName": school_names,
            "groupName": group_names,
            "birthday": birthday,
            "timezone": timezone
        }
