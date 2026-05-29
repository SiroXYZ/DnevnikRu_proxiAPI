"""Обработчик для endpoint /marks"""
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime, timedelta
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler


# ==================== КОНСТАНТЫ ====================
DATE_FORMAT_INPUT = "%Y-%m-%d"
DATE_FORMAT_LESSON = "%Y-%m-%dT%H:%M:%S"
DATE_FORMAT_MARK = "%Y-%m-%dT%H:%M:%S.%f"
DATE_FORMAT_OUTPUT_SHORT = "%d.%m.%Y"
DATE_FORMAT_OUTPUT_LONG = "%d.%m.%Y %H:%M"

MARK_DATE_LOOKBACK_DAYS = 60

UNKNOWN_SUBJECT = "Неизвестный предмет"
UNKNOWN_WORK_TYPE = "Неизвестно"
UNKNOWN_LESSON_TITLE = "Неизвестно"
UNKNOWN_DATE = "Неизвестно"
# ==================================================


class MarksHandler:
    """Обработчик данных оценок"""
    
    async def handle(
        self, 
        token: str,
        start_date: str,
        end_date: Optional[str] = None,
        person_id: Optional[str] = None,
        school_id: Optional[str] = None,
        subject: Optional[str] = None,
        by_mark_date: bool = False
    ) -> Dict[str, Any]:
        """
        Получить оценки за период, сгруппированные по предметам
        
        Args:
            token: токен доступа
            start_date: начальная дата (YYYY-MM-DD)
            end_date: конечная дата (YYYY-MM-DD), опционально
            person_id: ID ученика, опционально (если не указан, берется из контекста)
            school_id: ID школы, опционально (если не указан, берется из контекста)
            subject: фильтр по названию предмета, опционально
            by_mark_date: если True, фильтрует по дате выставления оценки, иначе по дате урока
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
                school_id_to_use = school_validation[1]
                # 
                
                date_range = self._calculate_api_date_range(start, end, by_mark_date)
                
                marks_data = await self._fetch_marks(
                    request_handler,
                    person_id_to_use,
                    school_id_to_use,
                    date_range
                )
                
                work_types_cache = await self._fetch_work_types(
                    request_handler,
                    school_id_to_use
                )
                
                formatted_marks = await self._format_marks(
                    marks_data,
                    request_handler,
                    work_types_cache,
                    subject,
                    by_mark_date,
                    start_date,
                    end_date or start_date
                )
            
            logger.info(f"Marks retrieved successfully for {start_date} to {end_date or start_date}")
            return {
                "success": True,
                "data": formatted_marks
            }
        except Exception as e:
            logger.error(f"Error in MarksHandler: {str(e)}")
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
    
    def _calculate_api_date_range(
        self,
        start: datetime,
        end: datetime,
        by_mark_date: bool
    ) -> Tuple[str, str]:
        """Вычисляет диапазон дат для API запроса"""
        if by_mark_date:
            start_for_api = (end - timedelta(days=MARK_DATE_LOOKBACK_DAYS)).strftime(DATE_FORMAT_INPUT)
            end_for_api = end.strftime(DATE_FORMAT_INPUT)
        else:
            start_for_api = start.strftime(DATE_FORMAT_INPUT)
            end_for_api = end.strftime(DATE_FORMAT_INPUT)
        
        return start_for_api, end_for_api
    
    async def _fetch_marks(
        self,
        request_handler: RequestHandler,
        person_id: str,
        school_id: str,
        date_range: Tuple[str, str]
    ) -> List[Dict]:
        """Получает оценки за период"""
        start_for_api, end_for_api = date_range
        endpoint = f"persons/{person_id}/schools/{school_id}/marks/{start_for_api}/{end_for_api}"
        return await request_handler.client.get(endpoint)
    
    async def _fetch_work_types(
        self,
        request_handler: RequestHandler,
        school_id: str
    ) -> Dict[str, str]:
        """Получает типы работ школы"""
        work_types_data = await request_handler.client.get(f"work-types/{school_id}")
        return {
            str(wt.get("id")): wt.get("title", UNKNOWN_WORK_TYPE)
            for wt in work_types_data
        }
    
    async def _format_marks(
        self,
        marks_data: List[Dict],
        request_handler: RequestHandler,
        work_types_cache: Dict[str, str],
        subject_filter: Optional[str] = None,
        by_mark_date: bool = False,
        start_date_str: Optional[str] = None,
        end_date_str: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Форматирует оценки в нужный формат с параллельной загрузкой данных"""
        unique_work_ids, unique_lesson_ids = self._extract_unique_ids(marks_data)
        
        works_cache = await self._fetch_works(request_handler, unique_work_ids)
        lessons_cache = await self._fetch_lessons(request_handler, unique_lesson_ids)
        
        formatted = {}
        for mark in marks_data:
            try:
                formatted_mark = self._process_mark(
                    mark,
                    works_cache,
                    lessons_cache,
                    work_types_cache,
                    subject_filter,
                    by_mark_date,
                    start_date_str,
                    end_date_str
                )
                
                if formatted_mark:
                    subject_name = formatted_mark["subject_name"]
                    if subject_name not in formatted:
                        formatted[subject_name] = []
                    formatted[subject_name].append(formatted_mark["mark_entry"])
            
            except Exception as e:
                logger.warning(f"Error processing mark: {str(e)}")
                continue
        
        for subject in formatted:
            formatted[subject].sort(key=lambda x: x["mark_date"])
        
        return formatted
    
    def _extract_unique_ids(self, marks_data: List[Dict]) -> Tuple[set, set]:
        """Извлекает уникальные ID работ и уроков"""
        unique_work_ids = set()
        unique_lesson_ids = set()
        
        for mark in marks_data:
            work_id = str(mark.get("work_str", ""))
            lesson_id = str(mark.get("lesson_str", ""))
            if work_id:
                unique_work_ids.add(work_id)
            if lesson_id:
                unique_lesson_ids.add(lesson_id)
        
        return unique_work_ids, unique_lesson_ids
    
    async def _fetch_works(
        self,
        request_handler: RequestHandler,
        work_ids: set
    ) -> Dict[str, Dict]:
        """Получает данные о работах параллельно"""
        if not work_ids:
            return {}
        
        endpoints = [f"works/{work_id}" for work_id in work_ids]
        results = await request_handler.execute_parallel_requests(endpoints)
        
        works_cache = {}
        for work_id, result in zip(work_ids, results):
            if not isinstance(result, Exception):
                works_cache[work_id] = result
            else:
                logger.warning(f"Could not fetch work {work_id}: {result}")
        
        return works_cache
    
    async def _fetch_lessons(
        self,
        request_handler: RequestHandler,
        lesson_ids: set
    ) -> Dict[str, Dict]:
        """Получает данные об уроках параллельно"""
        if not lesson_ids:
            return {}
        
        endpoints = [f"lessons/{lesson_id}" for lesson_id in lesson_ids]
        results = await request_handler.execute_parallel_requests(endpoints)
        
        lessons_cache = {}
        for lesson_id, result in zip(lesson_ids, results):
            if not isinstance(result, Exception):
                lessons_cache[lesson_id] = result
            else:
                logger.warning(f"Could not fetch lesson {lesson_id}: {result}")
        
        return lessons_cache
    
    def _process_mark(
        self,
        mark: Dict,
        works_cache: Dict[str, Dict],
        lessons_cache: Dict[str, Dict],
        work_types_cache: Dict[str, str],
        subject_filter: Optional[str],
        by_mark_date: bool,
        start_date_str: Optional[str],
        end_date_str: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        work_id = str(mark.get("work_str", ""))
        lesson_id = str(mark.get("lesson_str", ""))
        mark_value = mark.get("value", "")
        mark_date = mark.get("date", "")
        work_type_id = str(mark.get("workType", ""))
        mood = mark.get("mood", "")
        
        work_data = works_cache.get(work_id, {})
        lesson_data = lessons_cache.get(lesson_id, {})
        
        subject_name = DataValidator.safe_get_nested(
            lesson_data, "subject", "name",
            default=UNKNOWN_SUBJECT
        )
        
        if subject_filter and subject_name.lower() != subject_filter.lower():
            return None
        
        work_type_name = work_types_cache.get(work_type_id, UNKNOWN_WORK_TYPE)
        lesson_title = lesson_data.get("title", UNKNOWN_LESSON_TITLE)
        
        lesson_date_str = self._format_date(
            lesson_data.get("date", ""),
            DATE_FORMAT_LESSON,
            DATE_FORMAT_OUTPUT_SHORT
        )
        lesson_only_date = self._parse_date(lesson_data.get("date", ""), DATE_FORMAT_LESSON)
        
        mark_date_str = self._format_date(
            mark_date,
            DATE_FORMAT_MARK,
            DATE_FORMAT_OUTPUT_LONG
        )
        mark_only_date = self._parse_date(mark_date, DATE_FORMAT_MARK)
        
        if not self._is_date_in_range(
            lesson_only_date,
            mark_only_date,
            by_mark_date,
            start_date_str,
            end_date_str
        ):
            return None
        
        return {
            "subject_name": subject_name,
            "mark_entry": {
                "work_id": work_id,
                "lesson_date": lesson_date_str,
                "mark_date": mark_date_str,
                "value": str(mark_value),
                "mood": mood,
                "work_type": work_type_name,
                "lesson_title": lesson_title
            }
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
    
    def _parse_date(self, date_str: str, date_format: str) -> Optional[datetime]:
        """Парсит дату в объект datetime"""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, date_format)
        except ValueError:
            return None
    
    def _is_date_in_range(
        self,
        lesson_date: Optional[datetime],
        mark_date: Optional[datetime],
        by_mark_date: bool,
        start_date_str: Optional[str],
        end_date_str: Optional[str]
    ) -> bool:
        """Проверяет, попадает ли дата в диапазон"""
        if not start_date_str or not end_date_str:
            return True
        
        try:
            start = datetime.strptime(start_date_str, DATE_FORMAT_INPUT)
            end = datetime.strptime(end_date_str, DATE_FORMAT_INPUT)
            
            if by_mark_date:
                if mark_date and not (start.date() <= mark_date.date() <= end.date()):
                    return False
            else:
                if lesson_date and not (start.date() <= lesson_date.date() <= end.date()):
                    return False
            
            return True
        except ValueError:
            return True
