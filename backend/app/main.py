from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        version="1.0.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        debug=settings.DEBUG,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["health"])
    def health() -> dict:
        return {"status": "ok", "app": settings.APP_NAME, "env": settings.ENV}

    # feature routers are registered in app.api.register_routers(app)
    from app.api import register_routers

    register_routers(app)

    return app


app = create_app()
