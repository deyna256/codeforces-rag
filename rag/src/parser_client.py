import httpx

from .config import settings
from .models import ParserResponse


async def fetch_contest(contest_url: str) -> ParserResponse:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.PARSER_BASE_URL}/contest",
            json={"url": contest_url},
        )
        resp.raise_for_status()
        return ParserResponse.model_validate(resp.json())
