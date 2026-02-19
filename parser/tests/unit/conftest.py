import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def api_client():
    return AsyncMock()


@pytest.fixture
def page_parser():
    return AsyncMock()


@pytest.fixture
def editorial_parser():
    return AsyncMock()


@pytest.fixture
def url_parser():
    return MagicMock()
