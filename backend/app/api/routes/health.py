from fastapi import APIRouter

from ..deps import Ctx

router = APIRouter(tags=["health"])


@router.get("/healthz")
def health(ctx: Ctx) -> dict:
    return {
        "status": "ok",
        "version": "1.0.0",
        "storage": ctx.settings.storage,
        "ai_enabled": bool(ctx.ai.client),
        "model": ctx.settings.gemini_model,
    }


@router.get("/readyz")
def ready(ctx: Ctx) -> dict[str, str]:
    ctx.repo.read()
    return {"status": "ready"}
