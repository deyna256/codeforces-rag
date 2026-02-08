from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_file": (".env", "../.env")}

    POSTGRES_URL: str = "postgresql://codeforces:codeforces@localhost:5432/codeforces"
    QDRANT_URL: str = "http://localhost:6333"
    OPENAI_API_KEY: str = ""
    PARSER_BASE_URL: str = "http://localhost:8001"
    EMBEDDING_MODEL: str = "text-embedding-3-small"


settings = Settings()
