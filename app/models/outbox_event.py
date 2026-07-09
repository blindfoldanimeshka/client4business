from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class OutboxEvent(TimestampMixin, Base):
    """Transactional Outbox: событие пишется в той же транзакции БД, что и
    изменение состояния заявки. Отдельный publisher (worker), который читает
    неопубликованные записи и шлёт их в брокер (Kafka/SQS/etc), находится вне
    рамок этого задания, но модель к нему готова."""

    __tablename__ = "outbox_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    aggregate_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    # payload - только идентификаторы и продуктовые поля, без секретов/PII.
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    published_at: Mapped[datetime | None] = mapped_column(nullable=True)
