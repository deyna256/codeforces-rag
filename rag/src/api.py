from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from . import db
from .embedder import embed_texts
from .indexer import index_contest
from .models import LoadContestRequest, ProblemListItem, SearchRequest, SearchResult
from .parser_client import fetch_contest


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.init_pg()
    db.init_qdrant()
    yield
    db.close_qdrant()
    await db.close_pg()


app = FastAPI(title="Codeforces RAG", lifespan=lifespan)


@app.get("/health")
async def health():
    pg_ok = False
    qdrant_ok = False
    qdrant_points = 0
    try:
        async with db.pg_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        pg_ok = True
    except Exception:
        pass
    try:
        info = db.qdrant.get_collection(db.COLLECTION)
        qdrant_ok = True
        qdrant_points = info.points_count
    except Exception:
        pass
    status = "ok" if (pg_ok and qdrant_ok) else "degraded"
    return {"status": status, "postgres": pg_ok, "qdrant": qdrant_ok, "qdrant_points": qdrant_points}


@app.post("/contests/load")
async def load_contest(body: LoadContestRequest):
    resp = await fetch_contest(body.contest_url)
    count = await index_contest(resp)
    return {"contest": resp.title, "problems_loaded": count}


@app.post("/search", response_model=list[SearchResult])
async def search(req: SearchRequest):
    vectors = embed_texts([req.query])
    hits = db.qdrant_search(
        vector=vectors[0],
        rating_min=req.rating_min,
        rating_max=req.rating_max,
        tags=req.tags,
        chunk_type=req.chunk_type,
        limit=req.limit,
    )
    return hits


@app.get("/problems", response_model=list[ProblemListItem])
async def list_problems(
    rating_min: int | None = Query(None),
    rating_max: int | None = Query(None),
    tags: list[str] | None = Query(None),
    contest_id: str | None = Query(None),
    limit: int = Query(50, le=200),
):
    return await db.get_problems(
        rating_min=rating_min,
        rating_max=rating_max,
        tags=tags,
        contest_id=contest_id,
        limit=limit,
    )


@app.get("/problems/{problem_id}/statement")
async def problem_statement(problem_id: str):
    result = await db.get_problem_text(problem_id, "statement")
    if not result:
        raise HTTPException(404, "Problem not found")
    return result


@app.get("/problems/{problem_id}/editorial")
async def problem_editorial(problem_id: str):
    result = await db.get_problem_text(problem_id, "editorial")
    if not result:
        raise HTTPException(404, "Problem not found")
    return result
