"""Обработчик для endpoint /all_marks"""
from typing import Any, Dict, Optional, List
from datetime import datetime
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler
from handlers.marks_handler import MarksHandler


class AllMarksHandler:
    """Обработчик данных всех оценок по периодам и предметам"""
    
    async def handle(
        self,
        token: str,
        person_id: Optional[str] = None,
        periods_id: Optional[str] = None,
        subjects_id: Optional[List[str]] = None,
        edu_group_id: Optional[str] = None,
        school_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить все оценки за период(ы), сгруппированные по предметам с расчетом среднего
        
        Args:
            token: токен доступа
            person_id: ID ученика, опционально (если не указан, берется из контекста)
            periods_id: ID периода отчетности, опционально (если не указан, берется текущий)
            subjects_id: список ID предметов для фильтра, опционально (если не указан, берутся все)
            edu_group_id: ID группы, опционально (если не указан, берется из контекста)
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
                
                school_validation = DataValidator.get_school_id(context_data, school_id)
                if not school_validation[0]:
                    return {
                        "success": False,
                        "error": school_validation[2]
                    }
                
                school_id_to_use = school_validation[1]
                
                period_data = await self._get_period_data(
                    request_handler,
                    periods_id,
                    context_data,
                    edu_group_id
                )
                
                if not period_data["success"]:
                    return period_data
                
                periods_id_to_use = period_data["period_id"]
                start_date = period_data["start_date"]
                end_date = period_data["end_date"]
            
            marks_handler = MarksHandler()
            marks_result = await marks_handler.handle(
                token=token,
                start_date=start_date,
                end_date=end_date,
                person_id=person_id_to_use,
                school_id=school_id_to_use
            )
            
            if not marks_result.get("success"):
                return marks_result
            
            formatted_data = marks_result.get("data", {})
            
            subject_names_to_filter = await self._build_subject_filter(
                request_handler,
                school_id_to_use,
                subjects_id
            )
            
            result = self._format_marks_result(
                formatted_data,
                subject_names_to_filter
            )
            
            logger.info(f"All marks retrieved successfully for period {periods_id_to_use}")
            return {
                "success": True,
                "data": result,
                "period": {
                    "id": periods_id_to_use,
                    "start": start_date,
                    "end": end_date
                }
            }
        
        except Exception as e:
            logger.error(f"Error in AllMarksHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_period_data(
        self,
        request_handler: RequestHandler,
        periods_id: Optional[str],
        context_data: Dict[str, Any],
        edu_group_id: Optional[str]
    ) -> Dict[str, Any]:
        """Получает данные периода отчетности"""
        edu_validation = DataValidator.get_edu_group_id(context_data, edu_group_id)
        if not edu_validation[0]:
            return {
                "success": False,
                "error": edu_validation[2]
            }
        
        edu_group_id_to_use = edu_validation[1]
        periods_endpoint = f"edu-groups/{edu_group_id_to_use}/reporting-periods"
        periods_data = await request_handler.client.get(periods_endpoint)
        
        if not periods_id:
            current_period = self._find_current_period(periods_data)
            if not current_period:
                return {
                    "success": False,
                    "error": "No reporting periods found"
                }
            periods_id_to_use = current_period.get("id_str")
            start_date = current_period.get("start", "")[:10]
            end_date = current_period.get("finish", "")[:10]
        else:
            period_found = self._find_period_by_id(periods_data, periods_id)
            if not period_found:
                return {
                    "success": False,
                    "error": f"Reporting period {periods_id} not found"
                }
            periods_id_to_use = periods_id
            start_date = period_found.get("start", "")[:10]
            end_date = period_found.get("finish", "")[:10]
        
        return {
            "success": True,
            "period_id": periods_id_to_use,
            "start_date": start_date,
            "end_date": end_date
        }
    
    def _find_current_period(self, periods_data: List[Dict]) -> Optional[Dict]:
        """Находит текущий период отчетности"""
        today = datetime.now().date()
        
        for period in periods_data:
            try:
                start_str = period.get("start", "")[:10]
                finish_str = period.get("finish", "")[:10]
                
                start = datetime.strptime(start_str, "%Y-%m-%d").date()
                finish = datetime.strptime(finish_str, "%Y-%m-%d").date()
                
                if start <= today <= finish:
                    return period
            except ValueError:
                continue
        
        if periods_data:
            return periods_data[0]
        
        return None
    
    def _find_period_by_id(self, periods_data: List[Dict], periods_id: str) -> Optional[Dict]:
        """Находит период по ID"""
        for period in periods_data:
            if period.get("id_str") == periods_id:
                return period
        return None
    
    async def _build_subject_filter(
        self,
        request_handler: RequestHandler,
        school_id: str,
        subjects_id: Optional[List[str]]
    ) -> Optional[set]:
        """Строит фильтр по предметам"""
        if not subjects_id:
            return None
        
        try:
            subjects_data = await request_handler.client.get(f"schools/{school_id}/subjects")
            subject_map = {
                str(s.get("id")): s.get("name", "")
                for s in subjects_data
            }
            
            subject_names_to_filter = set()
            for subj_id in subjects_id:
                if subj_id in subject_map:
                    subject_names_to_filter.add(subject_map[subj_id])
                else:
                    subject_names_to_filter.add(subj_id)
            
            return subject_names_to_filter
        except Exception:
            return set(subjects_id)
    
    def _format_marks_result(
        self,
        formatted_data: Dict[str, List[Dict]],
        subject_names_to_filter: Optional[set]
    ) -> List[Dict[str, Any]]:
        """Форматирует результат оценок"""
        result = []
        
        for subject_name, marks_list in formatted_data.items():
            if subject_names_to_filter is not None:
                if subject_name not in subject_names_to_filter:
                    continue
            
            marks_formatted = []
            mark_values = []
            
            for mark in marks_list:
                marks_formatted.append({
                    "work_id": mark.get("work_id", ""),
                    "mark": mark.get("value", ""),
                    "mood": mark.get("mood", "")
                })
                
                try:
                    mark_val = int(mark.get("value", "0"))
                    mark_values.append(mark_val)
                except (ValueError, TypeError):
                    pass
            
            avg_mark = "0"
            if mark_values:
                avg = sum(mark_values) / len(mark_values)
                avg_mark = f"{avg:.2f}".rstrip('0').rstrip('.')
            
            result.append({
                "subject": subject_name,
                "marks": marks_formatted,
                "avg": avg_mark
            })
        
        return result
