# Quick Start

## Prerequisites

- Docker & Docker Compose
- [uv](https://docs.astral.sh/uv/)
- [just](https://github.com/casey/just) (optional)
- OpenAI API key

## 1. Environment

```bash
cp .env.example .env
```

Fill in `OPENAI_API_KEY` in `.env`. Other variables have working defaults for local development.

| Variable           | Default                                                      |
|--------------------|--------------------------------------------------------------|
| `POSTGRES_URL`     | `postgresql://codeforces:codeforces@localhost:5432/codeforces` |
| `QDRANT_URL`       | `http://localhost:6333`                                      |
| `OPENAI_API_KEY`   | _(required)_                                                 |
| `PARSER_BASE_URL`  | `http://localhost:8001`                                      |
| `EMBEDDING_MODEL`  | `text-embedding-3-small`                                     |

## 2. Start infrastructure

```bash
just up  # or: docker compose up -d
```

Starts Qdrant (`:6333`), PostgreSQL (`:5432`), and Parser (`:8001`).

## 3. Install dependencies

```bash
just rag-sync  # from root
just sync      # from rag/
```

## 4. Run API server

```bash
just rag-run   # from root
just run       # from rag/
```

Or all at once (infra + deps + server):

```bash
just start
```

API is available at `http://localhost:8000`. On startup it creates the `problems` table in PostgreSQL and the `codeforces` collection in Qdrant.

## 5. Health check

```bash
just health
```

```json
{"status": "ok", "postgres": true, "qdrant": true}
```

## 6. Load a contest

```bash
curl -X POST localhost:8000/contests/load \
  -H "Content-Type: application/json" \
  -d '{"contest_url": "https://codeforces.com/contest/1920"}'
```

Pipeline: parser fetches contest data, problems are saved to PostgreSQL, texts are chunked (2000 chars, 200 overlap), embedded via OpenAI, and stored in Qdrant.

## 7. Search

**Semantic search:**

```bash
curl -X POST localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "dynamic programming on subarrays", "rating_min": 1200, "limit": 5}'
```

All parameters except `query` are optional: `rating_min`, `rating_max`, `tags`, `chunk_type`, `limit`.

**Filter by metadata:**

```bash
curl "localhost:8000/problems?rating_min=800&rating_max=1200&limit=10"
```

**Full problem text:**

```bash
curl localhost:8000/problems/1920A/statement
curl localhost:8000/problems/1920A/editorial
```

## 8. Shutdown & cleanup

```bash
just down       # stop containers
just clean      # stop containers + delete .volumes/
just nuke       # clean + delete .venv, uv.lock, __pycache__
```

## API docs

Swagger UI: http://localhost:8000/docs
