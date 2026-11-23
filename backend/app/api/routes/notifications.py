from fastapi import APIRouter, Response

from ..deps import SignedIn
from ..schemas import ReadNotifications

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def listing(s: SignedIn) -> dict:
    items = sorted(
        (n for n in s.state.notifications.values() if n.user_id == s.user.id), key=lambda n: n.created_at, reverse=True
    )
    return {"items": items[:50], "unread_count": sum(not n.read for n in items)}


@router.get("/unread-count")
def count(s: SignedIn) -> dict[str, int]:
    return {"unread_count": sum(n.user_id == s.user.id and not n.read for n in s.state.notifications.values())}


@router.post("/read", status_code=204)
def mark(s: SignedIn, payload: ReadNotifications) -> Response:
    def operation(state, user):
        for entry in state.notifications.values():
            if entry.user_id == user.id and (payload.ids == "all" or entry.id in payload.ids):
                entry.read = True

    s.mutate(operation)
    return Response(status_code=204)
