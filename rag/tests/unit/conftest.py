import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_pg_conn(monkeypatch):
    conn = AsyncMock()
    pool = MagicMock()
    pool.acquire.return_value.__aenter__ = AsyncMock(return_value=conn)
    pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr("src.db.pg_pool", pool)
    return conn


@pytest.fixture
def mock_qdrant_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr("src.db.qdrant", client)
    return client


@pytest.fixture
def mock_openai_client(monkeypatch):
    client = MagicMock()
    monkeypatch.setattr("src.embedder._client", client)
    return client
