import pytest
from pydantic import ValidationError

from src.config import Settings


class TestSettings:
    def test_valid_openai_key_accepted(self):
        s = Settings(OPENAI_API_KEY="sk-valid-test-key")

        assert s.OPENAI_API_KEY == "sk-valid-test-key"

    def test_invalid_openai_key_rejected(self):
        with pytest.raises(ValidationError, match="must start with 'sk-'"):
            Settings(OPENAI_API_KEY="invalid-key-no-prefix")

    def test_default_values(self):
        s = Settings(OPENAI_API_KEY="sk-test")

        assert s.POSTGRES_URL == "postgresql://codeforces:codeforces@localhost:5432/codeforces"
        assert s.QDRANT_URL == "http://localhost:6333"
        assert s.PARSER_BASE_URL == "http://localhost:8001"
        assert s.EMBEDDING_MODEL == "text-embedding-3-small"
