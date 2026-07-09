import hashlib
import json

from sqlalchemy.orm import Session

from app.core.exceptions import IdempotencyKeyConflict
from app.models.idempotency import IdempotencyRecord


def fingerprint(body: dict) -> str:
    raw = json.dumps(body, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def get_existing_response(
    db: Session, *, workspace_id: str, key: str, endpoint: str, body: dict
) -> dict | None:
    """Возвращает сохранённый ответ, если такой (workspace, key, endpoint) уже
    обрабатывался. Бросает IdempotencyKeyConflict, если ключ переиспользован
    с другим телом запроса (это ошибка клиента - 409/422 на уровне API)."""

    record = (
        db.query(IdempotencyRecord)
        .filter_by(workspace_id=workspace_id, idempotency_key=key, endpoint=endpoint)
        .one_or_none()
    )
    if record is None:
        return None

    if record.request_fingerprint != fingerprint(body):
        raise IdempotencyKeyConflict()

    return {"status": record.response_status, "body": record.response_body}


def store_response(
    db: Session,
    *,
    workspace_id: str,
    key: str,
    endpoint: str,
    body: dict,
    response_status: int,
    response_body: dict,
) -> None:
    record = IdempotencyRecord(
        workspace_id=workspace_id,
        idempotency_key=key,
        endpoint=endpoint,
        request_fingerprint=fingerprint(body),
        response_status=response_status,
        response_body=response_body,
    )
    db.add(record)
