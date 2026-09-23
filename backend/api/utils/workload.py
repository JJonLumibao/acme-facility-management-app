"""Engineer workload scoring and assignment ranking (pure functions, no database access)."""
from typing import Any, Dict, List, Optional

# Urgent (high/critical) tickets count double: they demand more attention than routine ones.
URGENT_WEIGHT = 2
# Load score at or above which an engineer is considered moderately / heavily loaded.
MODERATE_THRESHOLD = 3
HEAVY_THRESHOLD = 6


def load_score(active: int, urgent: int) -> int:
    """Weighted count of active tickets (urgent tickets already counted once in `active`)."""
    return active + urgent * (URGENT_WEIGHT - 1)


def load_level(score: int) -> str:
    """Bucket a load score into 'light', 'moderate' or 'heavy'."""
    if score >= HEAVY_THRESHOLD:
        return "heavy"
    if score >= MODERATE_THRESHOLD:
        return "moderate"
    return "light"


def annotate(engineer: Dict[str, Any], department: Optional[str] = None) -> Dict[str, Any]:
    """Add load score/level/percentage and department match flags to an engineer workload row."""
    score = load_score(engineer.get("active_count", 0), engineer.get("urgent_count", 0))
    return {
        **engineer,
        "load_score": score,
        "load_level": load_level(score),
        "load_percent": min(100, round(score / HEAVY_THRESHOLD * 100)),
        "department_match": bool(department) and engineer.get("department") == department,
    }


def rank_for_assignment(engineers: List[Dict[str, Any]], department: Optional[str]) -> List[Dict[str, Any]]:
    """Order engineers for assignment: available first, then same department, then lightest load.

    The best candidate (available, not heavily loaded, preferring the matching department) is
    flagged `recommended` so the UI can highlight it.
    """
    annotated = [annotate(engineer, department) for engineer in engineers]
    ranked = sorted(
        annotated,
        key=lambda e: (not e["is_available"], not e["department_match"], e["load_score"], e["full_name"] or ""),
    )
    recommended_found = False
    for engineer in ranked:
        is_candidate = engineer["is_available"] and engineer["load_level"] != "heavy"
        engineer["recommended"] = is_candidate and not recommended_found
        recommended_found = recommended_found or engineer["recommended"]
    return ranked
