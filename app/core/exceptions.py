class ApprovalRequestNotFound(Exception):
    pass


class IdempotencyKeyConflict(Exception):
    """Тот же Idempotency-Key использован с другим телом запроса."""

    pass
