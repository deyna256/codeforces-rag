from litestar import Litestar
from litestar.openapi.config import OpenAPIConfig

from config import get_settings
from infrastructure.errors import (
    CodeforcesEditorialError,
    ContestNotFoundError,
)
from infrastructure.parsers import ParsingError, URLParsingError
from infrastructure.parsers.errors import (
    EditorialContentFetchError,
    EditorialContentParseError,
    EditorialNotFoundError,
    LLMSegmentationError,
)
from api.exceptions import exception_to_http_response
from api.routes import ContestController, ProblemController


def create_app() -> Litestar:
    settings = get_settings()

    exception_handlers = {
        CodeforcesEditorialError: exception_to_http_response,
        ContestNotFoundError: exception_to_http_response,
        EditorialContentFetchError: exception_to_http_response,
        EditorialContentParseError: exception_to_http_response,
        EditorialNotFoundError: exception_to_http_response,
        LLMSegmentationError: exception_to_http_response,
        ParsingError: exception_to_http_response,
        URLParsingError: exception_to_http_response,
    }

    openapi_config = OpenAPIConfig(
        title="Codeforces Editorial Finder API",
        version="1.0.0",
        description="API for finding and extracting editorials for Codeforces problems",
    )

    app = Litestar(
        route_handlers=[ContestController, ProblemController],
        exception_handlers=exception_handlers,
        debug=settings.log_level == "DEBUG",
        openapi_config=openapi_config,
    )

    return app


app = create_app()
