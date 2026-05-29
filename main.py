"""Основное"""
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.concurrency import iterate_in_threadpool
from config import settings, CORS_ORIGINS
from utils.logger import logger
from utils.access_store import append_request_log, ensure_storage, get_owner_id_by_token
from api.routers import (
    context, lessons, marks, all_marks, works,
    work_types, teachers, subjects, groups, relatives,
    reporting_periods, entries, schedules, rating,
    schedules_person, timetables
)

app = FastAPI(
    title="Dnevnik.ru API",
    description="API для работы с данными Dnevnik.ru",
    version="1.0.0"
)


def _safe_append_log(owner_id: str, payload: dict) -> None:
    try:
        append_request_log(owner_id, payload)
    except Exception as exc:
        logger.warning(f"Failed to write log for {owner_id}: {exc}")


@app.on_event("startup")
async def startup_event():
    ensure_storage()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    client_ip = request.headers.get("x-forwarded-for")
    if client_ip:
        client_ip = client_ip.split(",")[0].strip()
    else:
        client_ip = request.client.host if request.client else "unknown"

    started_at = time.perf_counter()
    token = request.headers.get("access-token") or request.headers.get("access_token")

    try:
        response = await call_next(request)
        body = b""
        async for chunk in response.body_iterator:
            body += chunk
        response.body_iterator = iterate_in_threadpool([body])

        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        owner_id = get_owner_id_by_token(token) if token else None
        _safe_append_log(
            owner_id or "unknown",
            {
                "ts": int(time.time()),
                "owner_id": owner_id,
                "ip": client_ip,
                "method": request.method,
                "path": str(request.url.path),
                "query": str(request.url.query) if request.url.query else "",
                "status_code": response.status_code,
                "elapsed_ms": elapsed_ms,
                "response": body.decode("utf-8", errors="replace"),
            },
        )
        return response
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        owner_id = get_owner_id_by_token(token) if token else None
        _safe_append_log(
            owner_id or "unknown",
            {
                "ts": int(time.time()),
                "owner_id": owner_id,
                "ip": client_ip,
                "method": request.method,
                "path": str(request.url.path),
                "query": str(request.url.query) if request.url.query else "",
                "status_code": 500,
                "elapsed_ms": elapsed_ms,
                "error": str(exc),
            },
        )
        raise

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(context.router)
app.include_router(lessons.router)
app.include_router(marks.router)
app.include_router(all_marks.router)
app.include_router(works.router)
app.include_router(work_types.router)
app.include_router(teachers.router)
app.include_router(subjects.router)
app.include_router(groups.router)
app.include_router(relatives.router)
app.include_router(reporting_periods.router)
app.include_router(entries.router)
app.include_router(schedules.router)
app.include_router(rating.router)
app.include_router(schedules_person.router)
app.include_router(timetables.router)


@app.get("/")
async def root():
    """Корневой endpoint с информацией об API"""
    return {
        "message": "Dnevnik.ru API",
        "version": "1.1.0",
        "docs": "/docs",
        "endpoints": [
            "/context - Контекст пользователя",
            "/lessons/{lesson_id} - Информация об уроке",
            "/marks - Оценки",
            "/all_marks - Все оценки с средним баллом",
            "/works/{work_id} - Информация о работе",
            "/work-types - Типы работ",
            "/teachers - Учителя",
            "/subjects - Предметы",
            "/groups - Группы",
            "/relatives - Родители",
            "/reporting-periods - Периоды отчетности",
            "/entries - Записи логов (посещаемость)",
            "/schedules - Расписание",
            "/get-rating - Рейтинг студентов",
            "/schedules-person/{person_id}/{group_id}/{start_date} - Расписание ученика с деталями",
            "/timetables/{group_id} - Расписание звонков группы"
        ]
    }


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting API server on {settings.api_host}:{settings.api_port}")
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.api_debug
    )
