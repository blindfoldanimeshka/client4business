import logging

from fastapi import FastAPI

from app.api.v1 import approval_requests, health
from app.config import get_settings

settings = get_settings()

logging.basicConfig(level=settings.LOG_LEVEL)
logger = logging.getLogger("approval_service")

app = FastAPI(title="approval-service", version="0.1.0")

app.include_router(health.router)
app.include_router(approval_requests.router)


@app.middleware("http")
async def log_requests(request, call_next):
    # Логируем только маршрут/метод/статус - без тела запроса/ответа, чтобы
    # не попадали персональные данные или содержимое решений в общий лог.
    response = await call_next(request)
    logger.info("%s %s -> %s", request.method, request.url.path, response.status_code)
    return response
