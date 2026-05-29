"""Обработчик запросов к API"""
from typing import Any, Dict, List, Optional, Tuple
import asyncio
from utils.client import DnevnikAPIClient
from utils.logger import logger


class RequestHandler:
    """Класс для работы с запросами к API и управления очередями"""
    
    def __init__(self, client: DnevnikAPIClient):
        self.client = client
        self._context_cache: Optional[Dict[str, Any]] = None
        self._context_request_lock = asyncio.Lock() 

    async def get_context(self, use_cache: bool = True) -> Dict[str, Any]:
        """Получает контекст пользователя с кешированием"""
        if use_cache and self._context_cache is not None:
            return self._context_cache
        

        async with self._context_request_lock:
            if self._context_cache is not None: 
                return self._context_cache
                
            context_data = await self.client.get("users/me/context")
            if use_cache:
                self._context_cache = context_data
            return context_data
    
    async def execute_parallel_requests(
        self, 
        endpoints: List[str],
        return_exceptions: bool = True
    ) -> List[Any]:
        """Выполняет параллельные GET запросы"""
        if not endpoints:
            return []
        
        logger.info(f"Batch execution: Sending {len(endpoints)} requests to API...")
        
        tasks = [self.client.get(endpoint) for endpoint in endpoints]
        
        results = await asyncio.gather(*tasks, return_exceptions=return_exceptions)
        return results
    
    async def execute_parallel_requests_with_params(
        self,
        requests: List[Tuple[str, Optional[Dict[str, Any]]]],
        return_exceptions: bool = True
    ) -> List[Any]:
        """Выполняет параллельные GET запросы с параметрами"""
        if not requests:
            return []
        
        logger.info(f"Batch execution: Sending {len(requests)} requests with params...")
        
        tasks = [
            self.client.get(endpoint, params=params) 
            for endpoint, params in requests
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=return_exceptions)
        return results
    
    def create_batch_endpoints(
        self,
        base_endpoint_template: str,
        ids: List[str],
        additional_params: Optional[Dict[str, str]] = None
    ) -> List[str]:
        """Создает список endpoint'ов для батч-запросов"""
        endpoints = []
        for item_id in ids:
            endpoint = base_endpoint_template.format(id=item_id)
            if additional_params:
                from urllib.parse import urlencode
                query = urlencode(additional_params)
                endpoint = f"{endpoint}?{query}"
            endpoints.append(endpoint)
        return endpoints

    def filter_successful_results(
        self,
        results: List[Any],
        source_data: Optional[List[Any]] = None
    ) -> List[Any]:
        """Фильтрует успешные результаты, логируя ошибки"""
        successful = []
        for idx, result in enumerate(results):
            if isinstance(result, Exception):
                source_info = f"item {idx}" if not source_data else f"{source_data[idx]}"
                logger.warning(f"Request failed for {source_info}: {str(result)}")
                continue
            if result is not None:
                successful.append(result)
        return successful