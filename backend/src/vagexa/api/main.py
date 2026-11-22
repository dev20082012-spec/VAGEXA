from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from vagexa.adapters.persistence.session import dispose_engine, init_engine
from vagexa.api.errors import FieldError, Problem, problem_body
from vagexa.api.middleware import RequestContextMiddleware
from vagexa.api.routers import (
    analysis,
    auth,
    cases,
    correlation,
    graph,
    health,
    infrastructure,
    ingestion,
    investigation,
    users,
)
from vagexa.config import Settings, load_settings
from vagexa.logging_config import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    dispose_engine()


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved = settings or load_settings()
    configure_logging(resolved.log_level)
    init_engine(resolved)
    production = resolved.environment == "production"
    app = FastAPI(
        title="VAGEXA",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=None if production else "/docs",
        redoc_url=None,
        openapi_url=None if production else "/openapi.json",
    )
    app.state.settings = resolved
    app.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "X-Request-ID", "X-CSRF-Token"],
    )
    app.add_middleware(RequestContextMiddleware)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(users.router)
    app.include_router(cases.router)
    app.include_router(ingestion.router)
    app.include_router(analysis.router)
    app.include_router(graph.router)
    app.include_router(infrastructure.router)
    app.include_router(correlation.router)
    app.include_router(investigation.router)
    if resolved.static_dir:
        _serve_frontend(app, resolved.static_dir)

    @app.exception_handler(Problem)
    async def handle_problem(request: Request, exc: Problem) -> JSONResponse:
        request_id = str(getattr(request.state, "request_id", ""))
        return JSONResponse(
            status_code=exc.status,
            content=problem_body(exc, request_id, request.url.path),
            media_type="application/problem+json",
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = str(getattr(request.state, "request_id", ""))
        errors = [
            FieldError(
                field=".".join(str(part) for part in err.get("loc", ()) if part != "body"),
                reason=err["msg"],
            )
            for err in exc.errors()
        ]
        problem = Problem(422, "invalid", "Invalid request", "The request could not be validated.", errors)
        return JSONResponse(
            status_code=422,
            content=problem_body(problem, request_id, request.url.path),
            media_type="application/problem+json",
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = str(getattr(request.state, "request_id", ""))
        slug = "not-found" if exc.status_code == 404 else "internal"
        title = "Not available" if exc.status_code == 404 else "Request failed"
        problem = Problem(exc.status_code, slug, title, "The request could not be completed.")
        return JSONResponse(
            status_code=exc.status_code,
            content=problem_body(problem, request_id, request.url.path),
            media_type="application/problem+json",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
        request_id = str(getattr(request.state, "request_id", ""))
        get_logger("vagexa.error").error("unhandled", error_type=type(exc).__name__)
        problem = Problem(500, "internal", "Something went wrong", "The request could not be completed.")
        return JSONResponse(
            status_code=500,
            content=problem_body(problem, request_id, request.url.path),
            media_type="application/problem+json",
        )

    return app


def _serve_frontend(app: FastAPI, directory: str) -> None:
    """Serve the built investigator app from the same origin as the API."""
    root = Path(directory).resolve()
    index = root / "index.html"
    if not index.is_file():
        raise RuntimeError("VAGEXA_STATIC_DIR does not contain index.html")

    def page(full_path: str = "") -> FileResponse:
        candidate = (root / full_path).resolve() if full_path else index
        try:
            candidate.relative_to(root)
        except ValueError:
            return FileResponse(index)
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)

    app.add_api_route("/", page, methods=["GET"], include_in_schema=False)
    app.add_api_route("/{full_path:path}", page, methods=["GET"], include_in_schema=False)


def main() -> None:
    import uvicorn

    load_settings()
    uvicorn.run(
        "vagexa.api.main:create_app",
        factory=True,
        host="127.0.0.1",
        port=8000,
        log_config=None,
    )
