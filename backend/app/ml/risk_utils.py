"""Utility functions for the ML/risk engine."""
RISK_LEVELS = [
    ("VERY_LOW", 0, 20),
    ("LOW", 21, 40),
    ("MODERATE", 41, 60),
    ("HIGH", 61, 80),
    ("CRITICAL", 81, 100),
]

# Default configurable thresholds (admin can override)
DEFAULT_THRESHOLDS = {
    "VERY_LOW": {"lower": 0, "upper": 20},
    "LOW": {"lower": 21, "upper": 40},
    "MODERATE": {"lower": 41, "upper": 60},
    "HIGH": {"lower": 61, "upper": 80},
    "CRITICAL": {"lower": 81, "upper": 100},
}


def risk_level_for_score(score: float, thresholds: dict | None = None) -> str:
    """Map a 0-100 risk score to a named risk level using configurable thresholds.

    Thresholds may be either {'LEVEL': {'lower':..,'upper':..}} dicts or
    {'LEVEL': (lower, upper)} tuples.
    """
    t = thresholds or DEFAULT_THRESHOLDS
    for level, config in t.items():
        if isinstance(config, (tuple, list)):
            lower, upper = int(config[0]), int(config[1])
        else:
            lower = config.get("lower", 0)
            upper = config.get("upper", 100)
        if lower <= score <= upper:
            return level
    # Fallback by numeric membership
    for level, lo, hi in RISK_LEVELS:
        if lo <= score <= hi:
            return level
    return "CRITICAL" if score > 100 else "VERY_LOW"


def risk_color(level: str) -> str:
    palette = {
        "VERY_LOW": "#22c55e",  # green
        "LOW": "#eab308",       # yellow
        "MODERATE": "#f97316",  # orange
        "HIGH": "#ef4444",      # red
        "CRITICAL": "#a855f7",  # purple
    }
    return palette.get(level, "#64748b")


def recommended_action_for(level: str) -> str:
    actions = {
        "VERY_LOW": "No action required. Routine monitoring.",
        "LOW": "Continue routine monitoring. No immediate action.",
        "MODERATE": "Heightened monitoring recommended. Review vulnerable assets.",
        "HIGH": "Increased monitoring and preparedness. Alert local authorities.",
        "CRITICAL": "Immediate monitoring and preparedness. Prepare for possible evacuation.",
    }
    return actions.get(level, "Monitor situation.")
