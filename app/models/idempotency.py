from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class IdempotencyRecord(TimestampMixin, Base):
    """Хранит результат первого выполнения запроса с данным Idempotency-Key,
    чтобы при повторе (тот же ключ + тот же endpoint + тот же workspace)
    вернуть сохранённый ответ, а не создавать дубликат / не переводить
    заявку повторно в финальное состояние."""

    __tablename__ = "idempotency_records"
    __table_args__ = (
        Index(
            "uq_idempotency_workspace_key_endpoint",
            "workspace_id",
            "idempotency_key",
            "endpoint",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    endpoint: Mapped[str] = mapped_column(String(64), nullable=False)

    # Fingerprint тела запроса - чтобы отличить "тот же запрос повторили" от
    # "тот же ключ использовали для другого тела" (последнее - ошибка клиента, 409/422).
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)

    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict] = mapped_column(JSON, nullable=False)
