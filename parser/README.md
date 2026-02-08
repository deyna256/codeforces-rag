# Codeforces Editorial Finder

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![LiteStar](https://img.shields.io/badge/LiteStar-2.0+-orange.svg)](https://litestar.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

HTTP API for extracting editorials/tutorials for Codeforces problems using AI (GPT-4o).

## Quick Start (Docker)

```bash
cp .env.example .env  # Add your OPENAI_API_KEY
docker-compose up -d
```
API available at `http://localhost:8000`

## API Usage

**POST** `/editorial`
```json
{ "url": "https://codeforces.com/problemset/problem/1/A" }
```

### Supported Formats
- `https://codeforces.com/problemset/problem/{contest_id}/{problem_id}`

## Development

Managed with [uv](https://github.com/astral-sh/uv) and [just](https://github.com/casey/just).

### Just Commands
- `just build` / `just up` / `just down` - Docker management
- `just test` - Run pytest
- `just format` / `just lint` - Ruff checks
- `just typecheck` - Type validation

## Architecture

### System Layers
```
┌─────────────────────────────────────────┐
│   Presentation Layer (HTTP API)         │  ← LiteStar routes, schemas
├─────────────────────────────────────────┤
│   Application Layer (Use Cases)         │  ← Orchestrator, cache logic
├─────────────────────────────────────────┤
│   Domain Layer (Business Logic)         │  ← Parsers, extractors, models
├─────────────────────────────────────────┤
│   Infrastructure Layer (External APIs)  │  ← HTTP, OpenAI, Redis clients
└─────────────────────────────────────────┘
```

### Project Structure
```
src/
├── presentation/  # HTTP API (Routes, Schemas, Apps)
├── application/   # Orchestration & Use cases
├── domain/        # Business logic (Parsers, Extractors, Fetchers)
├── infrastructure/# External clients (HTTP, OpenAI, Redis)
└── config.py      # Pydantic settings
```

---
[deyna256](https://github.com/deyna256) | MIT License
