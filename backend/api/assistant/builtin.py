"""Built-in assistant: answers the core business questions without an external AI service.

Matches the question to a topic by keywords, runs the same role-scoped tool the AI would use, and phrases
the result in plain sentences.
"""
from typing import Any, Callable, Dict, List, Optional, Tuple

from assistant import tools

# (topic, tool, keywords). Checked by keyword hits; on a tie the earlier topic wins.
_TOPICS: List[Tuple[str, str, Tuple[str, ...]]] = [
    ("communication", "get_communication_stats",
     ("inform", "notif", "communicat", "kept up", "reply", "replies", "stale", "no update", "reopen")),
    ("workload", "get_engineer_workload",
     ("busy", "busiest", "workload", "overload", "available", "availability", "capacity", "engineer",
      "distribut", "free")),
    ("hotspots", "get_hotspots",
     ("hot", "hotspot", "where", "location", "building", "floor", "seat", "room", "recurring", "repeat",
      "again", "spot", "most issues", "most incidents")),
    ("response_times", "get_response_times",
     ("fast", "slow", "how long", "how quick", "quickly", "time to", "response time", "acknowledg",
      "turnaround", "speed", "resolve time", "resolution time")),
    ("attention", "get_attention_items",
     ("escalat", "blocked", "stuck", "attention", "urgent", "why", "waiting")),
    ("categories", "get_top_categories",
     ("categor", "common", "type of", "types of", "kind of", "kinds of", "frequent", "most reported", "issue type")),
    ("overview", "get_overview",
     ("open", "status", "how many", "count", "summary", "overview", "active", "plate", "my incidents",
      "my tickets", "going on", "resolved")),
]

SUGGESTIONS: Dict[str, List[str]] = {
    "facility_admin": [
        "Where do issues happen most?",
        "What's escalated or blocked, and why?",
        "Which engineers are overloaded?",
        "How fast are we resolving incidents?",
        "What are the most common issues?",
        "Are employees being kept informed?",
    ],
    "engineer": [
        "What's on my plate?",
        "What's blocked and why?",
        "How fast am I resolving tickets?",
        "What kinds of issues do I handle most?",
    ],
    "employee": [
        "What's the status of my incidents?",
        "Are any of my incidents blocked?",
        "How quickly are my issues being resolved?",
        "What kinds of issues have I reported?",
    ],
}


def suggestions_for(user: Dict[str, Any]) -> List[str]:
    return SUGGESTIONS.get(user["role"], SUGGESTIONS["employee"])


def match_topic(message: str) -> Optional[Tuple[str, str]]:
    """Return (topic, tool) for the best keyword match, or None if nothing matches."""
    text = message.lower()
    best: Optional[Tuple[str, str]] = None
    best_hits = 0
    for topic, tool_name, keywords in _TOPICS:
        hits = sum(1 for keyword in keywords if keyword in text)
        if hits > best_hits:
            best, best_hits = (topic, tool_name), hits
    return best


def format_hours(hours: Optional[float]) -> str:
    """Readable duration, e.g. 0.4 -> '24m', 5.25 -> '5h 15m', 50 -> '2d 2h'."""
    if hours is None:
        return "n/a"
    minutes = max(0, round(hours * 60))
    if minutes < 1:
        return "under a minute"
    days, rem = divmod(minutes, 1440)
    hrs, mins = divmod(rem, 60)
    if days:
        return f"{days}d {hrs}h" if hrs else f"{days}d"
    if hrs:
        return f"{hrs}h {mins}m" if mins else f"{hrs}h"
    return f"{mins}m"


def _plural(count: int, word: str) -> str:
    return f"{count} {word}{'' if count == 1 else 's'}"


def _scope(user: Dict[str, Any]) -> str:
    """Whose incidents the numbers cover, e.g. 'across all facilities'."""
    return {
        "facility_admin": "across all facilities",
        "engineer": "for incidents assigned to you",
        "employee": "for incidents you reported",
    }.get(user["role"], "overall")


def _bullets(lines: List[str]) -> str:
    return "\n".join(f"• {line}" for line in lines)


def _reason(text: Optional[str]) -> str:
    """Reasons are free text; trim trailing punctuation so they read cleanly on their own line."""
    return (text or "No reason given").strip().rstrip(".")


# --- Renderers: tool data -> short heading + bullet points ---------------------------------------------
# The chat panel preserves line breaks, so answers use a one-line summary followed by one item per line.

def _render_overview(data: Dict[str, Any], user: Dict[str, Any]) -> str:
    counts, by_status = data["counts"], data["by_status"]
    if not counts.get("total"):
        return "There are no incidents yet."
    lines = [
        f"{by_status.get('open', 0)} open · {by_status.get('in_progress', 0)} in progress · "
        f"{by_status.get('blocked', 0)} blocked"
    ]
    if user["role"] == tools.ADMIN and counts["unassigned"]:
        lines.append(f"{counts['unassigned']} waiting for an engineer")
    if counts["escalated"]:
        lines.append(f"{counts['escalated']} escalated")
    if by_status.get("resolved"):
        lines.append(f"{by_status['resolved']} resolved, awaiting confirmation")
    lines.append(f"{counts['resolved_7d']} resolved in the last 7 days")
    active = _plural(counts["active"], "active incident")
    heading = {
        "facility_admin": f"{active} across all facilities:",
        "engineer": f"{active} assigned to you:",
    }.get(user["role"], f"You have {active}:")
    return f"{heading}\n\n{_bullets(lines)}"


