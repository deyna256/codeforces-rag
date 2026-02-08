from .chunker import chunk_problem
from .db import qdrant_upsert_chunks, upsert_problem
from .embedder import embed_texts
from .models import ParserResponse, Problem


async def index_contest(resp: ParserResponse) -> int:
    all_chunks = []

    for pp in resp.problems:
        problem = Problem(
            problem_id=f"{pp.contest_id}{pp.id}",
            contest_id=pp.contest_id,
            name=pp.title,
            rating=pp.rating,
            tags=pp.tags,
            statement=pp.statement or None,
            editorial=pp.explanation or None,
            time_limit=pp.time_limit or None,
            memory_limit=pp.memory_limit or None,
            url=f"https://codeforces.com/contest/{pp.contest_id}/problem/{pp.id}",
        )
        await upsert_problem(problem)
        all_chunks.extend(chunk_problem(problem))

    if all_chunks:
        texts = [c.text for c in all_chunks]
        vectors = embed_texts(texts)
        qdrant_upsert_chunks(all_chunks, vectors)

    return len(resp.problems)
