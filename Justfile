# List available commands
default:
    @just --list

# Build and start all services
up:
    docker compose up -d --build

# Stop all services
down:
    docker compose down

# Stop services and remove volumes
clean:
    docker compose down
    rm -rf .volumes

# Run all tests
test:
    cd parser && uv run pytest
    cd rag && uv run pytest

# Check code style (ruff check)
style:
    cd parser && uv run ruff check .
    cd rag && uv run ruff check .

# Type checking (ty)
type:
    cd parser && uv run ty check
    cd rag && uv run ty check

# Format code (ruff format)
format:
    cd parser && uv run ruff format .
    cd rag && uv run ruff format .
