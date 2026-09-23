"""Unit tests for incident workflow rules (transitions, milestones, timeline events)."""
import pytest

from utils import workflow
from utils.validation import ValidationError


def _incident(**overrides):
    base = {
        "status": "open", "priority": "medium", "assigned_to": None, "is_escalated": False,
        "escalation_reason": None, "title": "AC broken", "description": None, "category": "hvac",
        "building_id": 1, "floor_id": None, "seat_id": None,
    }
    return {**base, **overrides}


class TestTransitions:
    def test_engineer_can_start_and_resolve(self):
        workflow.validate_transition("engineer", "open", "in_progress")
        workflow.validate_transition("engineer", "in_progress", "resolved")

    def test_engineer_cannot_close(self):
        with pytest.raises(ValidationError):
            workflow.validate_transition("engineer", "resolved", "closed")

    def test_employee_can_only_confirm_or_reopen_resolution(self):
        assert set(workflow.allowed_transitions("employee", "resolved")) == {"closed", "open"}
        for status in ("open", "in_progress", "blocked", "closed"):
            assert workflow.allowed_transitions("employee", status) == ()

    def test_admin_can_reopen_closed(self):
        workflow.validate_transition("facility_admin", "closed", "open")

    def test_unknown_status_rejected(self):
        with pytest.raises(ValidationError):
            workflow.validate_transition("facility_admin", "open", "done")

    @pytest.mark.parametrize(
        "current,new,expected",
        [
            ("in_progress", "blocked", True),
            ("in_progress", "resolved", True),
            ("resolved", "open", True),
            ("closed", "open", True),
            ("open", "in_progress", False),
            ("resolved", "closed", False),
        ],
    )
    def test_requires_reason(self, current, new, expected):
        assert workflow.requires_reason(current, new) is expected

    def test_status_note_prefixes(self):
        assert workflow.status_note("in_progress", "blocked", "waiting on parts") == "Blocked: waiting on parts"
        assert workflow.status_note("in_progress", "resolved", "fixed") == "Resolution: fixed"
        assert workflow.status_note("resolved", "open", "still broken") == "Reopened: still broken"


class TestMilestones:
    def test_staff_action_acknowledges(self):
        assert workflow.milestone_updates(_incident(), {"priority": "high"}, "engineer") == {
            "acknowledged_at": "set_if_null"
        }

    def test_employee_action_does_not_acknowledge(self):
        assert workflow.milestone_updates(_incident(), {"priority": "high"}, "employee") == {}

    def test_assignment_and_start(self):
        updates = workflow.milestone_updates(_incident(), {"assigned_to": 5}, "facility_admin")
        assert updates["assigned_at"] == "set_if_null"
        updates = workflow.milestone_updates(_incident(), {"status": "in_progress"}, "engineer")
        assert updates["started_at"] == "set_if_null"

    def test_unassignment_does_not_stamp_assigned(self):
        updates = workflow.milestone_updates(_incident(assigned_to=5), {"assigned_to": None}, "facility_admin")
        assert "assigned_at" not in updates

    def test_close_without_resolve_backfills_resolved(self):
        updates = workflow.milestone_updates(_incident(), {"status": "closed"}, "facility_admin")
        assert updates["closed_at"] == "set"
        assert updates["resolved_at"] == "set_if_null"

    def test_reopen_clears_completion(self):
        updates = workflow.milestone_updates(_incident(status="resolved"), {"status": "open"}, "employee")
        assert updates == {"resolved_at": "clear", "closed_at": "clear"}


class TestChangeEvents:
    def test_status_assignment_and_priority_events(self):
        names = {5: "Sam Engineer", 6: "Alex Engineer"}
        events = workflow.change_events(
            _incident(assigned_to=5),
            {"status": "blocked", "assigned_to": 6, "priority": "high"},
            "waiting on parts",
            names.get,
        )
        assert [e["event_type"] for e in events] == ["status_changed", "assigned", "priority_changed"]
        assert events[0] == {
            "event_type": "status_changed", "from_value": "open", "to_value": "blocked", "details": "waiting on parts",
        }
        assert events[1]["from_value"] == "Sam Engineer" and events[1]["to_value"] == "Alex Engineer"

    def test_unchanged_values_produce_no_events(self):
        assert workflow.change_events(_incident(), {"priority": "medium", "status": "open"}, None, lambda _: None) == []

    def test_escalation_and_details(self):
        events = workflow.change_events(
            _incident(),
            {"is_escalated": True, "escalation_reason": "Affects whole floor", "title": "AC broken on 3F"},
            None,
            lambda _: None,
        )
        assert events[0]["event_type"] == "escalated" and events[0]["details"] == "Affects whole floor"
        assert events[1] == {"event_type": "details_updated", "from_value": None, "to_value": None, "details": "title"}
