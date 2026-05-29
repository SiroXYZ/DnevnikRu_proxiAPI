"""Обработчик для endpoint /timetables"""
from typing import Any, Dict, Optional
from datetime import datetime
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.request_handler import RequestHandler


class TimetablesHandler:
    """Обработчик расписания звонков группы"""
    
    async def handle(self, token: str, group_id: str) -> Dict[str, Any]:
        """
        Получить расписание звонков группы
        
        Args:
            token: токен доступа
            group_id: ID группы
        """
        try:
            client = DnevnikAPIClient(token=token)
            request_handler = RequestHandler(client)
            
            async with client:
                endpoint = f"edu-groups/{group_id}/timetables"
                timetable_data = await request_handler.client.get(endpoint)
                
                if not timetable_data:
                    return {
                        "success": False,
                        "error": f"No timetable found for group {group_id}"
                    }
                
                formatted_timetable = self._format_timetable(timetable_data)
                
                logger.info(f"Timetable for group {group_id} retrieved successfully")
                return {
                    "success": True,
                    "data": formatted_timetable
                }
        
        except Exception as e:
            logger.error(f"Error in TimetablesHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_timetable(self, timetable_data: Dict[str, Any]) -> Dict[str, Any]:
        """Форматирует расписание звонков в удобный формат"""
        try:
            formatted_items = []
            
            name = timetable_data.get("Name", "Основное расписание")
            first_lesson_number = timetable_data.get("FirstLessonNumber", 1)
            
            items = timetable_data.get("Items", [])
            
            for item in items:
                lesson_number = item.get("LessonNumber", 0)
                if lesson_number <= 0:
                    continue
                
                start_str = item.get("Start", "")
                finish_str = item.get("Finish", "")
                
                start_time = self._extract_time(start_str)
                finish_time = self._extract_time(finish_str)
                
                lesson_item = {
                    "lesson_number": lesson_number,
                    "start_time": start_time,
                    "finish_time": finish_time,
                    "time": f"{start_time} - {finish_time}" if start_time and finish_time else "Неизвестно",
                }
                
                formatted_items.append(lesson_item)
            
            formatted_items.sort(key=lambda x: x["lesson_number"])
            
            return {
                "name": name,
                "first_lesson_number": first_lesson_number,
                "lessons": formatted_items
            }
        
        except Exception as e:
            logger.error(f"Error formatting timetable: {str(e)}")
            raise
    
    def _extract_time(self, iso_datetime_str: str) -> Optional[str]:
        """Извлекает время из ISO 8601 строки (HH:MM)"""
        if not iso_datetime_str:
            return None
        
        try:
            dt = datetime.fromisoformat(iso_datetime_str.replace("Z", "+00:00"))
            return dt.strftime("%H:%M")
        except Exception:
            return None
