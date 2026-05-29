# Dnevnik API
![Static Badge](https://img.shields.io/badge/DnevnikRu_proxiAPI-SiroXYZ)
![GitHub Repo stars](https://img.shields.io/github/stars/SiroXYZ/DnevnikRu_proxiAPI)



![FastAPI](https://img.shields.io/badge/FastAPI-0ea5e9?style=for-the-badge&logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-2e7d32?style=for-the-badge&logo=sqlite&logoColor=white)
![Async](https://img.shields.io/badge/Async-aiohttp-f97316?style=for-the-badge)

> Продолжение проекта **DnevnikFormatter** - Python-модуля для работы с API Дневник.ру, упрощающего доступ к данным о расписании, оценках и тестах.  
> Здесь эта идея стала ещё проще, стабильнее и удобнее для реальных интеграций: один API, обычный `Access-Token`, логирование и SQLite-хранилище.

## Быстрые ссылки

- [Связь](https://t.me/SiroX1)
- [Сайт для получения токена](https://androsovpavel.pythonanywhere.com/)
- [Репозиторий с документацией по автоматизации получения токена](https://github.com/SiroXYZ/token-auto-dnevnik.ru)

## Что делает проект

API помогает получать данные Dnevnik.ru через обычный `Access-Token` без лишней обвязки.

Он уже умеет:

- отдавать контекст пользователя
- получать оценки, расписание, предметы, учителей и связанные данные
- работать с периодами, записями и рейтингом
- хранить служебные данные в SQLite
- вести JSONL-логи по владельцу токена

## Что стало лучше

- меньше лишней обвязки и ручных шагов
- стабильнее работа с токенами и владельцем токена
- кэширование владельца токена в БД
- запросы и логи стали предсказуемее
- проще подключать в Telegram-боты, веб-приложения и внутренние сервисы

## Почему это удобно

- один API вместо набора скриптов
- простая интеграция в любые проекты
- асинхронная обработка запросов
- логирование по `owner_id`
- быстрое локальное поднятие
- понятная структура кода

## Как запустить

```bash
pip install -r requirements.txt
python main.py
```

Или напрямую:

```bash
uvicorn main:app --host 127.0.0.1 --port 8080
```

## Пример запроса

```bash
curl -H "access-token: YOUR_TOKEN" \
  "http://127.0.0.1:8080/marks?start_date=2026-05-29"
```

## Настройки

Все настройки лежат в [config.py](./config.py).

- `api_host`
- `api_port`
- `api_debug`
- `log_level`
- `dnevnik_base_url`
- `cors_origins`

## Документация API

- Swagger: `/docs`
- ReDoc: `/redoc`
- Главная: `/`

## Структура проекта

- `main.py` - приложение FastAPI
- `api/` - роуты
- `handlers/` - обработчики логики
- `utils/` - клиент, БД и служебные функции
- `config.py` - центральный конфиг
- `logs/` - логи запросов

## Контакт

Если нужна помощь по проекту или интеграции:

- Telegram: [@Sirop1](https://t.me/Sirop1)

## Лицензия

Смотри файл лицензии в репозитории.
