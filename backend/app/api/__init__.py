from fastapi import FastAPI

api_v1_prefix = "/api/v1"


def register_routers(app: FastAPI) -> None:
    """Register all v1 routers."""
    from app.api.v1 import (
        auth,
        equipment,
        experiments,
        learning_plans,
        members,
        projects,
        skills,
        tasks,
        users,
        weekly_reports,
    )

    app.include_router(auth.router, prefix=api_v1_prefix)
    app.include_router(users.router, prefix=api_v1_prefix)
    app.include_router(members.router, prefix=api_v1_prefix)
    app.include_router(skills.router, prefix=api_v1_prefix)
    app.include_router(skills.member_skills_router, prefix=api_v1_prefix)
    app.include_router(learning_plans.router, prefix=api_v1_prefix)
    app.include_router(weekly_reports.router, prefix=api_v1_prefix)
    app.include_router(projects.router, prefix=api_v1_prefix)
    app.include_router(projects.milestones_router, prefix=api_v1_prefix)
    app.include_router(tasks.router, prefix=api_v1_prefix)
    app.include_router(experiments.router, prefix=api_v1_prefix)
    app.include_router(experiments.attachments_router, prefix=api_v1_prefix)
    app.include_router(equipment.router, prefix=api_v1_prefix)
    app.include_router(equipment.bookings_router, prefix=api_v1_prefix)
    app.include_router(equipment.borrows_router, prefix=api_v1_prefix)
    app.include_router(equipment.maintenance_router, prefix=api_v1_prefix)
