from pydantic import BaseModel


class ParserProblem(BaseModel):
    contest_id: str
    id: str
    title: str
    statement: str = ""
    rating: int | None = None
    tags: list[str] = []
    time_limit: str = ""
    memory_limit: str = ""
    explanation: str = ""


class ParserResponse(BaseModel):
    contest_id: str
    title: str
    problems: list[ParserProblem]


class Problem(BaseModel):
    problem_id: str
    contest_id: str
    name: str
    rating: int | None = None
    tags: list[str] = []
    statement: str | None = None
    editorial: str | None = None
    time_limit: str | None = None
    memory_limit: str | None = None
    url: str | None = None


class LoadContestRequest(BaseModel):
    contest_url: str


class SearchRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "query": "dynamic programming on subarrays",
                    "limit": 10,
                }
            ]
        }
    }

    query: str
    rating_min: int | None = None
    rating_max: int | None = None
    tags: list[str] | None = None
    chunk_type: str | None = None
    limit: int = 10


class SearchResult(BaseModel):
    problem_id: str
    name: str
    rating: int | None = None
    tags: list[str] = []
    score: float
    snippet: str


class ProblemListItem(BaseModel):
    problem_id: str
    contest_id: str
    name: str
    rating: int | None = None
    tags: list[str] = []
    url: str | None = None


class Chunk(BaseModel):
    problem_id: str
    name: str
    rating: int | None = None
    tags: list[str] = []
    chunk_type: str
    text: str
