from app.models.approval_request import FINAL_STATUSES, ApprovalStatus

# Разрешённые переходы. Из pending можно уйти в любое финальное состояние,
# из финального состояния переходов нет вообще.
ALLOWED_TRANSITIONS: dict[ApprovalStatus, set[ApprovalStatus]] = {
    ApprovalStatus.PENDING: {
        ApprovalStatus.APPROVED,
        ApprovalStatus.REJECTED,
        ApprovalStatus.CANCELLED,
    },
    ApprovalStatus.APPROVED: set(),
    ApprovalStatus.REJECTED: set(),
    ApprovalStatus.CANCELLED: set(),
}


class InvalidTransitionError(Exception):
    def __init__(self, current: ApprovalStatus, target: ApprovalStatus):
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition from {current} to {target}")


def is_final(status: ApprovalStatus) -> bool:
    return status in FINAL_STATUSES


def assert_transition_allowed(current: ApprovalStatus, target: ApprovalStatus) -> None:
    if target not in ALLOWED_TRANSITIONS.get(current, set()):
        raise InvalidTransitionError(current, target)
