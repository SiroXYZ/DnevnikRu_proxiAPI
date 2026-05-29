"""Обработчик для endpoint /entries"""
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler


# ==================== КОНСТАНТЫ ====================
MAX_DAYS_PER_REQUEST = 30
DATE_FORMAT_INPUT = "%Y-%m-%d"
DATE_FORMAT_LESSON = "%Y-%m-%dT%H:%M:%S"
DATE_FORMAT_CREATED = "%Y-%m-%dT%H:%M:%S.%f"
DATE_FORMAT_OUTPUT_SHORT = "%d.%m.%Y"
DATE_FORMAT_OUTPUT_LONG = "%d.%m.%Y %H:%M"
UNKNOWN_SUBJECT = "Неизвестный предмет"
UNKNOWN_DATE = "Неизвестно"
# ==================================================


class EntriesHandler:
    """Обработчик данных записей в логе уроков (logEntries)"""
    
    def __init__(self):
        self.max_days_per_request = MAX_DAYS_PER_REQUEST
    
    async def handle(
        self, 
        token: str,
        start_date: str,
        end_date: Optional[str] = None,
        person_id: Optional[str] = None,
        school_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить записи логов за период
        
        Если период больше MAX_DAYS_PER_REQUEST дней, разбивает запрос на несколько и объединяет результаты
        
        Args:
            token: токен доступа
            start_date: начальная дата (YYYY-MM-DD)
            end_date: конечная дата (YYYY-MM-DD), опционально (если не указана, используется start_date)
            person_id: ID ученика, опционально (если не указан, берется из контекста)
            school_id: ID школы, опционально (для валидации, если не указан, берется из контекста)
        """
        try:
            validation_result = self._validate_dates(start_date, end_date)
            if not validation_result["success"]:
                return validation_result
            start, end = validation_result["dates"]
            
            client = DnevnikAPIClient(token=token)
            request_handler = RequestHandler(client)
            
            async with client:
                context_data = await request_handler.get_context()
                
                person_validation = DataValidator.get_person_id(context_data, person_id)
                if not person_validation[0]:
                    return {
                        "success": False,
                        "error": person_validation[2]
                    }
                person_id_to_use = person_validation[1]
                
                school_validation = DataValidator.get_school_id(context_data, school_id)
                if not school_validation[0]:
                    return {
                        "success": False,
                        "error": school_validation[2]
                    }
                
                date_ranges = self._split_date_range(start, end)
                
                all_log_entries, all_lessons = await self._fetch_entries_data(
                    request_handler,
                    person_id_to_use,
                    date_ranges
                )
                
                formatted_entries = await self._format_entries(all_log_entries, all_lessons)
                
                logger.info(f"Entries retrieved successfully for {start_date} to {end_date or start_date}")
                return {
                    "success": True,
                    "data": formatted_entries
                }
        
        except Exception as e:
            logger.error(f"Error in EntriesHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _validate_dates(self, start_date: str, end_date: Optional[str]) -> Dict[str, Any]:
        """Валидирует и парсит даты"""
        start_valid, start_obj, start_error = DataValidator.validate_date_format(start_date)
        if not start_valid:
            return {
                "success": False,
                "error": start_error
            }
        
        end_obj = start_obj
        if end_date:
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
    
    def _split_date_range(self, start: datetime, end: datetime) -> List[Tuple[datetime, datetime]]:
        """Разбивает диапазон дат на интервалы по MAX_DAYS_PER_REQUEST дней"""
        ranges = []
        current_start = start
        
        while current_start <= end:
            current_end = min(
                current_start + timedelta(days=self.max_days_per_request - 1),
                end
            )
            ranges.append((current_start, current_end))
            current_start = current_end + timedelta(days=1)
        
        return ranges
    
    async def _fetch_entries_data(
        self,
        request_handler: RequestHandler,
        person_id: str,
        date_ranges: List[Tuple[datetime, datetime]]
    ) -> Tuple[List[Dict], Dict[str, Dict]]:
        """Получает данные записей для всех интервалов дат"""
        endpoints = self._build_endpoints(person_id, date_ranges)
        results = await request_handler.execute_parallel_requests(endpoints)
        
        return self._process_entries_results(results, person_id)
    
    def _build_endpoints(
        self,
        person_id: str,
        date_ranges: List[Tuple[datetime, datetime]]
    ) -> List[str]:
        """Строит список endpoint'ов для запросов"""
        return [
            f"persons/{person_id}/lesson-log-entries?"
            f"startDate={range_start.strftime(DATE_FORMAT_INPUT)}&"
            f"endDate={range_end.strftime(DATE_FORMAT_INPUT)}"
            for range_start, range_end in date_ranges
        ]
    
    def _process_entries_results(
        self,
        results: List[Any],
        person_id: str
    ) -> Tuple[List[Dict], Dict[str, Dict]]:
        """Обрабатывает результаты запросов"""
        all_log_entries = []
        all_lessons = {}
        
        for response in results:
            if isinstance(response, Exception):
                logger.warning(f"Error fetching entries: {response}")
                continue
            
            if "logEntries" in response:
                self._enrich_entries_with_person_id(response["logEntries"], person_id)
                all_log_entries.extend(response["logEntries"])
            
            if "lessons" in response:
                self._merge_lessons(all_lessons, response["lessons"])
        
        return all_log_entries, all_lessons
    
    def _enrich_entries_with_person_id(self, entries: List[Dict], person_id: str) -> None:
        """Добавляет person_id к записям"""
        for entry in entries:
            entry["person_id"] = person_id
    
    def _merge_lessons(self, all_lessons: Dict[str, Dict], lessons: List[Dict]) -> None:
        """Объединяет уроки, избегая дубликатов"""
        for lesson in lessons:
            lesson_id = str(lesson.get("id_str", lesson.get("id", "")))
            if lesson_id and lesson_id not in all_lessons:
                all_lessons[lesson_id] = lesson
    
    async def _format_entries(
        self,
        log_entries: List[Dict],
        lessons: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """Форматирует записи логов в нужный формат"""
        formatted = []
        
        for entry in log_entries:
            try:
                formatted_entry = self._format_single_entry(entry, lessons)
                if formatted_entry:
                    formatted.append(formatted_entry)
            except Exception as e:
                logger.warning(f"Error formatting entry: {str(e)}")
                continue
        
        formatted.sort(key=lambda x: x["createdDate"])
        return formatted
    
    def _format_single_entry(
        self,
        entry: Dict,
        lessons: Dict[str, Dict]
    ) -> Optional[Dict[str, Any]]:
        """Форматирует одну запись"""
        lesson_str = str(entry.get("lesson_str", ""))
        lesson_data = lessons.get(lesson_str, {})
        
        subject_name = DataValidator.safe_get_nested(
            lesson_data, "subject", "name",
            default=UNKNOWN_SUBJECT
        )
        
        lesson_date = self._format_date(
            lesson_data.get("date", ""),
            DATE_FORMAT_LESSON,
            DATE_FORMAT_OUTPUT_SHORT
        )
        
        created_date = self._format_date(
            entry.get("createdDate", ""),
            DATE_FORMAT_CREATED,
            DATE_FORMAT_OUTPUT_LONG
        )
        
        return {
            "lesson_str": lesson_str,
            "name": subject_name,
            "status": entry.get("status", ""),
            "date": lesson_date,
            "createdDate": created_date
        }
    
    def _format_date(self, date_str: str, input_format: str, output_format: str) -> str:
        """Форматирует дату из одного формата в другой"""
        if not date_str:
            return UNKNOWN_DATE
        
        try:
            date_obj = datetime.strptime(date_str, input_format)
            return date_obj.strftime(output_format)
        except ValueError:
            return UNKNOWN_DATE
