import os

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import StaticPool, create_engine
from sqlalchemy.orm import sessionmaker

from app import models  # noqa: F401  registers models on Base.metadata
from app.database import Base, get_db
from app.main import app

# Общий in-memory SQLite engine на весь тестовый процесс (StaticPool - чтобы
# все подключения шарили одну и ту же in-memory базу).
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


def _override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def auth_headers(workspace_id: str, user_id: str, actions: list[str]) -> dict:
    return {
        "X-Workspace-Id": workspace_id,
        "X-User-Id": user_id,
        "X-Actions": ",".join(actions),
    }


ALL_ACTIONS = ["approval:read", "approval:create", "approval:decide", "approval:cancel"]
