"""Обработчик для endpoint /works/{work_id}"""
from typing import Any, Dict, Optional, List
from datetime import datetime
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler


class WorksHandler:
    """Обработчик данных о работе и оценках"""
    
    async def handle(
        self, 
        token: str, 
        work_id: str, 
        person_id: Optional[str] = None,
        school_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить информацию о работе и оценках по ней
        
        Args:
            token: токен доступа
            work_id: ID работы
            person_id: ID ученика (опционально, если указан - показывает его оценку)
            school_id: ID школы, опционально (если не указан, берется из контекста)
        """
        try:
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
                
                work_data = await request_handler.client.get(f"works/{work_id}")
                if not work_data:
                    return {
                        "success": False,
                        "error": f"Work {work_id} not found"
                    }
                
                person_marks = await request_handler.client.get(
                    f"persons/{person_id_to_use}/works/{work_id}/marks"
                )
                
                if not person_marks:
                    return {
                        "success": False,
                        "error": f"No marks found for person {person_id_to_use} in work {work_id}"
                    }
                
                person_mark = person_marks[0] if isinstance(person_marks, list) else person_marks
                
                lesson_id = str(work_data.get("lesson", ""))
                lesson_data = await request_handler.client.get(f"lessons/{lesson_id}")
                
                work_types_data = await request_handler.client.get(f"work-types/{school_id_to_use}")
                work_types_by_id = {
                    str(wt.get("id")): wt.get("title", "Неизвестно")
                    for wt in work_types_data
                }
                
                group_id = work_data.get("eduGroup_str", "")
                students_by_id = await self._fetch_students(
                    request_handler,
                    group_id
                )
                
                marks_histogram = await request_handler.client.get(
                    f"works/{work_id}/marks/histogram"
                )
                
                class_distribution = await self._build_class_distribution(
                    marks_histogram,
                    students_by_id,
                    request_handler,
                    group_id,
                    work_id
                )
                
                formatted = self._format_work_data(
                    work_data,
                    lesson_data,
                    person_mark,
                    work_types_by_id,
                    class_distribution
                )
                
                logger.info(f"Work {work_id} information retrieved successfully")
                return {
                    "success": True,
                    "data": [formatted]
                }
        
        except Exception as e:
            logger.error(f"Error in WorksHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _fetch_students(
        self,
        request_handler: RequestHandler,
        group_id: str
    ) -> Dict[str, str]:
        """Получает словарь учеников группы"""
        if not group_id:
            return {}
        
        try:
            students_data = await request_handler.client.get(f"edu-groups/{group_id}/persons")
            return {
                str(student.get("id_str", "")): student.get("shortName", "Неизвестно")
                for student in students_data
            }
        except Exception as e:
            logger.warning(f"Error fetching students for group {group_id}: {str(e)}")
            return {}
    
    async def _build_class_distribution(
        self,
        marks_histogram: Dict[str, Any],
        students_by_id: Dict[str, str],
        request_handler: RequestHandler,
        group_id: str,
        work_id: str
    ) -> Dict[str, Any]:
        """Строит распределение оценок по классу с параллельной загрузкой"""
        distribution = {}
        
        if not students_by_id:
            return distribution
        
        student_ids = list(students_by_id.keys())
        endpoints = [
            f"persons/{student_id}/works/{work_id}/marks"
            for student_id in student_ids
        ]
        
        results = await request_handler.execute_parallel_requests(endpoints)
        
        for student_id, marks_result in zip(student_ids, results):
            if isinstance(marks_result, Exception):
                logger.warning(
                    f"Error fetching mark for student {student_id} on work {work_id}: {marks_result}"
                )
                continue
            
            if marks_result:
                mark_entry = marks_result[0] if isinstance(marks_result, list) else marks_result
                mark_value = str(mark_entry.get("value", ""))
                student_name = students_by_id[student_id]
                
                if mark_value not in distribution:
                    distribution[mark_value] = {
                        "count": 0,
                        "student_marks": []
                    }
                
                distribution[mark_value]["count"] += 1
                distribution[mark_value]["student_marks"].append({
                    "name": student_name,
                    "mark": mark_value
                })
        
        return distribution
    
    def _format_work_data(
        self,
        work_data: Dict,
        lesson_data: Dict,
        person_mark: Dict,
        work_types_by_id: Dict[str, str],
        class_distribution: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Форматирует данные о работе"""
        lesson_id = str(work_data.get("lesson", ""))
        lesson_title = lesson_data.get("title", "Неизвестно")
        lesson_date_str = lesson_data.get("date", "")
        
        lesson_date_formatted = self._format_date(
            lesson_date_str,
            "%Y-%m-%dT%H:%M:%S",
            "%d.%m.%Y"
        )
        
        work_type_id = str(work_data.get("workType", ""))
        work_type_name = work_types_by_id.get(work_type_id, "Неизвестно")
        
        subject_info = lesson_data.get("subject", {})
        subject_name = subject_info.get("name", "Неизвестный предмет")
        
        mark_date_str = person_mark.get("date", "")
        mark_date_formatted = self._format_date(
            mark_date_str,
            "%Y-%m-%dT%H:%M:%S.%f",
            "%d.%m.%Y %H:%M"
        )
        
        return {
            "lesson_id": lesson_id,
            "subject": subject_name,
            "work_type": work_type_name,
            "lesson_title": lesson_title,
            "mark": str(person_mark.get("value", "")),
            "class_distribution": class_distribution,
            "mark_date": mark_date_formatted,
            "lesson_date": lesson_date_formatted
        }
    
    def _format_date(self, date_str: str, input_format: str, output_format: str) -> str:
        """Форматирует дату из одного формата в другой"""
        if not date_str:
            return ""
        
        try:
            date_obj = datetime.strptime(date_str, input_format)
            return date_obj.strftime(output_format)
        except (ValueError, TypeError):
            return ""
