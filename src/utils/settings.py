"""
App-wide runtime settings stored in the database.

At startup, load_app_settings() reads all AppSetting rows and writes them
into os.environ so they override deployment-level env vars (Coolify, .env, etc.).
save_app_setting() persists a key/value pair to both the DB and os.environ
immediately, so changes take effect without a redeploy.
"""
from __future__ import annotations

import os
from datetime import datetime


# ── Field definitions used by the admin UI ───────────────────────────────────

EMAIL_SETTING_DEFS: list[dict] = [
    {
        "group": "Brevo API",
        "fields": [
            {
                "key": "BREVO_API_KEY",
                "label": "API Key",
                "help": "Found in Brevo → SMTP & API → API Keys. Leave blank to keep the current value.",
                "placeholder": "xkeysib-…",
                "secret": True,
            },
        ],
    },
    {
        "group": "Sender Identity",
        "fields": [
            {
                "key": "BREVO_SENDER_EMAIL",
                "label": "Sender Email",
                "help": "Must be a verified sender in your Brevo account.",
                "placeholder": "hello@stewardwell.com",
                "secret": False,
            },
            {
                "key": "BREVO_SENDER_NAME",
                "label": "Sender Name",
                "help": "Display name shown to recipients.",
                "placeholder": "Stewardwell",
                "secret": False,
            },
        ],
    },
    {
        "group": "Reply-To (optional)",
        "fields": [
            {
                "key": "BREVO_REPLY_TO_EMAIL",
                "label": "Reply-To Email",
                "help": "If set, replies from users go here instead of the sender address.",
                "placeholder": "support@stewardwell.com",
                "secret": False,
            },
        ],
    },
]

PAYMENT_SETTING_DEFS: list[dict] = [
    {
        "group": "Application",
        "fields": [
            {
                "key": "APP_BASE_URL",
                "label": "App Base URL",
                "help": "Public root URL of your app (no trailing slash). Used in email links and Stripe redirect URLs.",
                "placeholder": "https://app.stewardwell.com",
                "secret": False,
            },
        ],
    },
    {
        "group": "Stripe — API Keys",
        "fields": [
            {
                "key": "STRIPE_SECRET_KEY",
                "label": "Secret Key",
                "help": "Starts with sk_live_… or sk_test_…  Leave blank to keep the current value.",
                "placeholder": "sk_live_…",
                "secret": True,
            },
            {
                "key": "STRIPE_PUBLISHABLE_KEY",
                "label": "Publishable Key",
                "help": "Starts with pk_live_… or pk_test_…  Safe to display in browser JS.",
                "placeholder": "pk_live_…",
                "secret": False,
            },
        ],
    },
    {
        "group": "Stripe — Products & Prices",
        "fields": [
            {
                "key": "STRIPE_PRICE_ID_MONTHLY",
                "label": "Monthly Price ID",
                "help": "Stripe Price ID for the monthly Pro subscription (price_…).",
                "placeholder": "price_…",
                "secret": False,
            },
            {
                "key": "STRIPE_PRICE_ID_ANNUAL",
                "label": "Annual Price ID",
                "help": "Stripe Price ID for the annual Pro subscription. Leave blank if not offered yet.",
                "placeholder": "price_…",
                "secret": False,
            },
        ],
    },
    {
        "group": "Stripe — Webhooks",
        "fields": [
            {
                "key": "STRIPE_WEBHOOK_SECRET",
                "label": "Webhook Signing Secret",
                "help": "whsec_…  Found in your Stripe Dashboard → Webhooks. Leave blank to keep current value.",
                "placeholder": "whsec_…",
                "secret": True,
            },
        ],
    },
    {
        "group": "Stripe — Other",
        "fields": [
            {
                "key": "STRIPE_DONATE_URL",
                "label": "Donation Payment Link URL",
                "help": "Stripe Payment Link URL displayed on the donations page.",
                "placeholder": "https://buy.stripe.com/…",
                "secret": False,
            },
        ],
    },
    {
        "group": "Donations — Buy Me a Coffee",
        "fields": [
            {
                "key": "BMAC_URL",
                "label": "Buy Me a Coffee Page URL",
                "help": "Your public BMAC page, e.g. https://buymeacoffee.com/yourname — shown as a donate button on the landing page.",
                "placeholder": "https://buymeacoffee.com/yourname",
                "secret": False,
            },
            {
                "key": "BMAC_WIDGET_ENABLED",
                "label": "Show Floating Widget",
                "help": "Set to 'true' to embed the BMAC floating button widget on every public page.",
                "placeholder": "true",
                "secret": False,
            },
        ],
    },
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_app_settings() -> None:
    """Load all AppSetting rows into os.environ.  Called once at app startup."""
    try:
        from src.models.main import AppSetting
        for row in AppSetting.query.all():
            if row.value is not None:
                os.environ[row.key] = row.value
    except Exception:
        # Table may not exist yet on first boot — that's fine.
        pass


def save_app_setting(key: str, value: str) -> None:
    """Persist key/value to DB and update os.environ immediately."""
    from src.models.main import AppSetting, db
    row = AppSetting.query.get(key)
    if row is None:
        row = AppSetting(key=key, value=value)
        db.session.add(row)
    else:
        row.value = value
        row.updated_at = datetime.utcnow()
    db.session.commit()
    if value:
        os.environ[key] = value
    else:
        os.environ.pop(key, None)
