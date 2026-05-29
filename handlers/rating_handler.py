import asyncio
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler
from handlers.groups_handler import GroupsHandler

class RatingHandler:
    """Обработчик для формирования рейтинга по оценкам и пропускам"""
    
    MAX_DAYS_PER_ABSENCE_REQUEST = 30
    
    async def handle(
        self,
        token: str,
        start_date: str,
        end_date: Optional[str] = None,
        class_list_ids: Optional[str] = None,
        subject_ids: Optional[str] = None,
        include_absences: bool = False,
        parallel: bool = False,
        school: bool = False
    ) -> Dict[str, Any]:
        """Формирует рейтинг учеников параллельно по всем группам"""
        try:
            validation_result = self._validate_dates(start_date, end_date)
            if not validation_result["success"]:
                return validation_result
            
            start, end = validation_result["dates"]
            subject_ids_list = self._parse_subject_ids(subject_ids)
            
            client = DnevnikAPIClient(token=token)
            request_handler = RequestHandler(client)
            
            async with client:
                groups_to_process = await self._determine_groups(
                    request_handler,
                    class_list_ids,
                    parallel,
                    school,
                    token
                )
                
                if not groups_to_process:
                    return {"success": False, "error": "No groups found to process"}
                
                all_results = await self._process_groups(
                    request_handler,
                    groups_to_process,
                    start_date,
                    end_date or start_date,
                    subject_ids_list,
                    include_absences,
                    start,
                    end
                )
                
                if not all_results:
                    return {
                        "success": False, 
                        "error": "No students with grades found"
                    }
                
                sorted_results = self._sort_and_rank_students(all_results)
                
                logger.info(f"Rating generated for {len(sorted_results)} students across {len(groups_to_process)} groups")
                return {
                    "success": True,
                    "data": {
                        "rating": sorted_results,
                        "period": {
                            "start": start_date,
                            "end": end_date or start_date,
                            "days": (end - start).days + 1
                        },
                        "groups_count": len(groups_to_process),
                        "include_absences": include_absences,
                        "subjects": subject_ids_list if subject_ids_list else ["all"],
                        "mode": "school" if school else ("parallel" if parallel else "custom")
                    }
                }
        
        except Exception as e:
            logger.error(f"Error in RatingHandler: {str(e)}")
            return {"success": False, "error": str(e)}

    async def _process_groups(
        self,
        request_handler: RequestHandler,
        groups_to_process: List[Dict[str, str]],
        start_date: str,
        end_date: str,
        subject_ids_list: List[str],
        include_absences: bool,
        start: datetime,
        end: datetime
    ) -> List[Dict[str, Any]]:
        """Создает задачи для каждой группы и запускает их одновременно"""
        
        tasks = [
            self._process_single_group(
                request_handler,
                group_info,
                start_date,
                end_date,
                subject_ids_list,
                include_absences,
                start,
                end
            )
            for group_info in groups_to_process
        ]

        results = await asyncio.gather(*tasks)
        
        all_results = []
        for group_rating in results:
            all_results.extend(group_rating)
            
        return all_results

    async def _process_single_group(
        self,
        request_handler: RequestHandler,
        group_info: Dict[str, str],
        start_date: str,
        end_date: str,
        subject_ids_list: List[str],
        include_absences: bool,
        start: datetime,
        end: datetime
    ) -> List[Dict[str, Any]]:
        """Логика обработки одной конкретной группы"""
        group_id = group_info["id"]
        group_name = group_info["name"]
        
        students_data = await request_handler.client.get(f"edu-groups/{group_id}/persons")
        
        if not students_data:
            logger.warning(f"No students found in group {group_id}")
            return []
        
        all_marks = await self._fetch_group_marks(
            request_handler,
            group_id,
            start_date,
            end_date,
            subject_ids_list
        )
        
        student_marks = self._group_marks_by_student(all_marks)
        
        student_absences = {}
        if include_absences:
            student_absences = await self._get_student_absences(
                request_handler,
                students_data,
                start,
                end
            )
        
        return self._calculate_group_rating(
            students_data,
            student_marks,
            student_absences,
            group_name
        )


    async def _fetch_group_marks(
        self,
        request_handler: RequestHandler,
        group_id: str,
        start_date: str,
        end_date: str,
        subject_ids_list: List[str]
    ) -> List[Dict]:
        if subject_ids_list:
            endpoints = [
                f"edu-groups/{group_id}/subjects/{subject_id}/marks/{start_date}/{end_date}"
                for subject_id in subject_ids_list
            ]
        else:
            endpoints = [f"edu-groups/{group_id}/marks/{start_date}/{end_date}"]
        
        results = await request_handler.execute_parallel_requests(endpoints)
        all_marks = []
        for result in results:
            if isinstance(result, Exception):
                logger.warning(f"Error fetching marks for group {group_id}: {result}")
                continue
            if result:
                all_marks.extend(result if isinstance(result, list) else [result])
        return all_marks

    async def _get_student_absences(
        self,
        request_handler: RequestHandler,
        students_data: List[Dict],
        start: datetime,
        end: datetime
    ) -> Dict[str, int]:
        student_absences = {}
        if not students_data:
            return student_absences
        
        date_ranges = self._split_date_range(start, end)
        requests = []
        task_info = []
        
        for student in students_data:
            person_id = str(student.get("id_str", ""))
            for chunk_start, chunk_end in date_ranges:
                requests.append((
                    f"persons/{person_id}/lesson-log-entries",
                    {
                        "startDate": chunk_start.strftime("%Y-%m-%d"),
                        "endDate": chunk_end.strftime("%Y-%m-%d")
                    }
                ))
                task_info.append(person_id)
        
        results = await request_handler.execute_parallel_requests_with_params(requests)
        
        for person_id, result in zip(task_info, results):
            if isinstance(result, Exception) or not result:
                continue
            if person_id not in student_absences:
                student_absences[person_id] = 0
            for entry in result.get("logEntries", []):
                if entry.get("status", "") in ("Pass", "Ill"):
                    student_absences[person_id] += 1
        return student_absences

    def _validate_dates(self, start_date: str, end_date: Optional[str]) -> Dict[str, Any]:
        start_valid, start_obj, start_error = DataValidator.validate_date_format(start_date)
        if not start_valid:
            return {"success": False, "error": start_error}
        
        end_obj = start_obj
        if end_date:
            end_valid, end_obj, end_error = DataValidator.validate_date_format(end_date)
            if not end_valid:
                return {"success": False, "error": end_error}
        
        range_valid, range_error = DataValidator.validate_date_range(start_obj, end_obj)
        if not range_valid:
            return {"success": False, "error": range_error}
        
        return {"success": True, "dates": (start_obj, end_obj)}

    def _parse_subject_ids(self, subject_ids: Optional[str]) -> List[str]:
        if not subject_ids: return []
        return [sid.strip() for sid in subject_ids.split(",")]

    async def _determine_groups(self, request_handler, class_list_ids, parallel, school, token) -> List[Dict[str, str]]:
        if class_list_ids:
            return [{"id": gid.strip(), "name": gid.strip()} for gid in class_list_ids.split(",")]
        
        context_data = await request_handler.get_context()
        if school:
            groups_handler = GroupsHandler()
            groups_result = await groups_handler.handle(token=token, parallel=False)
            if not groups_result.get("success"): return []
            return [{"id": g.get("id"), "name": g.get("name")} for g in groups_result.get("data", {}).get("groups", [])]
        
        edu_validation = DataValidator.get_edu_groups(context_data)
        if not edu_validation[0]: return []
        current_group_id = edu_validation[1]

        if parallel:
            parallel_data = await request_handler.client.get(f"edu-groups/{current_group_id}/parallel")
            return [{"id": g.get("id_str"), "name": g.get("name")} for g in parallel_data if g.get("type") == "Group"]
        
        group_info = await request_handler.client.get(f"edu-groups/{current_group_id}")
        return [{"id": current_group_id, "name": group_info.get("name", "Неизвестная группа")}]

    def _group_marks_by_student(self, all_marks: List[Dict]) -> Dict[str, List[Dict]]:
        student_marks = {}
        for mark in all_marks:
            person_id = str(mark.get("person_str", ""))
            if person_id not in student_marks:
                student_marks[person_id] = []
            student_marks[person_id].append(mark)
        return student_marks

    def _calculate_group_rating(self, students_data, student_marks, student_absences, group_name) -> List[Dict[str, Any]]:
        group_rating = []
        for student in students_data:
            person_id = str(student.get("id_str", ""))
            marks = student_marks.get(person_id, [])
            mark_values = self._extract_valid_marks(marks)
            if not mark_values: continue
            
            avg_grade = sum(mark_values) / len(mark_values)
            group_rating.append({
                "name": student.get("shortName", "Неизвестно"),
                "personId": person_id,
                "avg_grade": round(avg_grade, 2),
                "marks_count": len(mark_values),
                "absences_count": student_absences.get(person_id, 0),
                "group": group_name
            })
        return group_rating

    def _extract_valid_marks(self, marks: List[Dict]) -> List[int]:
        mark_values = []
        for mark in marks:
            try:
                val = int(mark.get("value", "0"))
                mark_values.append(val)
            except: pass
        return mark_values

    def _split_date_range(self, start: datetime, end: datetime) -> List[tuple]:
        ranges = []
        curr = start
        while curr <= end:
            nxt = min(curr + timedelta(days=self.MAX_DAYS_PER_ABSENCE_REQUEST - 1), end)
            ranges.append((curr, nxt))
            curr = nxt + timedelta(days=1)
        return ranges

    def _sort_and_rank_students(self, all_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        sorted_results = sorted(
            all_results,
            key=lambda x: (-x["avg_grade"], -x["marks_count"], x["absences_count"])
        )
        for i, student in enumerate(sorted_results, 1):
            student["position"] = i
        return sorted_results