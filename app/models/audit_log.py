from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class AuditLogEntry(TimestampMixin, Base):
    """След изменений: кто и что сделал с заявкой.
    payload должен содержать только продуктовые поля (без токенов/URL/etc,
    см. app.core.sanitize)."""

    __tablename__ = "audit_log_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    approval_request_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("approval_requests.id"), nullable=False, index=True
    )
    actor_user_id: Mapped[str] = mapped_column(String(64), nullable=False)
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # created|approved|rejected|cancelled
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
