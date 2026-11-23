from fastapi import APIRouter

from ...core.errors import find, require
from ...domain.models import Equipment, User
from ...seed.demo_data import seed
from ...services.admin_service import save_equipment
from ...services.catalog_service import page
from ...services.events import audit
from ..deps import Admin
from ..schemas import CertificationChange, EquipmentCreate, EquipmentUpdate, Id
from .catalog import PageLimit

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/equipment")
def catalogue(s: Admin) -> list[Equipment]:
    """List equipment records for the management interface."""
    return list(s.state.equipment.values())


@router.get("/users")
def users(s: Admin) -> list[User]:
    """List users for the management interface."""
    return list(s.state.users.values())


@router.post("/equipment", status_code=201)
def create(s: Admin, payload: EquipmentCreate) -> Equipment:
    """Create an equipment record as an administrator."""
    return s.mutate(lambda state, user: save_equipment(state, user, payload.model_dump(), s.now, s.horizon))


@router.patch("/equipment/{key}")
def edit(s: Admin, key: Id, payload: EquipmentUpdate) -> Equipment:
    """Apply an administrator's patch to an equipment record."""
    return s.mutate(
        lambda state, user: save_equipment(state, user, payload.model_dump(exclude_unset=True), s.now, s.horizon, key)
    )


@router.post("/users/{key}/certifications")
def certifications(s: Admin, key: Id, payload: CertificationChange) -> User:
    """Update a user's certifications and record the change."""

    def operation(state, user):
        target = find(state.users, key, "User")
        target.certifications = sorted((set(target.certifications) | set(payload.add)) - set(payload.remove))
        audit(state, s.now, user.id, "user.certification", key, {"count": len(target.certifications)})
        return target

    return s.mutate(operation)


@router.get("/audit")
def audit_log(s: Admin, limit: PageLimit = 20, cursor: str | None = None) -> dict:
    """Page through audit entries with the newest first."""
    return page(sorted(s.state.audit_log.values(), key=lambda item: item.at, reverse=True), limit, cursor)


@router.post("/demo/reset")
def reset(s: Admin) -> dict[str, bool]:
    """Restore seeded data for the in-memory demo."""
    require(s.ctx.settings.demo_mode, "NOT_FOUND", "Demo mode is disabled.", 404)
    require(
        s.ctx.settings.storage == "memory",
        "RESET_UNSUPPORTED",
        "Reset is available in memory mode; redeploy to reseed.",
        409,
    )

    def operation(state, user):
        seed(state, s.now, reset=True)
        audit(state, s.now, user.id, "demo.reset", "seed")
        return {"reset": True}

    return s.mutate(operation)
