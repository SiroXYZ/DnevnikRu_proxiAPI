"""Обработчик для endpoint /group-students"""
from typing import Any, Dict, List, Optional
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler


class GroupStudentsHandler:
    """Обработчик данных учеников групп"""
    
    async def handle(
        self, 
        token: str, 
        group_ids: Optional[str] = None,
        parallel: bool = False,
        school: bool = False,
        school_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить список учеников групп
        
        Args:
            token: токен доступа
            group_ids: ID группы (опционально)
            parallel: если True, возвращает всех учеников параллели
            school: если True, возвращает всех учеников школы (игнорирует остальные флаги)
            school_id: ID школы, опционально (если не указан, берется из контекста)
        """
        try:
            client = DnevnikAPIClient(token=token)
            request_handler = RequestHandler(client)
            
            async with client:
                context_data = await request_handler.get_context()
                
                if school:
                    result = await self._get_school_students(
                        request_handler,
                        context_data,
                        school_id
                    )
                elif parallel:
                    result = await self._get_parallel_students(
                        request_handler,
                        context_data,
                        group_ids
                    )
                else:
                    result = await self._get_group_students(
                        request_handler,
                        context_data,
                        group_ids
                    )
            
            logger.info("Group students data processed successfully")
            return {
                "success": True,
                "data": result
            }
        except Exception as e:
            logger.error(f"Error in GroupStudentsHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _get_school_students(
        self,
        request_handler: RequestHandler,
        context_data: Dict[str, Any],
        school_id: Optional[str]
    ) -> Dict[str, Dict]:
        """Получает всех учеников школы"""
        school_validation = DataValidator.get_school_id(context_data, school_id)
        if not school_validation[0]:
            return {}
        
        school_id_to_use = school_validation[1]
        teachers_endpoint = f"schools/{school_id_to_use}/teachers"
        teachers_data = await request_handler.client.get(teachers_endpoint)
        
        if not teachers_data:
            logger.warning("No teachers found in school")
            return {}
        
        endpoints = [
            f"persons/{teacher.get('Id')}/edu-groups"
            for teacher in teachers_data
        ]
        
        results = await request_handler.execute_parallel_requests(endpoints)
        
        all_groups = {}
        all_group_ids = set()
        
        for teacher, result in zip(teachers_data, results):
            if isinstance(result, Exception) or result is None:
                continue
            
            for group in result:
                if group.get("type") == "Group":
                    group_id = group.get("id_str")
                    if group_id not in all_groups:
                        all_groups[group_id] = {
                            "id": group_id,
                            "name": group.get("name"),
                            "students": []
                        }
                        all_group_ids.add(group_id)
        
        if all_group_ids:
            student_endpoints = [
                f"edu-groups/{group_id}/persons"
                for group_id in all_group_ids
            ]
            
            student_results = await request_handler.execute_parallel_requests(student_endpoints)
            
            for group_id, result in zip(all_group_ids, student_results):
                if isinstance(result, Exception) or result is None:
                    continue
                
                for student in result:
                    all_groups[group_id]["students"].append({
                        "id": student.get("id_str"),
                        "userId": student.get("userId_str"),
                        "shortName": student.get("shortName")
                    })
        
        return all_groups
    
    async def _get_parallel_students(
        self,
        request_handler: RequestHandler,
        context_data: Dict[str, Any],
        group_ids: Optional[str]
    ) -> Dict[str, Dict]:
        """Получает всех учеников параллели"""
        if group_ids:
            endpoint = f"edu-groups/{group_ids}/parallel"
        else:
            edu_validation = DataValidator.get_edu_group_id(context_data)
            if not edu_validation[0]:
                return {}
            
            user_edu_group_id = edu_validation[1]
            endpoint = f"edu-groups/{user_edu_group_id}/parallel"
        
        parallel_data = await request_handler.client.get(endpoint)
        
        if parallel_data is None:
            logger.warning("No parallel data returned")
            return {}
        
        parallel_groups = [
            group for group in parallel_data
            if group.get("type") == "Group"
        ]
        
        if not parallel_groups:
            return {}
        
        endpoints = [
            f"edu-groups/{group.get('id_str')}/persons"
            for group in parallel_groups
        ]
        
        results = await request_handler.execute_parallel_requests(endpoints)
        
        result = {}
        for group, students_data in zip(parallel_groups, results):
            group_id = group.get("id_str")
            group_name = group.get("name")
            
            if isinstance(students_data, Exception) or students_data is None:
                result[group_id] = {"id": group_id, "name": group_name, "students": []}
            else:
                result[group_id] = {
                    "id": group_id,
                    "name": group_name,
                    "students": [
                        {
                            "id": student.get("id_str"),
                            "userId": student.get("userId_str"),
                            "shortName": student.get("shortName")
                        }
                        for student in students_data
                    ]
                }
        
        return result
    
    async def _get_group_students(
        self,
        request_handler: RequestHandler,
        context_data: Dict[str, Any],
        group_ids: Optional[str]
    ) -> Dict[str, Dict]:
        """Получает учеников конкретной группы"""
        if not group_ids:
            edu_validation = DataValidator.get_edu_group_id(context_data)
            if not edu_validation[0]:
                return {}
            group_ids = edu_validation[1]
        
        students_endpoint = f"edu-groups/{group_ids}/persons"
        students_data = await request_handler.client.get(students_endpoint)
        
        result = {group_ids: {"students": []}}
        
        if students_data is not None:
            for student in students_data:
                result[group_ids]["students"].append({
                    "id": student.get("id_str"),
                    "userId": student.get("userId_str"),
                    "shortName": student.get("shortName")
                })
        
        return result
