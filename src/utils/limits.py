"""
Tier-based feature limits for Stewardwell.

Free tier limits — Pro (or active trial) removes all caps.
"""
from __future__ import annotations

FREE_LIMITS = {
    "kids": 2,
    "chores": 5,
    "store_items": 5,
    "challenges": 3,
    "tasks": 5,
    "trusted_devices": 1,
    "co_parents": 1,          # only the account owner on free
    "chore_history_days": 7,
}

# Human-readable label for flash messages
_LABELS = {
    "kids": "kids",
    "chores": "chores",
    "store_items": "store items",
    "challenges": "challenges",
    "tasks": "tasks",
    "trusted_devices": "trusted devices",
    "co_parents": "co-parents",
}


def get_limit(family, resource: str) -> int | None:
    """Return the numeric limit for *resource* or None if unlimited."""
    if family.is_pro:
        return None
    return FREE_LIMITS.get(resource)


def can_add(family, resource: str, current_count: int) -> bool:
    """Return True if the family can add one more of *resource*."""
    limit = get_limit(family, resource)
    if limit is None:
        return True
    return current_count < limit


def limit_reached_message(resource: str) -> str:
    label = _LABELS.get(resource, resource)
    limit = FREE_LIMITS.get(resource, "?")
    return (
        f"Free plan is limited to {limit} {label}. "
        "Upgrade to Pro for unlimited access."
    )
