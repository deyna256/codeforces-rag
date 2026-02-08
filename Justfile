up:
    docker compose up -d

down:
    docker compose down

rag-sync:
    cd rag && uv sync

rag-run:
    cd rag && uv run uvicorn src.api:app --reload

health:
    curl -s localhost:8000/health | python -m json.tool

start: up rag-sync rag-run

clean:
    docker compose down
    rm -rf .volumes

nuke: clean
    rm -rf rag/.venv rag/uv.lock rag/src/__pycache__
