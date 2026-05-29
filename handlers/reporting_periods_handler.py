"""Обработчик для endpoint /reporting-periods"""
from typing import Any, Dict, List, Optional
from datetime import datetime
from utils.client import DnevnikAPIClient
from utils.logger import logger
from handlers.validators import DataValidator
from handlers.request_handler import RequestHandler


class ReportingPeriodsHandler:
    """Обработчик данных периодов отчётности в группе"""
    
    async def handle(
        self, 
        token: str, 
        edu_group_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получить список периодов отчётности в группе
        
        Args:
            token: токен доступа
            edu_group_id: ID учебной группы. Если None, получает из контекста
        """
        try:
            client = DnevnikAPIClient(token=token)
            request_handler = RequestHandler(client)
            
            async with client:
                if not edu_group_id:
                    context_data = await request_handler.get_context()
                    edu_validation = DataValidator.get_edu_groups(context_data)
                    if not edu_validation[0]:
                        return {
                            "success": False,
                            "error": edu_validation[2]
                        }
                    edu_group_id = edu_validation[1]
                
                endpoint = f"edu-groups/{edu_group_id}/reporting-periods"
                periods_data = await request_handler.client.get(endpoint)
            
            periods = self._format_periods(periods_data)
            
            logger.info(f"Reporting periods data processed successfully for group {edu_group_id}")
            return {
                "success": True,
                "data": {
                    "reportingPeriods": periods
                }
            }
        except Exception as e:
            logger.error(f"Error in ReportingPeriodsHandler: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_periods(self, periods_data: List[Dict]) -> List[Dict[str, Any]]:
        """Форматирует данные периодов отчетности"""
        today = datetime.now().date()
        periods = []
        
        for period in periods_data:
            is_current = self._check_if_current_period(period, today)
            
            periods.append({
                "number": period.get("number"),
                "id": period.get("id_str"),
                "start": period.get("start", "")[:10],
                "finish": period.get("finish", "")[:10],
                "type": period.get("type"),
                "name": period.get("name"),
                "current": is_current
            })
        
        return periods
    
    def _check_if_current_period(self, period: Dict, today: datetime.date) -> bool:
        """Проверяет, является ли период текущим"""
        try:
            start_str = period.get("start", "")
            finish_str = period.get("finish", "")
            
            if start_str and finish_str:
                start_date = datetime.strptime(start_str[:10], "%Y-%m-%d").date()
                finish_date = datetime.strptime(finish_str[:10], "%Y-%m-%d").date()
                return start_date <= today <= finish_date
        except (ValueError, AttributeError):
            pass
        
        return False
