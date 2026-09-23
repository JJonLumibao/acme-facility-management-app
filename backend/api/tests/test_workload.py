"""Unit tests for engineer workload scoring, assignment ranking and the category catalog."""
from utils import workload
from utils.catalog import CATEGORIES, DEPARTMENT_KEYS, department_for_category


def _engineer(name, department, active=0, urgent=0, available=True):
    return {
        "full_name": name, "department": department, "active_count": active,
        "urgent_count": urgent, "is_available": available,
    }


def test_urgent_tickets_weigh_double():
    assert workload.load_score(active=3, urgent=2) == 5


def test_load_levels():
    assert workload.load_level(0) == "light"
    assert workload.load_level(workload.MODERATE_THRESHOLD) == "moderate"
    assert workload.load_level(workload.HEAVY_THRESHOLD) == "heavy"


def test_ranking_prefers_available_same_department_light_load():
    ranked = workload.rank_for_assignment(
        [
            _engineer("Busy HVAC", "facilities", active=6),
            _engineer("IT Person", "it_support"),
            _engineer("Free HVAC", "facilities", active=1),
            _engineer("Away HVAC", "facilities", available=False),
        ],
        "facilities",
    )
    assert [e["full_name"] for e in ranked] == ["Free HVAC", "Busy HVAC", "IT Person", "Away HVAC"]
    assert [e["full_name"] for e in ranked if e["recommended"]] == ["Free HVAC"]


def test_overloaded_department_recommends_someone_else():
    ranked = workload.rank_for_assignment(
        [_engineer("Busy HVAC", "facilities", active=4, urgent=2), _engineer("IT Person", "it_support")],
        "facilities",
    )
    assert ranked[0]["full_name"] == "Busy HVAC" and ranked[0]["load_level"] == "heavy"
    assert not ranked[0]["recommended"]
    assert ranked[1]["recommended"]


def test_load_percent_is_capped():
    assert workload.annotate(_engineer("x", None, active=20))["load_percent"] == 100


def test_every_category_maps_to_known_department():
    for category in CATEGORIES:
        assert category["department"] is None or category["department"] in DEPARTMENT_KEYS
    assert department_for_category("hvac") == "facilities"
    assert department_for_category("unknown") is None
