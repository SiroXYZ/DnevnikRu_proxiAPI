"""Маршруты для работы с рейтингом студентов"""
from fastapi import APIRouter, Header, Query, HTTPException
from typing import Optional
from handlers.rating_handler import RatingHandler

router = APIRouter(prefix="/get-rating", tags=["Rating"])


@router.get("")
async def get_rating(
    access_token: str = Header(..., description="Токен доступа"),
    start_date: str = Query(..., description="Начальная дата (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Конечная дата (YYYY-MM-DD), опционально"),
    class_list_ids: Optional[str] = Query(None, description="ID группы или список ID групп (1,2,3)"),
    subject_ids: Optional[str] = Query(None, description="ID предмета или список ID предметов (1,2,3)"),
    include_absences: bool = Query(False, description="Включить учет пропусков"),
    parallel: bool = Query(False, description="Получить рейтинг параллели"),
    school: bool = Query(False, description="Получить рейтинг всей школы")
):
    """
    Получить рейтинг учеников по оценкам и пропускам
    
    ## Параметры:
    - **start_date**: Начальная дата (формат YYYY-MM-DD) - ОБЯЗАТЕЛЬНО
    - **end_date**: Конечная дата (формат YYYY-MM-DD) - опционально, если не указана = start_date
    - **class_list_ids**: ID одной группы или список ID групп через запятую (123,456,789)
    - **subject_ids**: ID одного предмета или список ID предметов (1,2,3) - если не указано, берутся все предметы
    - **include_absences**: Учитывать пропуски в рейтинге (true/false)
    - **parallel**: Получить рейтинг параллели текущего пользователя
    - **school**: Получить рейтинг всей школы
    
    ## Приоритет источников групп:
    1. Если указан **class_list_ids** - используются эти группы (group_name = ID)
    2. Если включен флаг **school** - загружаются все группы школы
    3. Если включен флаг **parallel** - загружается параллель текущего пользователя
    4. Если ничего не указано - используется группа из контекста текущего пользователя
    
    ## Примеры:
    
    ### Рейтинг одной группы:
    ```
    GET /get-rating?start_date=2026-01-01&end_date=2026-01-31&class_list_ids=123&include_absences=true
    ```
    
    ### Рейтинг нескольких групп:
    ```
    GET /get-rating?start_date=2026-01-01&class_list_ids=123,456,789&subject_ids=1,2&include_absences=true
    ```
    
    ### Рейтинг параллели:
    ```
    GET /get-rating?start_date=2026-01-01&parallel=true&include_absences=true
    ```
    
    ### Рейтинг школы:
    ```
    GET /get-rating?start_date=2026-01-01&school=true&include_absences=false
    ```
    
    ## Ответ (успешный):
    ```json
    {
      "success": true,
      "data": {
        "rating": [
          {
            "position": 1,
            "name": "Иван Сидоров",
            "personId": "123456",
            "avg_grade": 4.8,
            "marks_count": 15,
            "absences_count": 1,
            "group": "10А"
          },
          {
            "position": 2,
            "name": "Мария Петрова",
            "personId": "123457",
            "avg_grade": 4.75,
            "marks_count": 12,
            "absences_count": 2,
            "group": "10А"
          }
        ],
        "period": {
          "start": "2026-01-01",
          "end": "2026-01-31",
          "days": 31
        },
        "groups_count": 1,
        "include_absences": true,
        "subjects": ["1", "2"] или ["all"],
        "mode": "custom"
      }
    }
    ```
    
    ## Сортировка рейтинга:
    1. По средней оценке (↓ убывание)
    2. По количеству оценок (↓ убывание)
    3. По количеству пропусков (↑ возрастание)
    """
    handler = RatingHandler()
    result = await handler.handle(
        token=access_token,
        start_date=start_date,
        end_date=end_date,
        class_list_ids=class_list_ids,
        subject_ids=subject_ids,
        include_absences=include_absences,
        parallel=parallel,
        school=school
    )
    
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error", "Unknown error"))
    
    return result

