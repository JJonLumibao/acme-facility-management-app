"""Unit tests for the assistant: topic matching, formatting, role checks and tool argument validation."""
import pytest

from assistant import builtin, tools

ADMIN = {"id": 1, "role": "facility_admin"}
EMPLOYEE = {"id": 2, "role": "employee"}


@pytest.mark.parametrize(
    "question,topic",
    [
        ("Where do issues happen most?", "hotspots"),
        ("What's the hottest spot for issues?", "hotspots"),
        ("Which engineers are overloaded?", "workload"),
        ("How fast are we resolving incidents?", "response_times"),
        ("What's escalated or blocked, and why?", "attention"),
        ("What are the most common issues?", "categories"),
        ("What's the status of my incidents?", "overview"),
        ("Are employees being kept informed?", "communication"),
    ],
)
def test_match_topic(question, topic):
    assert builtin.match_topic(question)[0] == topic


def test_every_suggestion_is_answerable():
    for suggestions in builtin.SUGGESTIONS.values():
        for question in suggestions:
            assert builtin.match_topic(question) is not None, question


def test_unknown_question_returns_suggestions():
    reply = builtin.answer("tell me a joke", EMPLOYEE)
    assert reply["suggestions"] == builtin.SUGGESTIONS["employee"]


def test_admin_only_topic_is_refused_for_employees():
    reply = builtin.answer("Which engineers are overloaded?", EMPLOYEE)
    assert tools.ADMIN_ONLY_MESSAGE in reply["answer"] and reply["suggestions"]


def test_format_hours():
    assert builtin.format_hours(0.4) == "24m"
    assert builtin.format_hours(5.25) == "5h 15m"
    assert builtin.format_hours(50) == "2d 2h"
    assert builtin.format_hours(None) == "n/a"


def test_tool_specs_hide_admin_tools_from_employees():
    admin_tools = {spec["name"] for spec in tools.tool_specs(ADMIN)}
    employee_tools = {spec["name"] for spec in tools.tool_specs(EMPLOYEE)}
    assert "get_hotspots" in admin_tools and "get_hotspots" not in employee_tools
    assert tools.run_tool("get_hotspots", {}, EMPLOYEE) == {"error": tools.ADMIN_ONLY_MESSAGE}


def test_run_tool_validates_arguments():
    assert "error" in tools.run_tool("find_incidents", {"status": "exploded"}, ADMIN)
    assert "error" in tools.run_tool("find_incidents", {"drop_table": "users"}, ADMIN)
    assert "error" in tools.run_tool("no_such_tool", {}, ADMIN)
