"""Static reference data: issue categories and the engineer departments that handle them.

Categories are a fixed list so reporting is quick for employees, dashboards can group consistently,
and each category maps to the department best suited to handle it (used for assignment suggestions).
"""
from typing import Any, Dict, List, Optional

DEPARTMENTS: List[Dict[str, str]] = [
    {"key": "facilities", "label": "Facilities Maintenance"},
    {"key": "electrical", "label": "Electrical"},
    {"key": "it_support", "label": "IT Support"},
    {"key": "av", "label": "Audio / Visual"},
    {"key": "security", "label": "Security & Access"},
]

CATEGORIES: List[Dict[str, Any]] = [
    {
        "key": "hvac", "label": "Heating & Cooling", "group": "facility", "department": "facilities",
        "description": "Too hot or cold, AC or heating not working, poor ventilation",
    },
    {
        "key": "plumbing", "label": "Plumbing & Restrooms", "group": "facility", "department": "facilities",
        "description": "Leaks, clogs, no water, restroom supplies",
    },
    {
        "key": "electrical", "label": "Power & Outlets", "group": "facility", "department": "electrical",
        "description": "Dead outlets, tripped breakers, power outages",
    },
    {
        "key": "lighting", "label": "Lighting", "group": "facility", "department": "electrical",
        "description": "Lights out, flickering, too dim",
    },
    {
        "key": "furniture", "label": "Furniture & Workspace", "group": "facility", "department": "facilities",
        "description": "Broken chairs or desks, sit-stand desks, lockers",
    },
    {
        "key": "cleaning", "label": "Cleaning & Hygiene", "group": "facility", "department": "facilities",
        "description": "Spills, trash, pest sightings, kitchen cleanliness",
    },
    {
        "key": "access_security", "label": "Access & Security", "group": "facility", "department": "security",
        "description": "Badge readers, door locks, cameras, alarms",
    },
    {
        "key": "network", "label": "Network & Wi-Fi", "group": "technology", "department": "it_support",
        "description": "No connectivity, slow Wi-Fi, dead network ports",
    },
    {
        "key": "hardware", "label": "Computer & Peripherals", "group": "technology", "department": "it_support",
        "description": "Monitors, docking stations, keyboards, mice",
    },
    {
        "key": "printer", "label": "Printers & Scanners", "group": "technology", "department": "it_support",
        "description": "Paper jams, toner, printer offline",
    },
    {
        "key": "av_equipment", "label": "Meeting Room A/V", "group": "technology", "department": "av",
        "description": "Displays, projectors, video conferencing, speakers",
    },
    {
        "key": "phone", "label": "Phones & Telephony", "group": "technology", "department": "it_support",
        "description": "Desk phones, headsets, voicemail",
    },
    {
        "key": "other", "label": "Other", "group": "other", "department": None,
        "description": "Anything that doesn't fit the categories above",
    },
]

CATEGORY_KEYS = {category["key"] for category in CATEGORIES}
DEPARTMENT_KEYS = {department["key"] for department in DEPARTMENTS}
_DEPARTMENT_BY_CATEGORY = {category["key"]: category["department"] for category in CATEGORIES}


def department_for_category(category: Optional[str]) -> Optional[str]:
    """Return the department responsible for a category (None for unknown/'other')."""
    return _DEPARTMENT_BY_CATEGORY.get(category or "")
