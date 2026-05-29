"""Обработчик для endpoint /schedules-person/{person_id}/{group_id}/{start_date}"""
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler
from handlers.lessons_handler import LessonsHandler


class SchedulesPersonHandler:
    """Обработчик расписания ученика с деталями уроков"""
    
    MAX_DAYS_PER_REQUEST = 30
    
    async def handle(
        self, 
        token: str, 
        person_id: str,
        group_id: str,
        start_date: str,
        end_date: Optional[str] = None,
        school_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить расписание ученика на определенную дату(ы)
        
        Args:
            token: токен доступа
            person_id: ID ученика (используется для получения посещаемости)
            group_id: ID группы
            start_date: дата начала (YYYY-MM-DD)
            end_date: дата конца (YYYY-MM-DD), если не указана - используется start_date
            school_id: ID школы, опционально (если не указан, берется из контекста)
        """
        try:
            if end_date is None:
                end_date = start_date
            
            validation_result = self._validate_dates(start_date, end_date)
            if not validation_result["success"]:
                return validation_result
            
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
                
                timetable_map = await self._get_timetable(
                    request_handler,
                    group_id,
                    context_data.get("groupIds", [])
                )
                
                lessons_ids_data = await request_handler.client.get(
                    f"edu-groups/{group_id}/lessons/{start_date}/{end_date}"
                )
                
                if not lessons_ids_data:
                    logger.warning(f"No lessons found for group {group_id} on {start_date}")
                    return {
                        "success": True,
                        "data": {}
                    }
                
                lesson_details = await self._fetch_lesson_details(
                    token,
                    lessons_ids_data
                )
                
                attendance_map = await self._get_attendance(
                    request_handler,
                    person_id,
                    start_date,
                    end_date
                )
                
                formatted_schedule = self._format_schedule(
                    lessons_ids_data,
                    lesson_details,
                    attendance_map,
                    timetable_map
                )
                
                logger.info(f"Schedule for person {person_id} retrieved successfully")
                return {
                    "success": True,
                    "data": formatted_schedule
                }
        
        except Exception as e:
            logger.error(f"Error in SchedulesPersonHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _validate_dates(self, start_date: str, end_date: str) -> Dict[str, Any]:
        """Валидирует и парсит даты"""
        start_valid, start_obj, start_error = DataValidator.validate_date_format(start_date)
        if not start_valid:
            return {
                "success": False,
                "error": start_error
            }
        
        end_valid, end_obj, end_error = DataValidator.validate_date_format(end_date)
        if not end_valid:
            return {
                "success": False,
                "error": end_error
            }
        
        range_valid, range_error = DataValidator.validate_date_range(start_obj, end_obj)
        if not range_valid:
            return {
                "success": False,
                "error": range_error
            }
        
        return {
            "success": True,
            "dates": (start_obj, end_obj)
        }
    
    async def _get_timetable(
        self,
        request_handler: RequestHandler,
        group_id: str,
        main_group_ids: List[str]
    ) -> Dict[int, str]:
        """Получает расписание уроков группы (время начала и окончания каждого урока)"""
        try:
            timetable_map = {}
            
            endpoint = f"edu-groups/{group_id}/timetables"
            if main_group_ids and main_group_ids[0] == group_id:
                timetable_data = await request_handler.client.get(endpoint)
            else:
                logger.warning(f"No access rights for timetables for group {group_id}")
                return timetable_map
            
            if not timetable_data:
                logger.warning(f"No timetable found for group {group_id}")
                return timetable_map
            
            items = timetable_data.get("Items", [])
            
            for item in items:
                lesson_number = item.get("LessonNumber", 0)
                if lesson_number <= 0:
                    continue
                
                start_str = item.get("Start", "")
                finish_str = item.get("Finish", "")
                
                start_time = self._extract_time(start_str)
                finish_time = self._extract_time(finish_str)
                
                if start_time and finish_time:
                    lesson_time = f"{start_time} - {finish_time}"
                    timetable_map[lesson_number] = lesson_time
            
            logger.info(f"Timetable loaded for group {group_id}: {len(timetable_map)} lessons")
            return timetable_map
        
        except Exception as e:
            logger.warning(f"Error getting timetable: {str(e)}")
            return {}
    
    def _extract_time(self, iso_datetime_str: str) -> Optional[str]:
        """Извлекает время из ISO 8601 строки (HH:MM)"""
        if not iso_datetime_str:
            return None
        
        try:
            dt = datetime.fromisoformat(iso_datetime_str.replace("Z", "+00:00"))
            return dt.strftime("%H:%M")
        except Exception:
            return None
    
    async def _fetch_lesson_details(
        self,
        token: str,
        lessons_ids_data: List[Dict]
    ) -> Dict[str, Dict]:
        """Загружает детали всех уроков параллельно"""
        import asyncio
        
        lessons_handler = LessonsHandler()
        lesson_tasks = [
            lessons_handler.handle(token=token, lesson_id=lesson.get("id_str", lesson.get("id", "")))
            for lesson in lessons_ids_data
        ]
        lesson_results = await asyncio.gather(*lesson_tasks, return_exceptions=True)
        
        lesson_details = {}
        for lesson_data, result in zip(lessons_ids_data, lesson_results):
            if isinstance(result, Exception):
                logger.warning(f"Error loading lesson {lesson_data.get('id')}: {result}")
                continue
            
            if not result.get("success"):
                logger.warning(f"Failed to load lesson {lesson_data.get('id')}")
                continue
            
            lesson_id_str = lesson_data.get("id_str", lesson_data.get("id", ""))
            lesson_details[lesson_id_str] = result.get("data", {})
        
        return lesson_details
    
    async def _get_attendance(
        self,
        request_handler: RequestHandler,
        person_id: str,
        start_date: str,
        end_date: str
    ) -> Dict[str, str]:
        """Получает информацию о посещаемости ученика за период"""
        try:
            attendance_map = {}
            
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            
            date_ranges = self._split_date_range(start_dt, end_dt)
            
            requests = [
                (
                    f"persons/{person_id}/lesson-log-entries",
                    {
                        "startDate": range_start.strftime("%Y-%m-%d"),
                        "endDate": range_end.strftime("%Y-%m-%d")
                    }
                )
                for range_start, range_end in date_ranges
            ]
            
            results = await request_handler.execute_parallel_requests_with_params(requests)
            
            for response in results:
                if isinstance(response, Exception):
                    logger.warning(f"Error fetching attendance: {response}")
                    continue
                
                log_entries = response.get("logEntries", [])
                
                for entry in log_entries:
                    if not entry:
                        continue
                    
                    lesson_id = entry.get("lesson_str", entry.get("lesson", ""))
                    status = entry.get("status", "")
                    
                    if lesson_id:
                        mapped_status = self._map_attendance_status(status)
                        attendance_map[str(lesson_id)] = mapped_status
            
            logger.info(f"Attendance loaded: {len(attendance_map)} entries")
            return attendance_map
        
        except Exception as e:
            logger.warning(f"Error getting attendance: {str(e)}")
            return {}
    
    def _map_attendance_status(self, status: str) -> str:
        """Маппирует статус посещаемости"""
        if status == "Pass":
            return "Отсутствовал"
        elif status == "Ill":
            return "Болел"
        else:
            return "Присутствовал"
    
    def _split_date_range(self, start: datetime, end: datetime) -> List[tuple]:
        """Разбивает диапазон дат на интервалы по MAX_DAYS_PER_REQUEST дней"""
        ranges = []
        current_start = start
        
        while current_start <= end:
            current_end = min(
                current_start + timedelta(days=self.MAX_DAYS_PER_REQUEST - 1),
                end
            )
            ranges.append((current_start, current_end))
            current_start = current_end + timedelta(days=1)
        
        return ranges
    
    def _format_schedule(
        self,
        lessons_ids_data: List[Dict],
        lesson_details: Dict[str, Dict],
        attendance_map: Dict[str, str],
        timetable_map: Dict[int, str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Форматирует расписание"""
        formatted_schedule = {}
        
        for lesson_data in lessons_ids_data:
            date_str = lesson_data.get("date", "")
            if not date_str:
                continue
            
            try:
                lesson_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                date_key = lesson_date.strftime("%d.%m.%Y")
            except Exception:
                continue
            
            if date_key not in formatted_schedule:
                formatted_schedule[date_key] = []
            
            lesson_id_str = lesson_data.get("id_str", lesson_data.get("id", ""))
            lesson_info = lesson_details.get(lesson_id_str, {})
            
            lesson_number = lesson_data.get("number", 0)
            lesson_time = timetable_map.get(lesson_number, "Недоступно")
            
            teacher_name = "Неизвестный учитель"
            if lesson_info.get("teachers"):
                teacher_name = lesson_info["teachers"][0].get("FullName", "Неизвестный учитель")
            
            attendance = attendance_map.get(lesson_id_str, "Неизвестно")
            
            schedule_item = {
                "lesson_id": lesson_id_str,
                "lesson_number": lesson_number,
                "time": lesson_time,
                "subject": lesson_info.get("subject", "Неизвестный предмет"),
                "title": lesson_info.get("title", ""),
                "teacher": teacher_name,
                "homeworks": lesson_info.get("homeworks", []),
                "works": lesson_info.get("works", []),
                "attendance": attendance
            }
            
            formatted_schedule[date_key].append(schedule_item)
        
        for date_key in formatted_schedule:
            formatted_schedule[date_key].sort(key=lambda x: x["lesson_number"])
        
        return formatted_schedule
