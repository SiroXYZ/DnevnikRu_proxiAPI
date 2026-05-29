"""Обработчик для endpoint /subjects"""
from typing import Any, Dict, List, Optional
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler


class SubjectsHandler:
    """Обработчик данных предметов в группе или школе"""
    
    async def handle(
        self, 
        token: str, 
        edu_group_id: Optional[str] = None,
        all: bool = False,
        school_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить список предметов в группе или во всей школе
        
        Args:
            token: токен доступа
            edu_group_id: ID учебной группы. Если None, получает из контекста
            all: если True, получает предметы всей школы. Если False, получает по группе
            school_id: ID школы, опционально (если не указан, берется из контекста)
        """
        try:
            client = DnevnikAPIClient(token=token)
            request_handler = RequestHandler(client)
            
            async with client:
                context_data = await request_handler.get_context()
                
                if all:
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
                    endpoint = f"schools/{school_id_to_use}/subjects"
                else:
                    edu_validation = DataValidator.get_edu_groups(context_data, edu_group_id)
                    if not edu_validation[0]:
                        return {
                            "success": False,
                            "error": edu_validation[2]
                        }
                    edu_group_id_to_use = edu_validation[1]
                    endpoint = f"edu-groups/{edu_group_id_to_use}/subjects"
                
                subjects_data = await request_handler.client.get(endpoint)
            
            subjects = self._format_subjects(subjects_data)
            
            logger.info("Subjects data processed successfully")
            return {
                "success": True,
                "data": {
                    "subjects": subjects
                }
            }
        except Exception as e:
            logger.error(f"Error in SubjectsHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_subjects(self, subjects_data: List[Dict]) -> List[Dict[str, str]]:
        """Форматирует данные предметов"""
        return [
            {
                "id": subject.get("id_str"),
                "name": subject.get("name")
            }
            for subject in subjects_data
        ]