def _render_hotspots(data: Dict[str, Any], user: Dict[str, Any]) -> str:
    if not data["buildings"]:
        return "No incidents have been reported against a location yet."
    sections = []
    if data["seats"]:
        seat = data["seats"][0]
        sections.append(
            f"Busiest spot: {seat['label']} ({seat['parent']}) with {_plural(seat['total'], 'incident')}, "
            f"{seat['active']} still active."
        )
    building = data["buildings"][0]
    top = [f"Top building: {building['label']} ({building['total']})"]
    if data["floors"]:
        floor = data["floors"][0]
        top.append(f"Top floor: {floor['label']}, {floor['parent']} ({floor['total']})")
    sections.append(_bullets(top))
    if data["recurring"]:
        repeats = [f"{row['category']} at {row['location']} ({row['count']}×)" for row in data["recurring"][:3]]
        sections.append("Recurring problems:\n" + _bullets(repeats))
    return "\n\n".join(sections)


def _render_response_times(data: Dict[str, Any], user: Dict[str, Any]) -> str:
    times = data["hours_from_report"]
    if not times["acknowledge"]["count"]:
        return "There isn't enough history yet to measure response times."
    labels = {"acknowledge": "Acknowledged", "assign": "Assigned", "start": "Work started", "resolve": "Resolved"}
    lines = [f"{labels[key]}: {format_hours(stat['median_hours'])}" for key, stat in times.items() if stat["count"]]
    resolved = times["resolve"]["count"]
    footer = (
        f"Average time to resolve: {format_hours(times['resolve']['avg_hours'])} "
        f"(based on {_plural(resolved, 'resolved incident')})."
    ) if resolved else "No incidents have been resolved yet."
    return f"Typical time from report (median) {_scope(user)}:\n\n{_bullets(lines)}\n\n{footer}"


def _render_attention(data: Dict[str, Any], user: Dict[str, Any]) -> str:
    items = data["items"]
    if not items:
        return "Nothing is escalated or blocked right now."
    entries = []
    for item in items[:5]:
        entry = f"• #{item['id']} {item['title']}"
        if item["escalated"]:
            entry += f"\n   Escalated: {_reason(item['escalation_reason'])}"
        if item["status"] == "blocked":
            entry += f"\n   Blocked: {_reason(item['blocked_reason'])}"
        entries.append(entry)
    verb = "needs" if len(items) == 1 else "need"
    more = f"\n\n…and {len(items) - 5} more." if len(items) > 5 else ""
    return f"{_plural(len(items), 'incident')} {verb} attention:\n\n" + "\n\n".join(entries) + more


def _render_categories(data: Dict[str, Any], user: Dict[str, Any]) -> str:
    rows = data["categories"]
    if not rows:
        return "No incidents have been reported yet."
    lines = [f"{row['category']}: {row['total']} total, {row['active']} active ({row['department']})" for row in rows[:5]]
    return f"Most common issues {_scope(user)}:\n\n{_bullets(lines)}"


def _render_workload(data: Dict[str, Any], user: Dict[str, Any]) -> str:
    engineers = data["engineers"]
    if not engineers:
        return "There are no engineers yet."
    available = [e for e in engineers if e["available"]]
    heavy = [e for e in available if e["load_level"] == "heavy"]
    sections = [f"{len(available)} of {len(engineers)} engineers are available."]
    if heavy:
        sections.append(
            "Heavily loaded:\n"
            + _bullets([f"{e['name']}: {e['active']} active, {e['urgent']} urgent" for e in heavy])
            + "\nConsider reassigning some of their tickets within the same department."
        )
    else:
        sections.append("Nobody is heavily loaded.")
    lightest = sorted(available, key=lambda e: e["active"])[:3]
    if lightest:
        sections.append(
            "Most capacity:\n" + _bullets([f"{e['name']} ({e['department']}): {e['active']} active" for e in lightest])
        )
    return "\n\n".join(sections)


def _render_communication(data: Dict[str, Any], user: Dict[str, Any]) -> str:
    if not data["total"]:
        return "There are no incidents yet."
    explained = data["finished_with_update_rate"] if data["finished_with_update_rate"] is not None else 0
    lines = [
        f"{data['staff_update_rate']}% of tickets have an update from staff",
        f"First staff reply after {format_hours(data['avg_first_response_hours'])} on average",
        f"{explained}% of resolved tickets include an explanation",
        f"{_plural(data['stale_active'], 'active ticket')} with no update in {data['stale_after_hours']}h",
        f"{_plural(data['reopened'], 'ticket')} reopened",
    ]
    return f"How well employees are kept informed {_scope(user)}:\n\n{_bullets(lines)}"


_RENDERERS: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], str]] = {
    "overview": _render_overview,
    "hotspots": _render_hotspots,
    "response_times": _render_response_times,
    "attention": _render_attention,
    "categories": _render_categories,
    "workload": _render_workload,
    "communication": _render_communication,
}


def answer(message: str, user: Dict[str, Any]) -> Dict[str, Any]:
    """Answer a question from the matching tool; unknown or forbidden topics get a helpful list instead."""
    suggestions = suggestions_for(user)
    matched = match_topic(message)
    if matched is None:
        return {
            "answer": "I can answer questions about your incidents and facilities. Try one of these:",
            "links": [],
            "suggestions": suggestions,
        }

    topic, tool_name = matched
    if tools.is_admin_only(tool_name) and user["role"] != tools.ADMIN:
        return {
            "answer": f"{tools.ADMIN_ONLY_MESSAGE} Here's what I can help you with:",
            "links": [],
            "suggestions": suggestions,
        }

    data = tools.run_tool(tool_name, {}, user)
    link = tools.tool_link(tool_name)
    return {"answer": _RENDERERS[topic](data, user), "links": [link] if link else [], "suggestions": []}
