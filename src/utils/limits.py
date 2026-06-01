"""
Tier-based feature limits and feature flags for Stewardwell.

Free tier limits — Pro (or active trial) removes all caps.

Feature tiers
─────────────
  "free"     — available to all users
  "pro"      — requires Pro plan (or active trial)
  "disabled" — unavailable to everyone (WIP / hidden)
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

# ── Feature flags ─────────────────────────────────────────────────────────────
# Maps feature key → minimum required tier: "free" | "pro" | "disabled"
FEATURES: dict[str, str] = {
    "chores":       "free",
    "store":        "free",
    "tasks":        "free",
    "schedule":     "pro",
    "challenges":   "pro",
    "history":      "pro",
    "activities":   "disabled",
}

# Human-readable display name for each feature (used in locked UI)
FEATURE_LABELS: dict[str, str] = {
    "chores":       "Chores",
    "store":        "Reward Store",
    "tasks":        "Tasks",
    "schedule":     "Schedule",
    "challenges":   "Challenges",
    "history":      "History",
    "activities":   "Activities",
}

# Human-readable label for flash messages (quantity limits)
_LABELS = {
    "kids": "kids",
    "chores": "chores",
    "store_items": "store items",
    "challenges": "challenges",
    "tasks": "tasks",
    "trusted_devices": "trusted devices",
    "co_parents": "co-parents",
}


# ── Quantity-limit helpers ─────────────────────────────────────────────────────

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


# ── Feature-flag helpers ───────────────────────────────────────────────────────

# Runtime dict — starts as a copy of the code defaults, then overridden from DB.
# Write to this dict (and DB) via save_feature_tier(); read via get_feature_tier().
_runtime_features: dict[str, str] = dict(FEATURES)


def get_feature_tier(feature_key: str) -> str:
    """Return the tier required for *feature_key* ('free', 'pro', or 'disabled')."""
    return _runtime_features.get(feature_key, "free")


def feature_can_access(family, feature_key: str) -> bool:
    """Return True if *family* can access *feature_key*."""
    tier = get_feature_tier(feature_key)
    if tier == "disabled":
        return False
    if tier == "pro":
        return bool(family and family.is_pro)
    return True  # "free" — always accessible


def load_features_from_db() -> None:
    """Overwrite _runtime_features with any rows stored in the DB.
    Call once at app startup (after db.create_all) and after every admin save.
    """
    try:
        from src.models.main import FeatureFlag
        rows = FeatureFlag.query.all()
        for row in rows:
            _runtime_features[row.key] = row.tier
    except Exception:
        pass  # DB not ready yet — fall back to defaults silently


def save_feature_tier(key: str, tier: str) -> None:
    """Persist a feature tier to DB and update the runtime dict immediately."""
    from src.models.main import FeatureFlag, db
    from datetime import datetime as _dt
    if tier not in ("free", "pro", "disabled"):
        raise ValueError(f"Invalid tier: {tier!r}")
    row = FeatureFlag.query.get(key)
    if row:
        row.tier = tier
        row.updated_at = _dt.utcnow()
    else:
        row = FeatureFlag(key=key, tier=tier)
        db.session.add(row)
    db.session.commit()
    _runtime_features[key] = tier
