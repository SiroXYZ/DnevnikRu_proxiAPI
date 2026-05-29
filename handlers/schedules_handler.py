"""Обработчик для endpoint /schedules"""
from typing import Any, Dict, Optional, List
from datetime import datetime
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler


class SchedulesHandler:
    """Обработчик данных расписания"""
    
    async def handle(
        self, 
        token: str,
        start_date: str,
        end_date: Optional[str] = None,
        person_id: Optional[str] = None,
        group_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить расписание текущего пользователя за период
        
        Args:
            token: токен доступа
            start_date: начальная дата (YYYY-MM-DD)
            end_date: конечная дата (YYYY-MM-DD), опционально
            person_id: ID ученика, опционально (если не указан, берется из контекста)
            group_id: ID группы, опционально (если не указан, берется из контекста)
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
                
                edu_validation = DataValidator.get_edu_groups(context_data, group_id)
                if not edu_validation[0]:
                    return {
                        "success": False,
                        "error": edu_validation[2]
                    }
                
                group_id_to_use = edu_validation[1]
                
                endpoint = f"persons/{person_id_to_use}/groups/{group_id_to_use}/schedules"
                schedule_response = await request_handler.client.get(
                    endpoint,
                    params={
                        "startDate": start.strftime("%Y-%m-%dT00:00:00"),
                        "endDate": end.strftime("%Y-%m-%dT23:59:59")
                    }
                )
                
                formatted_schedule = await self._format_schedule(
                    schedule_response,
                    request_handler
                )
                
                logger.info(f"Schedule retrieved successfully for {start_date} to {end_date or start_date}")
                return {
                    "success": True,
                    "data": formatted_schedule
                }
        except Exception as e:
            logger.error(f"Error in SchedulesHandler: {str(e)}")
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
    
    async def _format_schedule(
        self,
        raw_data: Dict,
        request_handler: RequestHandler
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Форматирует сырое расписание в нужный формат"""
        formatted = {}
        
        all_homework_ids = self._extract_homework_ids(raw_data)
        homework_details_map = await self._fetch_homework_details(
            request_handler,
            all_homework_ids
        )
        
        for day in raw_data.get("days", []):
            day_date = day.get("date", "")
            if not day_date:
                continue
            
            date_str = self._format_day_date(day_date)
            if not date_str:
                continue
            
            day_data = self._build_day_dictionaries(day)
            lessons = self._process_lessons(
                day,
                day_data,
                homework_details_map
            )
            
            formatted[date_str] = lessons
        
        return formatted
    
    def _extract_homework_ids(self, raw_data: Dict) -> set:
        """Извлекает все ID домашних заданий"""
        all_homework_ids = set()
        for day in raw_data.get("days", []):
            for hw in day.get("homeworks", []):
                hw_id = str(hw.get("id", ""))
                if hw_id:
                    all_homework_ids.add(hw_id)
        return all_homework_ids
    
    async def _fetch_homework_details(
        self,
        request_handler: RequestHandler,
        homework_ids: set
    ) -> Dict[str, Dict]:
        """Загружает детали всех домашних заданий параллельно"""
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
    
    def _format_day_date(self, day_date: str) -> Optional[str]:
        """Форматирует дату дня"""
        if not day_date:
            return None
        
        try:
            date_obj = datetime.strptime(day_date, "%Y-%m-%dT%H:%M:%S")
            return date_obj.strftime("%d.%m.%Y")
        except ValueError:
            return day_date
    
    def _build_day_dictionaries(self, day: Dict) -> Dict[str, Any]:
        """Создает словари для быстрого поиска данных дня"""
        works_by_id = {str(w.get("id", "")): w for w in day.get("works", [])}
        homeworks_by_id = {str(h.get("id", "")): h for h in day.get("homeworks", [])}
        
        marks_by_work = {}
        mood_by_work = {}
        for mark in day.get("marks", []):
            work_id = str(mark.get("work", ""))
            marks_by_work[work_id] = mark.get("value", 0)
            mood_by_work[work_id] = mark.get("mood", {})
        
        teachers_by_id = {}
        for teacher_info in day.get("teachers", []):
            person = teacher_info.get("person", {})
            teachers_by_id[str(person.get("id"))] = person.get("shortName", "Неизвестно")
        
        work_types_by_id = {}
        for wt in day.get("workTypes", []):
            wt_id = str(wt.get("id", ""))
            work_types_by_id[wt_id] = wt.get("name", "Неизвестный тип")
        
        subjects_by_id = {
            str(s["id"]): s.get("name")
            for s in day.get("subjects", [])
        }
        
        attendance_by_lesson = self._build_attendance_map(day)
        
        return {
            "works_by_id": works_by_id,
            "homeworks_by_id": homeworks_by_id,
            "marks_by_work": marks_by_work,
            "mood_by_work": mood_by_work,
            "teachers_by_id": teachers_by_id,
            "work_types_by_id": work_types_by_id,
            "subjects_by_id": subjects_by_id,
            "attendance_by_lesson": attendance_by_lesson
        }
    
    def _build_attendance_map(self, day: Dict) -> Dict[str, str]:
        """Создает словарь статусов посещаемости"""
        attendance_by_lesson = {}
        for entry in day.get("lessonLogEntries", []):
            lesson_str = str(entry.get("lesson_str", ""))
            status = entry.get("status", "")
            
            if status == "Pass":
                attendance_by_lesson[lesson_str] = "Отсутствовал"
            elif status == "Ill":
                attendance_by_lesson[lesson_str] = "Болел"
            else:
                attendance_by_lesson[lesson_str] = "Присутствовал"
        
        return attendance_by_lesson
    
    def _process_lessons(
        self,
        day: Dict,
        day_data: Dict[str, Any],
        homework_details_map: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """Обрабатывает уроки дня"""
        lessons = []
        
        for lesson in day.get("lessons", []):
            lesson_data = self._format_lesson(
                lesson,
                day_data,
                homework_details_map
            )
            lessons.append(lesson_data)
        
        lessons.sort(key=lambda x: x["lesson_number"])
        return lessons
    
    def _format_lesson(
        self,
        lesson: Dict,
        day_data: Dict[str, Any],
        homework_details_map: Dict[str, Dict]
    ) -> Dict[str, Any]:
        """Форматирует один урок"""
        lesson_id = str(lesson.get("id", ""))
        lesson_str = str(lesson.get("id_str", lesson_id))
        
        time_str = lesson.get("hours", "")
        
        subject_id = str(lesson.get("subjectId", ""))
        subject = day_data["subjects_by_id"].get(subject_id, "Неизвестный предмет")
        
        teacher_ids = lesson.get("teachers", [])
        teachers = [
            day_data["teachers_by_id"].get(str(tid), "Неизвестно")
            for tid in teacher_ids
        ]
        teacher_str = ", ".join(teachers) if teachers else "Неизвестно"
        
        building = lesson.get("building", "")
        place = lesson.get("place", "")
        location = f"{building} {place}".strip() if building or place else "Не указано"
        
        attendance = day_data["attendance_by_lesson"].get(lesson_str, "Присутствовал")
        
        works_list, homeworks_list = self._process_lesson_works(
            lesson,
            day_data,
            homework_details_map
        )
        
        return {
            "lesson_id": lesson_id,
            "lesson_number": lesson.get("number", 0),
            "time": time_str,
            "subject": subject,
            "title": lesson.get("title", subject),
            "teacher": teacher_str,
            "place": location,
            "homeworks": homeworks_list,
            "works": works_list,
            "attendance": attendance,
            "is_important": lesson.get("isImportant", False),
        }
    
    def _process_lesson_works(
        self,
        lesson: Dict,
        day_data: Dict[str, Any],
        homework_details_map: Dict[str, Dict]
    ) -> tuple[List[Dict], List[Dict]]:
        """Обрабатывает работы и домашние задания урока"""
        works_list = []
        homeworks_list = []
        
        for work_id in lesson.get("works", []):
            work_id_str = str(work_id)
            
            if work_id_str in day_data["homeworks_by_id"]:
                homework = self._format_homework(
                    day_data["homeworks_by_id"][work_id_str],
                    day_data,
                    homework_details_map,
                    work_id_str
                )
                homeworks_list.append(homework)
            elif work_id_str in day_data["works_by_id"]:
                work = self._format_work(
                    day_data["works_by_id"][work_id_str],
                    day_data,
                    work_id_str
                )
                works_list.append(work)
        
        return works_list, homeworks_list
    
    def _format_homework(
        self,
        hw: Dict,
        day_data: Dict[str, Any],
        homework_details_map: Dict[str, Dict],
        work_id_str: str
    ) -> Dict[str, Any]:
        """Форматирует домашнее задание"""
        work_type_id = str(hw.get("workType", ""))
        work_type_name = day_data["work_types_by_id"].get(work_type_id, "Домашнее задание")
        
        mark_value = day_data["marks_by_work"].get(work_id_str, 0)
        mood = day_data["mood_by_work"].get(work_id_str, "")
        
        sent_date = hw.get("sentDate", "")
        sent_date_formatted = self._format_sent_date(sent_date)
        
        homework_details = homework_details_map.get(work_id_str, {})
        files = self._extract_homework_files(homework_details, hw)
        
        return {
            "text": hw.get("text", ""),
            "files": files,
            "sent_date": sent_date_formatted,
            "mark": mark_value,
            "mood": mood,
        }
    
    def _format_work(
        self,
        work: Dict,
        day_data: Dict[str, Any],
        work_id_str: str
    ) -> Dict[str, Any]:
        """Форматирует работу"""
        work_type_id = str(work.get("workType", ""))
        work_type_name = day_data["work_types_by_id"].get(work_type_id, "Неизвестная работа")
        
        mark_value = day_data["marks_by_work"].get(work_id_str, 0)
        mood = day_data["mood_by_work"].get(work_id_str, "")
        
        return {
            "work_id": work_id_str,
            "work": work_type_name,
            "mark": mark_value,
            "mood": mood
        }
    
    def _format_sent_date(self, sent_date: str) -> str:
        """Форматирует дату отправки"""
        if not sent_date:
            return ""
        
        try:
            hw_date = datetime.fromisoformat(sent_date.replace("Z", "+00:00"))
            return hw_date.strftime("%d.%m.%Y %H:%M")
        except Exception:
            return ""
    
    def _extract_homework_files(
        self,
        homework_details: Dict,
        hw: Dict
    ) -> List[Dict[str, str]]:
        """Извлекает файлы домашнего задания"""
        files = []
        
        for file_info in homework_details.get("files", []):
            files.append({
                "name": file_info.get("name", ""),
                "download_url": file_info.get("downloadUrl", ""),
            })
        
        if not files:
            file_ids = hw.get("files", [])
            files = [
                {
                    "name": f"file_{fid}",
                    "download_url": f"https://dnevnik.ru/files/{fid}",
                }
                for fid in file_ids
            ]
        
        return files
