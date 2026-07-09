from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.config import get_settings
from app.core.auth import Action, AuthContext, require_action
from app.core.exceptions import ApprovalRequestNotFound, IdempotencyKeyConflict
from app.core.idempotency import get_existing_response, store_response
from app.core.state_machine import InvalidTransitionError
from app.schemas.approval_request import (
    ApprovalRequestCreate,
    ApprovalRequestList,
    ApprovalRequestOut,
)
from app.schemas.decision import ApproveIn, CancelIn, RejectIn
from app.services import approval_service

router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/approval-requests", tags=["approval-requests"])
settings = get_settings()


def _run_with_idempotency(
    *,
    db: Session,
    request: Request,
    workspace_id: str,
    endpoint: str,
    body: dict,
    success_status: int,
    handler: Callable[[], ApprovalRequestOut],
) -> tuple[ApprovalRequestOut | dict, int]:
    """Общая обёртка идемпотентности для мутирующих эндпоинтов.

    Если заголовок Idempotency-Key не передан, каждый запрос выполняется как
    новый (клиент сам отвечает за дедупликацию). Это осознанный компромисс,
    см. DESIGN.md.
    """

    key = request.headers.get(settings.IDEMPOTENCY_HEADER)
    if not key:
        result = handler()
        return result, success_status

    try:
        existing = get_existing_response(
            db, workspace_id=workspace_id, key=key, endpoint=endpoint, body=body
        )
    except IdempotencyKeyConflict as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Idempotency-Key already used with a different request body",
        ) from exc

    if existing is not None:
        return existing["body"], existing["status"]

    result = handler()
    response_status = success_status
    store_response(
        db,
        workspace_id=workspace_id,
        key=key,
        endpoint=endpoint,
        body=body,
        response_status=response_status,
        response_body=result.model_dump(mode="json"),
    )
    db.commit()
    return result, response_status


def _to_out(model) -> ApprovalRequestOut:
    return ApprovalRequestOut(
        id=model.id,
        workspaceId=model.workspace_id,
        sourceType=model.source_type,
        sourceId=model.source_id,
        title=model.title,
        description=model.description,
        reviewerUserIds=model.reviewer_user_ids,
        status=model.status,
        createdByUserId=model.created_by_user_id,
        decidedByUserId=model.decided_by_user_id,
        decidedAt=model.decided_at,
        decisionNote=model.decision_note,
        createdAt=model.created_at,
        updatedAt=model.updated_at,
    )


@router.post("", response_model=ApprovalRequestOut, status_code=status.HTTP_201_CREATED)
def create_approval_request(
    workspace_id: str,
    payload: ApprovalRequestCreate,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_action(Action.CREATE)),
):
    def _handler() -> ApprovalRequestOut:
        model = approval_service.create_approval_request(
            db, workspace_id=workspace_id, actor_user_id=auth.user_id, data=payload
        )
        return _to_out(model)

    result, response_status = _run_with_idempotency(
        db=db,
        request=request,
        workspace_id=workspace_id,
        endpoint="create_approval_request",
        body=payload.model_dump(mode="json"),
        success_status=status.HTTP_201_CREATED,
        handler=_handler,
    )
    return result


@router.get("", response_model=ApprovalRequestList)
def list_approval_requests(
    workspace_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_action(Action.READ)),
):
    items, total = approval_service.list_approval_requests(
        db, workspace_id=workspace_id, limit=limit, offset=offset
    )
    return ApprovalRequestList(
        items=[_to_out(i) for i in items], total=total, limit=limit, offset=offset
    )


@router.get("/{request_id}", response_model=ApprovalRequestOut)
def get_approval_request(
    workspace_id: str,
    request_id: str,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_action(Action.READ)),
):
    try:
        model = approval_service.get_approval_request(
            db, workspace_id=workspace_id, request_id=request_id
        )
    except ApprovalRequestNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found") from exc
    return _to_out(model)


@router.post("/{request_id}/approve", response_model=ApprovalRequestOut)
def approve_approval_request(
    workspace_id: str,
    request_id: str,
    payload: ApproveIn,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_action(Action.DECIDE)),
):
    def _handler() -> ApprovalRequestOut:
        try:
            model = approval_service.approve(
                db,
                workspace_id=workspace_id,
                request_id=request_id,
                actor_user_id=auth.user_id,
                comment=payload.comment,
            )
        except ApprovalRequestNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found") from exc
        except InvalidTransitionError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot approve a request in status '{exc.current.value}'",
            ) from exc
        return _to_out(model)

    result, _ = _run_with_idempotency(
        db=db,
        request=request,
        workspace_id=workspace_id,
        endpoint=f"approve:{request_id}",
        body=payload.model_dump(mode="json"),
        success_status=status.HTTP_200_OK,
        handler=_handler,
    )
    return result


@router.post("/{request_id}/reject", response_model=ApprovalRequestOut)
def reject_approval_request(
    workspace_id: str,
    request_id: str,
    payload: RejectIn,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_action(Action.DECIDE)),
):
    def _handler() -> ApprovalRequestOut:
        try:
            model = approval_service.reject(
                db,
                workspace_id=workspace_id,
                request_id=request_id,
                actor_user_id=auth.user_id,
                reason=payload.reason,
            )
        except ApprovalRequestNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found") from exc
        except InvalidTransitionError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot reject a request in status '{exc.current.value}'",
            ) from exc
        return _to_out(model)

    result, _ = _run_with_idempotency(
        db=db,
        request=request,
        workspace_id=workspace_id,
        endpoint=f"reject:{request_id}",
        body=payload.model_dump(mode="json"),
        success_status=status.HTTP_200_OK,
        handler=_handler,
    )
    return result


@router.post("/{request_id}/cancel", response_model=ApprovalRequestOut)
def cancel_approval_request(
    workspace_id: str,
    request_id: str,
    payload: CancelIn,
    request: Request,
    db: Session = Depends(get_db),
    auth: AuthContext = Depends(require_action(Action.CANCEL)),
):
    def _handler() -> ApprovalRequestOut:
        try:
            model = approval_service.cancel(
                db,
                workspace_id=workspace_id,
                request_id=request_id,
                actor_user_id=auth.user_id,
                reason=payload.reason,
            )
        except ApprovalRequestNotFound as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found") from exc
        except InvalidTransitionError as exc:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Cannot cancel a request in status '{exc.current.value}'",
            ) from exc
        return _to_out(model)

    result, _ = _run_with_idempotency(
        db=db,
        request=request,
        workspace_id=workspace_id,
        endpoint=f"cancel:{request_id}",
        body=payload.model_dump(mode="json"),
        success_status=status.HTTP_200_OK,
        handler=_handler,
    )
    return result
