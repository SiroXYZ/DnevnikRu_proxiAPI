"""Валидаторы данных для handlers"""
from typing import Any, Dict, Optional, List, Tuple
from datetime import datetime
from utils.logger import logger


class DataValidator:
    """Класс для валидации данных из контекста и параметров"""
    
    DATE_FORMAT = "%Y-%m-%d"
    DEFAULT_UNKNOWN_VALUE = "Неизвестно"
    
    @staticmethod
    def validate_date_format(date_str: str) -> Tuple[bool, Optional[datetime], Optional[str]]:
        """Валидирует формат даты YYYY-MM-DD"""
        if not date_str:
            return False, None, "Date string is empty"
        
        try:
            date_obj = datetime.strptime(date_str, DataValidator.DATE_FORMAT)
            return True, date_obj, None
        except ValueError as e:
            return False, None, f"Invalid date format. Use YYYY-MM-DD: {str(e)}"
    
    @staticmethod
    def validate_date_range(start: datetime, end: datetime) -> Tuple[bool, Optional[str]]:
        """Проверяет, что start_date <= end_date"""
        if start > end:
            return False, "start_date must be <= end_date"
        return True, None
    
    @staticmethod
    def get_person_id(
        context_data: Optional[Dict[str, Any]] = None,
        person_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Получает person_id из параметра или контекста"""
        if person_id:
            return True, person_id, None
        
        if not context_data:
            return False, None, "No person ID provided and no context data available"
        
        person_id_from_context = context_data.get("personId")
        if not person_id_from_context:
            return False, None, "No person ID found in context"
        
        return True, person_id_from_context, None
    
    @staticmethod
    def get_school_id(
        context_data: Optional[Dict[str, Any]] = None,
        school_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Получает school_id из параметра или контекста"""
        if school_id:
            return True, school_id, None
        
        if not context_data:
            return False, None, "No school ID provided and no context data available"
        
        school_ids_from_context = context_data.get("schoolIds", [])
        if not school_ids_from_context:
            return False, None, "No schools found in context"
        
        return True, school_ids_from_context[0], None
    
    @staticmethod
    def get_school_ids(
        context_data: Optional[Dict[str, Any]] = None,
        school_ids: Optional[List[str]] = None
    ) -> Tuple[bool, Optional[List[str]], Optional[str]]:
        """Получает school_ids из параметра или контекста"""
        if school_ids:
            return True, school_ids, None
        
        if not context_data:
            return False, None, "No school IDs provided and no context data available"
        
        school_ids_from_context = context_data.get("schoolIds", [])
        if not school_ids_from_context:
            return False, None, "No schools found in context"
        
        return True, school_ids_from_context, None
    
    @staticmethod
    def get_edu_group_id(
        context_data: Optional[Dict[str, Any]] = None,
        edu_group_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Получает edu_group_id из параметра или контекста"""
        if edu_group_id:
            return True, edu_group_id, None
        
        if not context_data:
            return False, None, "No edu group ID provided and no context data available"
        
        edu_groups = context_data.get("eduGroups", [])
        if not edu_groups:
            return False, None, "No edu groups found in context"
        
        edu_group_id_from_context = edu_groups[0].get("id_str")
        if not edu_group_id_from_context:
            return False, None, "No valid edu group ID found in context"
        
        return True, edu_group_id_from_context, None
    
    @staticmethod
    def get_edu_groups(
        context_data: Optional[Dict[str, Any]] = None,
        edu_group_id: Optional[str] = None
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Получает edu_group_id из параметра или контекста (алиас для совместимости)"""
        return DataValidator.get_edu_group_id(context_data, edu_group_id)
    
    @staticmethod
    def validate_required_field(data: Dict[str, Any], field_name: str) -> Tuple[bool, Optional[str]]:
        """Проверяет наличие обязательного поля в данных"""
        if field_name not in data or not data[field_name]:
            return False, f"Missing required field: {field_name}"
        return True, None
    
    @staticmethod
    def safe_get_nested(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
        """Безопасно получает вложенное значение из словаря"""
        result = data
        for key in keys:
            if not isinstance(result, dict):
                return default
            result = result.get(key, default)
            if result is default:
                return default
        return result
