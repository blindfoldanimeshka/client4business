from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status

from app.config import get_settings

settings = get_settings()


class Action:
    READ = "approval:read"
    CREATE = "approval:create"
    DECIDE = "approval:decide"
    CANCEL = "approval:cancel"


@dataclass(frozen=True)
class AuthContext:
    workspace_id: str
    user_id: str
    actions: frozenset[str]

    def has(self, action: str) -> bool:
        return action in self.actions


def get_auth_context(request: Request) -> AuthContext:
    """Auth-заглушка для локального запуска.

    Запрос должен содержать заголовки:
      X-Workspace-Id: usr-owned workspace id
      X-User-Id: id пользователя, от имени которого выполняется запрос
      X-Actions: список действий через запятую, например
                 "approval:read,approval:create,approval:decide,approval:cancel"

    В реальной системе эти данные пришли бы из проверенного токена (JWT/mTLS/
    внутренний auth-сервис) - здесь мы явно доверяем заголовкам, т.к. это
    локальная заглушка, описанная в README.
    """

    workspace_id = request.headers.get(settings.AUTH_WORKSPACE_HEADER)
    user_id = request.headers.get(settings.AUTH_USER_HEADER)
    actions_raw = request.headers.get(settings.AUTH_ACTIONS_HEADER, "")

    if not workspace_id or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing auth headers: X-Workspace-Id / X-User-Id are required",
        )

    actions = frozenset(a.strip() for a in actions_raw.split(",") if a.strip())

    return AuthContext(workspace_id=workspace_id, user_id=user_id, actions=actions)


def require_action(action: str):
    """Dependency-фабрика: проверяет наличие нужного действия в скоупе,
    а также что workspace из пути совпадает с workspace из auth-контекста
    (изоляция данных между workspace)."""

    def _dependency(
        workspace_id: str,
        auth: AuthContext = Depends(get_auth_context),
    ) -> AuthContext:
        if auth.workspace_id != workspace_id:
            # Намеренно 404, а не 403: не подтверждаем даже факт существования
            # чужого workspace.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
        if not auth.has(action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required action: {action}",
            )
        return auth

    return _dependency
