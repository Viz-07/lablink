from .constants import PRIORITY_WEIGHTS, PROJECT_WEIGHTS
from .enums import ProjectType
from .models import Factor, PriorityBreakdown


def priority_score(
    days: int | None,
    usage: int,
    project: ProjectType | None,
    grant: bool,
    waiting_hours: float,
    no_shows: int = 0,
) -> PriorityBreakdown:
    """Compute five bounded factors and a reproducible four-decimal score."""
    values = {
        "deadline": (
            0.2 if days is None else 1 - days / 30,
            "No deadline" if days is None else f"{days} days before deadline",
        ),
        "fairness": (1 - usage / 600 - min(no_shows, 3) * 0.1, f"{usage / 60:g} hours used in the last 7 days"),
        "project": (
            PROJECT_WEIGHTS[project] if project else 0.3,
            project.value.replace("_", " ").title() if project else "No project",
        ),
        "approval": (float(grant), "Access approved" if grant else "No prior approval"),
        "waiting": (waiting_hours / 72, f"Waiting {waiting_hours:.1f} hours"),
    }
    factors = {}
    for key, (raw, label) in values.items():
        value, weight = min(1.0, max(0.0, raw)), PRIORITY_WEIGHTS[key]
        factors[key] = Factor(label=label, value=value, weight=weight, contribution=value * weight)
    return PriorityBreakdown(score=round(sum(f.contribution for f in factors.values()), 4), factors=factors)
