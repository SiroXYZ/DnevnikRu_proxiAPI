"""Обработчик для endpoint /relatives"""
from typing import Any, Dict, List
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.request_handler import RequestHandler


class RelativesHandler:
    """Обработчик данных относителей пользователя"""
    
    async def handle(self, token: str) -> Dict[str, Any]:
        """
        Получить список относителей (родителей) текущего пользователя
        
        Args:
            token: токен доступа
        """
        try:
            client = DnevnikAPIClient(token=token)
            request_handler = RequestHandler(client)
            
            async with client:
                endpoint = "users/me/relatives"
                relatives_data = await request_handler.client.get(endpoint)
            
            relatives = self._format_relatives(relatives_data)
            
            logger.info("Relatives data processed successfully")
            return {
                "success": True,
                "data": {
                    "relatives": relatives
                }
            }
        except Exception as e:
            logger.error(f"Error in RelativesHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_relatives(self, relatives_data: List[Dict]) -> List[Dict[str, Any]]:
        """Форматирует данные относителей"""
        return [
            {
                "type": relative.get("type"),
                "personId": relative.get("person", {}).get("id"),
                "userId": relative.get("person", {}).get("userId"),
                "shortName": relative.get("person", {}).get("shortName")
            }
            for relative in relatives_data
        ]
