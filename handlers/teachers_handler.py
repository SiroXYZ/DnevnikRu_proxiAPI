"""Обработчик для endpoint /teachers"""
from typing import Any, Dict, List, Optional
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler


class TeachersHandler:
    """Обработчик данных учителей школы"""
    
    async def handle(
        self, 
        token: str,
        school_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить список учителей своей школы
        
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
                endpoint = f"schools/{school_id_to_use}/teachers"
                teachers_data = await request_handler.client.get(endpoint)
            
            teachers = self._format_teachers(teachers_data)
            
            logger.info(f"Teachers data processed successfully for school {school_id_to_use}")
            return {
                "success": True,
                "data": {
                    "teachers": teachers
                }
            }
        except Exception as e:
            logger.error(f"Error in TeachersHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_teachers(self, teachers_data: List[Dict]) -> List[Dict[str, Any]]:
        """Форматирует данные учителей"""
        teachers = []
        for teacher in teachers_data:
            first_name = teacher.get("FirstName", "").strip()
            middle_name = teacher.get("MiddleName", "").strip()
            last_name = teacher.get("LastName", "").strip()
            full_name = f"{first_name} {middle_name} {last_name}".strip()
            
            teachers.append({
                "Id": teacher.get("Id"),
                "UserId": teacher.get("UserId"),
                "FullName": full_name,
                "DateBirth": teacher.get("DateBirth"),
                "Email": teacher.get("Email"),
                "Subjects": teacher.get("Subjects"),
                "NameTeacherPosition": teacher.get("NameTeacherPosition")
            })
        
        return teachers
