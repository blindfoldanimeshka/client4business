from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    """Liveness: процесс жив. Никаких внешних зависимостей не проверяем."""
    return {"status": "ok"}


@router.get("/ready")
def ready(db: Session = Depends(get_db)) -> dict:
    """Readiness: можем ли обслуживать трафик (проверяем связь с БД)."""
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
