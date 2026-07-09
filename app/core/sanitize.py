"""Хелперы, гарантирующие, что в логи, аудит и события попадают только
идентификаторы и продуктовые поля заявки - без секретов, токенов, email,
storage keys, signed URL и сырых provider payload.

ApprovalRequest в этом сервисе и так не хранит подобные поля (см. модель) -
это единая точка, куда стоит смотреть при добавлении новых полей, чтобы не
допустить утечки в будущем.
"""

ALLOWED_AUDIT_FIELDS = {
    "id",
    "workspace_id",
    "source_type",
    "source_id",
    "title",
    "reviewer_user_ids",
    "status",
    "created_by_user_id",
    "decided_by_user_id",
    "decision_note",
    "action",
}


def sanitize_for_audit(payload: dict) -> dict:
    """Оставляет только разрешённые поля. При добавлении новых полей в модель
    их нужно явно занести в ALLOWED_AUDIT_FIELDS, иначе они будут отброшены -
    это защита "по умолчанию deny", а не "по умолчанию allow"."""
    return {k: v for k, v in payload.items() if k in ALLOWED_AUDIT_FIELDS}
