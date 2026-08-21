from fastapi import APIRouter

from app.api.v1 import (
    auth,
    autonomous_migration,
    jobs,
    migrations,
    organizations,
    projects,
    users,
)

router = APIRouter()

router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(organizations.router, prefix="/organizations", tags=["organizations"])
router.include_router(projects.router, prefix="/projects", tags=["projects"])
router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
router.include_router(migrations.router, prefix="/migrations", tags=["migrations"])
router.include_router(
    autonomous_migration.router,
    prefix="/autonomous",
    tags=["autonomous migration"],
)
