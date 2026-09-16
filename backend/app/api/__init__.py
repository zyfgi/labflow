from fastapi import FastAPI

api_v1_prefix = "/api/v1"


def register_routers(app: FastAPI) -> None:
    """Register all v1 routers."""
    from app.api.v1 import auth, learning_plans, members, skills, users

    app.include_router(auth.router, prefix=api_v1_prefix)
    app.include_router(users.router, prefix=api_v1_prefix)
    app.include_router(members.router, prefix=api_v1_prefix)
    app.include_router(skills.router, prefix=api_v1_prefix)
    app.include_router(skills.member_skills_router, prefix=api_v1_prefix)
    app.include_router(learning_plans.router, prefix=api_v1_prefix)
