from fastapi import FastAPI

api_v1_prefix = "/api/v1"


def register_routers(app: FastAPI) -> None:
    """Register all v1 routers."""
    from app.api.v1 import (
        ai,
        audit_logs,
        auth,
        dashboard,
        equipment,
        experiments,
        exports,
        learning_plans,
        members,
        notifications,
        projects,
        search,
        skills,
        system,
        tasks,
        users,
        wechat,
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
    app.include_router(equipment.qr_router, prefix=api_v1_prefix)
    app.include_router(dashboard.router, prefix=api_v1_prefix)
    app.include_router(notifications.router, prefix=api_v1_prefix)
    app.include_router(search.router, prefix=api_v1_prefix)
    app.include_router(exports.router, prefix=api_v1_prefix)
    app.include_router(audit_logs.router, prefix=api_v1_prefix)
    app.include_router(ai.router, prefix=api_v1_prefix)
    app.include_router(system.router, prefix=api_v1_prefix)
    app.include_router(wechat.router, prefix=api_v1_prefix)
