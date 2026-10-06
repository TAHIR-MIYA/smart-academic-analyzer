"""FastAPI application entry point."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import routes_analysis, routes_documents, routes_health, routes_model
from app.config import get_settings
from app.db.database import init_db
from app.logging_config import setup_logging
from app.nlp.resources import check_nlp_resources
from app.utils.errors import AppError

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    setup_logging(settings)
    logger.info("Starting %s v%s", settings.app_name, settings.app_version)
    init_db()
    status = check_nlp_resources()
    if not status["ready"]:
        logger.warning("Run these to fix missing NLP resources: %s", status["fix"])
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        logger.info("%s %s -> %s: %s", request.method, request.url.path, exc.code, exc.message)
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, "details": exc.details}},
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(request: Request, exc: Exception):
        logger.exception("Unhandled error on %s %s", request.method, request.url.path)
        return JSONResponse(
            status_code=500,
            content={"error": {"code": "internal_error",
                               "message": "An unexpected server error occurred.", "details": None}},
        )

    app.include_router(routes_health.router)
    app.include_router(routes_documents.router)
    app.include_router(routes_analysis.router)
    app.include_router(routes_model.router)
    return app


app = create_app()
