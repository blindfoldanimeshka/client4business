# approval-service

Сервис согласования контента: принимает заявки на согласование перед публикацией
и фиксирует итоговое решение (approve / reject / cancel).

Внешние сущности (публикации, сценарии, пользователи, workspace) не реализуются —
сервис работает только с их идентификаторами.

## Стек

- Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic
- PostgreSQL (docker-compose) / SQLite (тесты и локальный запуск без Docker)
- pytest + httpx (TestClient)

## Запуск через Docker (рекомендуется)

```bash
docker compose up --build
```

Поднимет Postgres и сам сервис на `http://localhost:8000`. Миграции применяются
автоматически при старте контейнера (`alembic upgrade head` перед `uvicorn`).

Проверка:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## Локальный запуск без Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Для SQLite:
export DATABASE_URL="sqlite:///./local.db"
alembic upgrade head
uvicorn app.main:app --reload
```

## Тесты

```bash
pip install -r requirements.txt
pytest -q
```

Тесты используют SQLite in-memory и не требуют поднятого Postgres/Docker.

## Auth (заглушка)

Полноценной аутентификации нет — для локального запуска и тестового задания
используются HTTP-заголовки, которые в реальной системе пришли бы из
проверенного токена:

| Заголовок       | Назначение                                                        |
|-----------------|--------------------------------------------------------------------|
| `X-Workspace-Id`| workspace, от имени которого выполняется запрос                    |
| `X-User-Id`     | идентификатор пользователя (пишется в audit log как actor)         |
| `X-Actions`     | список разрешённых действий через запятую                          |

Доступные действия: `approval:read`, `approval:create`, `approval:decide`, `approval:cancel`.

Пример:

```bash
curl -X POST http://localhost:8000/api/v1/workspaces/ws_1/approval-requests \
  -H "X-Workspace-Id: ws_1" \
  -H "X-User-Id: usr_owner" \
  -H "X-Actions: approval:read,approval:create,approval:decide,approval:cancel" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: 3f3e5f0a-...-uuid" \
  -d '{
    "sourceType": "publication",
    "sourceId": "pub_123",
    "title": "Instagram reel draft",
    "description": "Needs final approval",
    "reviewerUserIds": ["usr_1", "usr_2"]
  }'
```

`workspace_id` в URL всегда сверяется с `X-Workspace-Id` — при несовпадении
запрос возвращает `404` (см. DESIGN.md, раздел про изоляцию workspace).

## Идемпотентность

Мутирующие эндпоинты (`create`, `approve`, `reject`, `cancel`) поддерживают
опциональный заголовок `Idempotency-Key`. Повтор запроса с тем же ключом (в
рамках одного workspace и одного эндпоинта) с тем же телом вернёт исходный
сохранённый ответ, не выполняя операцию повторно. Тот же ключ с другим телом —
`409 Conflict`.

## API

```
GET    /health
GET    /ready
POST   /api/v1/workspaces/{workspace_id}/approval-requests
GET    /api/v1/workspaces/{workspace_id}/approval-requests
GET    /api/v1/workspaces/{workspace_id}/approval-requests/{request_id}
POST   /api/v1/workspaces/{workspace_id}/approval-requests/{request_id}/approve
POST   /api/v1/workspaces/{workspace_id}/approval-requests/{request_id}/reject
POST   /api/v1/workspaces/{workspace_id}/approval-requests/{request_id}/cancel
```

Подробнее о модели данных, границах сервиса и компромиссах — в [DESIGN.md](./DESIGN.md).

## Структура проекта

```
app/
  api/v1/          # HTTP-роутеры (health, approval-requests)
  core/            # auth-заглушка, state machine, идемпотентность, санитайзер
  models/          # SQLAlchemy-модели
  schemas/         # Pydantic-схемы запросов/ответов
  services/        # бизнес-логика (транзакции, audit, outbox)
  config.py
  database.py
  main.py
alembic/           # миграции
tests/             # pytest
```
