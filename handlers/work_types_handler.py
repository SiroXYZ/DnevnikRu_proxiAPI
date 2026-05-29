"""Обработчик для endpoint /work-types"""
from typing import Any, Dict, List, Optional
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler


class WorkTypesHandler:
    """Обработчик данных типов работ"""
    
    async def handle(
        self, 
        token: str,
        school_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить список типов работ школы
        
        Args:
            token: токен доступа
            school_id: ID школы, опционально (если не указан, берется из контекста)
        """
        try:
            client = DnevnikAPIClient(token=token)
            request_handler = RequestHandler(client)
            
            async with client:
                context_data = await request_handler.get_context()
                
                school_validation = DataValidator.get_school_ids(
                    context_data,
                    [school_id] if school_id else None
                )
                if not school_validation[0]:
                    return {
                        "success": False,
                        "error": school_validation[2]
                    }
                
                school_id_to_use = school_validation[1][0]
                endpoint = f"work-types/{school_id_to_use}"
                work_types_data = await request_handler.client.get(endpoint)
            
            work_types = self._format_work_types(work_types_data)
            
            logger.info(f"Work types data processed successfully for school {school_id_to_use}")
            return {
                "success": True,
                "data": {
                    "workTypes": work_types
                }
            }
        except Exception as e:
            logger.error(f"Error in WorkTypesHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_work_types(self, work_types_data: List[Dict]) -> List[Dict[str, Any]]:
        """Форматирует данные типов работ"""
        return [
            {
                "id": work_type.get("id_str"),
                "title": work_type.get("title"),
                "abbr": work_type.get("abbr"),
                "weight": work_type.get("weight")
            }
            for work_type in work_types_data
        ]
