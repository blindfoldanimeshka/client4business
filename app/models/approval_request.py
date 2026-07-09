import enum
from datetime import datetime

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.database import Base
from app.models.base import TimestampMixin, new_uuid


class SourceType(str, enum.Enum):
    PUBLICATION = "publication"
    SCENARIO = "scenario"
    EDIT = "edit"
    EXTERNAL = "external"


class ApprovalStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


FINAL_STATUSES = {ApprovalStatus.APPROVED, ApprovalStatus.REJECTED, ApprovalStatus.CANCELLED}


class ApprovalRequest(TimestampMixin, Base):
    __tablename__ = "approval_requests"
    __table_args__ = (
        Index("ix_approval_requests_workspace_status", "workspace_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)

    # Внешние сущности - только идентификаторы, соседние сервисы не реализуем.
    workspace_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_type: Mapped[SourceType] = mapped_column(Enum(SourceType), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Список внешних user id ревьюеров. Храним как JSON-массив строк.
    reviewer_user_ids: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus), nullable=False, default=ApprovalStatus.PENDING
    )

    created_by_user_id: Mapped[str] = mapped_column(String(64), nullable=False)

    decided_by_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decided_at: Mapped[datetime | None] = mapped_column(nullable=True)
    # Комментарий (approve) или причина (reject/cancel) - это данные продукта,
    # не секреты, поэтому храним как есть, но не логируем во внешние логи целиком.
    decision_note: Mapped[str | None] = mapped_column(Text, nullable=True)
