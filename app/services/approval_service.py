from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import ApprovalRequestNotFound
from app.core.sanitize import sanitize_for_audit
from app.core.state_machine import assert_transition_allowed
from app.models.approval_request import ApprovalRequest, ApprovalStatus
from app.models.audit_log import AuditLogEntry
from app.models.outbox_event import OutboxEvent
from app.schemas.approval_request import ApprovalRequestCreate


def _audit_and_publish(db: Session, *, request: ApprovalRequest, actor_user_id: str, action: str) -> None:
    """Пишет audit log и outbox-событие в той же транзакции, что и изменение
    заявки. Именно это и даёт: (1) след "кто и что изменил", (2) готовность
    к интеграции через события без немедленного вызова внешних сервисов."""

    payload = sanitize_for_audit(
        {
            "id": request.id,
            "workspace_id": request.workspace_id,
            "status": request.status.value,
            "decided_by_user_id": request.decided_by_user_id,
            "decision_note": request.decision_note,
            "action": action,
        }
    )

    db.add(
        AuditLogEntry(
            workspace_id=request.workspace_id,
            approval_request_id=request.id,
            actor_user_id=actor_user_id,
            action=action,
            payload=payload,
        )
    )
    db.add(
        OutboxEvent(
            workspace_id=request.workspace_id,
            aggregate_id=request.id,
            event_type=f"approval_request.{action}",
            payload=payload,
        )
    )


def create_approval_request(
    db: Session, *, workspace_id: str, actor_user_id: str, data: ApprovalRequestCreate
) -> ApprovalRequest:
    request = ApprovalRequest(
        workspace_id=workspace_id,
        source_type=data.sourceType,
        source_id=data.sourceId,
        title=data.title,
        description=data.description,
        reviewer_user_ids=data.reviewerUserIds,
        status=ApprovalStatus.PENDING,
        created_by_user_id=actor_user_id,
    )
    db.add(request)
    db.flush()  # получить request.id перед записью audit/outbox

    _audit_and_publish(db, request=request, actor_user_id=actor_user_id, action="created")

    db.commit()
    db.refresh(request)
    return request


def list_approval_requests(
    db: Session, *, workspace_id: str, limit: int = 50, offset: int = 0
) -> tuple[list[ApprovalRequest], int]:
    base_query = select(ApprovalRequest).where(ApprovalRequest.workspace_id == workspace_id)

    items = list(
        db.scalars(
            base_query.order_by(ApprovalRequest.created_at.desc()).limit(limit).offset(offset)
        )
    )
    # NB: отдельный count-запрос менее эффективен, чем window function,
    # но для объёма этого сервиса и целей задания - достаточно и прозрачно.
    total = db.query(ApprovalRequest).filter_by(workspace_id=workspace_id).count()
    return items, total


def get_approval_request(db: Session, *, workspace_id: str, request_id: str) -> ApprovalRequest:
    request = (
        db.query(ApprovalRequest)
        .filter_by(id=request_id, workspace_id=workspace_id)
        .one_or_none()
    )
    if request is None:
        # Намеренно не различаем "не существует" и "существует в другом
        # workspace" - иначе это утечка информации через enumeration.
        raise ApprovalRequestNotFound()
    return request


def _decide(
    db: Session,
    *,
    workspace_id: str,
    request_id: str,
    actor_user_id: str,
    target_status: ApprovalStatus,
    action: str,
    note: str | None,
) -> ApprovalRequest:
    request = get_approval_request(db, workspace_id=workspace_id, request_id=request_id)

    assert_transition_allowed(request.status, target_status)

    request.status = target_status
    request.decided_by_user_id = actor_user_id
    request.decided_at = datetime.now(timezone.utc)
    request.decision_note = note

    _audit_and_publish(db, request=request, actor_user_id=actor_user_id, action=action)

    db.commit()
    db.refresh(request)
    return request


def approve(db: Session, *, workspace_id: str, request_id: str, actor_user_id: str, comment: str | None) -> ApprovalRequest:
    return _decide(
        db,
        workspace_id=workspace_id,
        request_id=request_id,
        actor_user_id=actor_user_id,
        target_status=ApprovalStatus.APPROVED,
        action="approved",
        note=comment,
    )


def reject(db: Session, *, workspace_id: str, request_id: str, actor_user_id: str, reason: str) -> ApprovalRequest:
    return _decide(
        db,
        workspace_id=workspace_id,
        request_id=request_id,
        actor_user_id=actor_user_id,
        target_status=ApprovalStatus.REJECTED,
        action="rejected",
        note=reason,
    )


def cancel(db: Session, *, workspace_id: str, request_id: str, actor_user_id: str, reason: str) -> ApprovalRequest:
    return _decide(
        db,
        workspace_id=workspace_id,
        request_id=request_id,
        actor_user_id=actor_user_id,
        target_status=ApprovalStatus.CANCELLED,
        action="cancelled",
        note=reason,
    )
