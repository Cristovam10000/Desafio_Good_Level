from fastapi import APIRouter
from app.infra.db import health_check

router = APIRouter()

@router.get("/healthz")
def healthz():
    return {"status": "ok"}

@router.get("/readyz")
def readyz():
    return health_check()
