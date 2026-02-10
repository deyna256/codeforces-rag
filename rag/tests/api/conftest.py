import pytest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from src.api import app


@pytest.fixture
def client():
    with (
        patch("src.db.init_pg", new_callable=AsyncMock),
        patch("src.db.init_qdrant"),
        patch("src.db.close_pg", new_callable=AsyncMock),
        patch("src.db.close_qdrant"),
    ):
        with TestClient(app) as c:
            yield c
