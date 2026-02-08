import uuid

import asyncpg
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    Range,
    VectorParams,
)

from .config import settings
from .models import Chunk, Problem, ProblemListItem

COLLECTION = "codeforces"
VECTOR_DIM = 1536

pg_pool: asyncpg.Pool | None = None
qdrant: QdrantClient | None = None


async def init_pg() -> asyncpg.Pool:
    global pg_pool
    pg_pool = await asyncpg.create_pool(settings.POSTGRES_URL)
    async with pg_pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS problems (
                problem_id   TEXT PRIMARY KEY,
                contest_id   TEXT NOT NULL,
                name         TEXT NOT NULL,
                rating       INTEGER,
                tags         TEXT[] DEFAULT '{}',
                statement    TEXT,
                editorial    TEXT,
                time_limit   TEXT,
                memory_limit TEXT,
                url          TEXT,
                created_at   TIMESTAMP DEFAULT NOW()
            );
            CREATE INDEX IF NOT EXISTS idx_rating ON problems(rating);
            CREATE INDEX IF NOT EXISTS idx_tags ON problems USING GIN(tags);
            CREATE INDEX IF NOT EXISTS idx_contest ON problems(contest_id);
        """)
    return pg_pool


def init_qdrant() -> QdrantClient:
    global qdrant
    qdrant = QdrantClient(url=settings.QDRANT_URL)
    if not qdrant.collection_exists(COLLECTION):
        qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )
    qdrant.create_payload_index(COLLECTION, "rating", PayloadSchemaType.INTEGER)
    qdrant.create_payload_index(COLLECTION, "tags", PayloadSchemaType.KEYWORD)
    qdrant.create_payload_index(COLLECTION, "chunk_type", PayloadSchemaType.KEYWORD)
    return qdrant


async def close_pg():
    global pg_pool
    if pg_pool:
        await pg_pool.close()
        pg_pool = None


def close_qdrant():
    global qdrant
    if qdrant:
        qdrant.close()
        qdrant = None


# ── PostgreSQL operations ──


async def upsert_problem(p: Problem):
    async with pg_pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO problems (problem_id, contest_id, name, rating, tags,
                                  statement, editorial, time_limit, memory_limit, url)
            VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            ON CONFLICT (problem_id) DO UPDATE SET
                name         = EXCLUDED.name,
                rating       = EXCLUDED.rating,
                tags         = EXCLUDED.tags,
                statement    = EXCLUDED.statement,
                editorial    = EXCLUDED.editorial,
                time_limit   = EXCLUDED.time_limit,
                memory_limit = EXCLUDED.memory_limit,
                url          = EXCLUDED.url
            """,
            p.problem_id,
            p.contest_id,
            p.name,
            p.rating,
            p.tags,
            p.statement,
            p.editorial,
            p.time_limit,
            p.memory_limit,
            p.url,
        )


async def get_problems(
    rating_min: int | None = None,
    rating_max: int | None = None,
    tags: list[str] | None = None,
    contest_id: str | None = None,
    limit: int = 50,
) -> list[ProblemListItem]:
    conditions = []
    args: list = []
    idx = 1

    if rating_min is not None:
        conditions.append(f"rating >= ${idx}")
        args.append(rating_min)
        idx += 1
    if rating_max is not None:
        conditions.append(f"rating <= ${idx}")
        args.append(rating_max)
        idx += 1
    if tags:
        conditions.append(f"tags && ${idx}")
        args.append(tags)
        idx += 1
    if contest_id is not None:
        conditions.append(f"contest_id = ${idx}")
        args.append(contest_id)
        idx += 1

    where = (" WHERE " + " AND ".join(conditions)) if conditions else ""
    query = f"SELECT problem_id, contest_id, name, rating, tags, url FROM problems{where} ORDER BY problem_id LIMIT ${idx}"
    args.append(limit)

    async with pg_pool.acquire() as conn:
        rows = await conn.fetch(query, *args)

    return [
        ProblemListItem(
            problem_id=r["problem_id"],
            contest_id=r["contest_id"],
            name=r["name"],
            rating=r["rating"],
            tags=list(r["tags"]) if r["tags"] else [],
            url=r["url"],
        )
        for r in rows
    ]


async def get_problem_text(problem_id: str, field: str) -> dict | None:
    if field not in ("statement", "editorial"):
        return None
    async with pg_pool.acquire() as conn:
        row = await conn.fetchrow(
            f"SELECT problem_id, name, {field} AS text FROM problems WHERE problem_id = $1",
            problem_id,
        )
    if not row:
        return None
    return {"problem_id": row["problem_id"], "name": row["name"], "text": row["text"]}


# ── Qdrant operations ──


def qdrant_upsert_chunks(chunks: list[Chunk], vectors: list[list[float]]):
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=vec,
            payload={
                "problem_id": c.problem_id,
                "name": c.name,
                "rating": c.rating,
                "tags": c.tags,
                "chunk_type": c.chunk_type,
                "text": c.text[:500],
            },
        )
        for c, vec in zip(chunks, vectors)
    ]
    qdrant.upsert(collection_name=COLLECTION, points=points)


def qdrant_search(
    vector: list[float],
    rating_min: int | None = None,
    rating_max: int | None = None,
    tags: list[str] | None = None,
    chunk_type: str | None = None,
    limit: int = 10,
) -> list[dict]:
    must = []
    if rating_min is not None or rating_max is not None:
        must.append(
            FieldCondition(
                key="rating",
                range=Range(
                    gte=rating_min,
                    lte=rating_max,
                ),
            )
        )
    if tags:
        must.append(FieldCondition(key="tags", match=MatchAny(any=tags)))
    if chunk_type:
        must.append(FieldCondition(key="chunk_type", match=MatchValue(value=chunk_type)))

    q_filter = Filter(must=must) if must else None

    hits = qdrant.query_points(
        collection_name=COLLECTION,
        query=vector,
        query_filter=q_filter,
        limit=limit,
        with_payload=True,
    ).points

    results = []
    for h in hits:
        p = h.payload
        results.append(
            {
                "problem_id": p["problem_id"],
                "name": p["name"],
                "rating": p.get("rating"),
                "tags": p.get("tags", []),
                "score": h.score,
                "snippet": p.get("text", ""),
            }
        )
    return results
