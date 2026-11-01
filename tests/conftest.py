import os

# Use a throwaway SQLite file for tests before app modules are imported.
os.environ.setdefault("DATABASE_URL", "sqlite:///./tests/test_gati.db")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.db import Base, engine, SessionLocal  # noqa: E402
from app.main import _seed, app  # noqa: E402


@pytest.fixture()
def client():
    """A TestClient backed by a freshly created, seeded test database."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as session:
        _seed(session)
    with TestClient(app) as client:
        yield client