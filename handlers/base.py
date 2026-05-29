"""Базовый класс для обработчиков"""
from typing import Any, Dict
from utils.logger import logger


class BaseHandler:
    """Базовый класс для всех обработчиков данных"""
    
    async def handle(self, **kwargs) -> Dict[str, Any]:
        """Главный метод обработки"""
        pass
