"""Router для endpoint /timetables"""
from fastapi import APIRouter, Header, Path
from typing import Dict, Any
from handlers.timetables_handler import TimetablesHandler

router = APIRouter(prefix="/timetables", tags=["Timetables"])


@router.get("/{group_id}", summary="Получить расписание звонков группы")
async def get_timetables(
    group_id: str = Path(..., description="ID группы"),
    access_token: str = Header(..., description="Токен доступа")
) -> Dict[str, Any]:
    """
    Получить расписание звонков (время начала и конца уроков) группы
    
    Возвращает полное расписание с информацией о каждом уроке:
    - Номер урока
    - Время начала и конца
    - Дни недели когда проводится
    - Название и тип урока
    
    **Параметры:**
    - `group_id` - ID группы (в пути)
    - `access_token` - токен доступа (в заголовке)
    
    **Пример запроса:**
    ```
    GET /timetables/2392148420039838219
    Header: access-token: ВАШ_ТОКЕН
    ```
    
    **Ответ:**
    ```json
    {
      "success": true,
      "data": {
        "name": "Основное расписание",
        "first_lesson_number": 1,
        "lessons": [
          {
            "lesson_number": 1,
            "name": "1 урок",
            "type": "Lesson",
            "start_time": "08:30",
            "finish_time": "09:15",
            "time": "08:30 - 09:15",
            "days_of_week": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
          },
          {
            "lesson_number": 2,
            "name": "2 урок",
            "type": "Lesson",
            "start_time": "09:25",
            "finish_time": "10:10",
            "time": "09:25 - 10:10",
            "days_of_week": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
          },
          {
            "lesson_number": 3,
            "name": "3 урок",
            "type": "Lesson",
            "start_time": "10:20",
            "finish_time": "11:05",
            "time": "10:20 - 11:05",
            "days_of_week": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
          }
        ]
      }
    }
    ```
    """
    handler = TimetablesHandler()
    result = await handler.handle(token=access_token, group_id=group_id)
    return result
