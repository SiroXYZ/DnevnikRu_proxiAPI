"""Обработчик для endpoint /persons"""
from typing import Any, Dict, List, Optional
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler


class PersonsHandler:
    """Обработчик данных учеников в группе"""
    
    async def handle(
        self, 
        token: str, 
        edu_group_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить список учеников в группе
        
        Args:
            token: токен доступа
            edu_group_id: ID учебной группы. Если None, получает из контекста
        """
        try:
            client = DnevnikAPIClient(token=token)
            request_handler = RequestHandler(client)
            
            async with client:
                if not edu_group_id:
                    context_data = await request_handler.get_context()
                    edu_validation = DataValidator.get_edu_groups(context_data)
                    if not edu_validation[0]:
                        return {
                            "success": False,
                            "error": edu_validation[2]
                        }
                    edu_group_id = edu_validation[1]
                
                endpoint = f"edu-groups/{edu_group_id}/persons"
                persons_data = await request_handler.client.get(endpoint)
            
            persons = self._format_persons(persons_data)
            
            logger.info(f"Persons data processed successfully for group {edu_group_id}")
            return {
                "success": True,
                "data": {
                    "persons": persons
                }
            }
        except Exception as e:
            logger.error(f"Error in PersonsHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_persons(self, persons_data: List[Dict]) -> List[Dict[str, str]]:
        """Форматирует данные учеников"""
        return [
            {
                "id": person.get("id_str"),
                "userId": person.get("userId_str"),
                "shortName": person.get("shortName")
            }
            for person in persons_data
        ]
