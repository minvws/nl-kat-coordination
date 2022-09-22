from fastapi import APIRouter
from fastapi.responses import RedirectResponse

from boefjes.katalogus.routers import organisations, repositories
from boefjes.katalogus.routers import plugins, settings

router = APIRouter()
router.include_router(organisations.router)
router.include_router(repositories.router)
router.include_router(plugins.router)
router.include_router(settings.router)


@router.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")
