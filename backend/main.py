import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.research import router as research_router
from core.config import settings
from core.run_logger import install_run_logging


logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
install_run_logging()


def create_app() -> FastAPI:
    application = FastAPI(
        title="Deep Research Agent API",
        version="2.0.0",
        description="Run the deep-research graph and return a completed report.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|192\.168\.\d+\.\d+)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
    )
    application.include_router(research_router)
    return application


app = create_app()
