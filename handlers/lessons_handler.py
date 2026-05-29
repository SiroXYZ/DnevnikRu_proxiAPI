"""Обработчик для endpoint /lessons/{lesson_id}"""
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler


# ==================== КОНСТАНТЫ ====================
DATE_FORMAT_LESSON = "%Y-%m-%dT%H:%M:%S"
DATE_FORMAT_OUTPUT_SHORT = "%d.%m.%Y"
DATE_FORMAT_OUTPUT_LONG = "%d.%m.%Y %H:%M"
DATE_FORMAT_ISO = "%Y-%m-%dT%H:%M:%S.%f"

WORK_TYPE_HOMEWORK = "Homework"
UNKNOWN_SUBJECT = "Неизвестный предмет"
UNKNOWN_WORK_TYPE = "Неизвестно"
UNKNOWN_TEACHER = "Неизвестный учитель"
# ==================================================


class LessonsHandler:
    """Обработчик данных об уроке"""
    
    async def handle(
        self, 
        token: str, 
        lesson_id: str,
        school_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить информацию об уроке по ID
        
        Args:
            token: токен доступа
            lesson_id: ID урока
            school_id: ID школы, опционально (если не указан, берется из контекста)
        """
        try:
            client = DnevnikAPIClient(token=token)
            request_handler = RequestHandler(client)
            
            async with client:
                context_data = await request_handler.get_context()
                
                lesson_data = await request_handler.client.get(f"lessons/{lesson_id}")
                
                if not lesson_data:
                    return {
                        "success": False,
                        "error": f"Lesson {lesson_id} not found"
                    }
                
                school_validation = DataValidator.get_school_id(context_data, school_id)
                if not school_validation[0]:
                    return {
                        "success": False,
                        "error": school_validation[2]
                    }
                school_id_to_use = school_validation[1]
                
                work_types_by_id = await self._fetch_work_types(
                    request_handler,
                    school_id_to_use
                )
                
                teachers_by_id = await self._fetch_teachers(
                    request_handler,
                    school_id_to_use
                )
                
                formatted_lesson = await self._format_lesson(
                    lesson_data, 
                    work_types_by_id, 
                    teachers_by_id,
                    request_handler
                )
                
                logger.info(f"Lesson {lesson_id} retrieved successfully")
                return {
                    "success": True,
                    "data": formatted_lesson
                }
        
        except Exception as e:
            logger.error(f"Error in LessonsHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _fetch_work_types(
        self,
        request_handler: RequestHandler,
        school_id: str
    ) -> Dict[str, str]:
        """Получает типы работ школы"""
        try:
            work_types_data = await request_handler.client.get(f"work-types/{school_id}")
            return {
                str(wt.get("id")): wt.get("title", UNKNOWN_WORK_TYPE)
                for wt in work_types_data
            }
        except Exception as e:
            logger.warning(f"Error fetching work types: {str(e)}")
            return {}
    
    async def _fetch_teachers(
        self,
        request_handler: RequestHandler,
        school_id: str
    ) -> Dict[int, str]:
        """Получает словарь учителей школы"""
        try:
            teachers_data = await request_handler.client.get(f"schools/{school_id}/teachers")
            teachers_by_id = {}
            for teacher in teachers_data:
                full_name = self._build_teacher_full_name(teacher)
                teachers_by_id[teacher.get("Id")] = full_name or UNKNOWN_TEACHER
            return teachers_by_id
        except Exception as e:
            logger.warning(f"Error fetching teachers: {str(e)}")
            return {}
    
    def _build_teacher_full_name(self, teacher: Dict) -> str:
        """Строит полное имя учителя"""
        first_name = teacher.get("FirstName", "").strip()
        middle_name = teacher.get("MiddleName", "").strip()
        last_name = teacher.get("LastName", "").strip()
        return f"{first_name} {middle_name} {last_name}".strip()
    
    async def _format_lesson(
        self, 
        lesson: Dict[str, Any],
        work_types_by_id: Dict[str, str],
        teachers_by_id: Dict[int, str],
        request_handler: RequestHandler
    ) -> Dict[str, Any]:
        """Форматирует данные об уроке в нужный формат"""
        try:
            date_formatted = self._format_lesson_date(lesson.get("date", ""))
            
            subject_name = DataValidator.safe_get_nested(
                lesson, "subject", "name",
                default=UNKNOWN_SUBJECT
            )
            
            works, homeworks = await self._process_works(
                lesson.get("works", []),
                work_types_by_id,
                request_handler
            )
            
            teachers = self._process_teachers(
                lesson.get("teachers", []),
                teachers_by_id
            )
            
            return {
                "date": date_formatted,
                "subject": subject_name,
                "title": lesson.get("title", ""),
                "number": lesson.get("number", 0),
                "homeworks": homeworks,
                "works": works,
                "teachers": teachers
            }
        
        except Exception as e:
            logger.error(f"Error formatting lesson: {str(e)}")
            raise
    
    def _format_lesson_date(self, lesson_date_str: str) -> str:
        """Форматирует дату урока"""
        if not lesson_date_str:
            return ""
        
        try:
            lesson_date = datetime.strptime(lesson_date_str, DATE_FORMAT_LESSON)
            return lesson_date.strftime(DATE_FORMAT_OUTPUT_SHORT)
        except ValueError:
            return ""
    
    async def _process_works(
        self,
        works: List[Dict],
        work_types_by_id: Dict[str, str],
        request_handler: RequestHandler
    ) -> Tuple[List[Dict], List[Dict]]:
        """Обрабатывает работы и домашние задания"""
        works_list = []
        homeworks_list = []
        
        homework_ids = [
            work.get("id_str", work.get("id", ""))
            for work in works
            if work.get("type") == WORK_TYPE_HOMEWORK
        ]
        
        homework_details_map = await self._fetch_homework_details(
            request_handler,
            homework_ids
        )
        
        for work in works:
            work_type_id = str(work.get("workType", ""))
            work_type_name = work_types_by_id.get(work_type_id, UNKNOWN_WORK_TYPE)
            work_id_str = work.get("id_str", work.get("id", ""))
            
            if work.get("type") == WORK_TYPE_HOMEWORK:
                homework_data = self._format_homework(
                    work,
                    homework_details_map.get(work_id_str, {})
                )
                homeworks_list.append(homework_data)
            
            if work.get("type") != WORK_TYPE_HOMEWORK or work.get("displayInJournal"):
                works_list.append({
                    "work_id": work_id_str,
                    "workType": work_type_name
                })
        
        return works_list, homeworks_list
    
    async def _fetch_homework_details(
        self,
        request_handler: RequestHandler,
        homework_ids: List[str]
    ) -> Dict[str, Dict]:
        """Получает детали домашних заданий параллельно"""
        if not homework_ids:
            return {}
        
        requests = [
            ("users/me/school/homeworks", {"homeworkId": hw_id})
            for hw_id in homework_ids
        ]
        
        results = await request_handler.execute_parallel_requests_with_params(requests)
        
        homework_details_map = {}
        for hw_id, result in zip(homework_ids, results):
            if not isinstance(result, Exception):
                homework_details_map[hw_id] = result
        
        return homework_details_map
    
    def _format_homework(
        self,
        work: Dict,
        homework_details: Dict
    ) -> Dict[str, Any]:
        """Форматирует данные домашнего задания"""
        files = []
        for file_info in homework_details.get("files", []):
            files.append({
                "name": file_info.get("name", ""),
                "download_url": file_info.get("downloadUrl", ""),
                "type": file_info.get("type", "")
            })
        
        sent_date_formatted = self._format_sent_date(work.get("sentDate", ""))
        
        return {
            "text": work.get("text", ""),
            "files": files,
            "sent_date": sent_date_formatted,
        }
    
    def _format_sent_date(self, sent_date_str: str) -> str:
        """Форматирует дату отправки домашнего задания"""
        if not sent_date_str:
            return ""
        
        try:
            sent_date = datetime.fromisoformat(sent_date_str.replace("Z", "+00:00"))
            return sent_date.strftime(DATE_FORMAT_OUTPUT_LONG)
        except Exception:
            return ""
    
    def _process_teachers(
        self,
        teacher_ids: List[int],
        teachers_by_id: Dict[int, str]
    ) -> List[Dict[str, str]]:
        """Обрабатывает список учителей"""
        return [
            {"FullName": teachers_by_id.get(teacher_id, UNKNOWN_TEACHER)}
            for teacher_id in teacher_ids
        ]
