"""Brevo transactional email helper.

Usage:
    from src.utils.email import send_email
    send_email(
        to_email="user@example.com",
        to_name="User Name",
        subject="Your subject",
        html_content="<p>Hello</p>",
    )
"""

from __future__ import annotations

import os

import requests


def send_email(
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
) -> bool:
    """Send a transactional email via Brevo.

    Returns True on success, False on failure.
    Logs to stderr on failure so the app never hard-crashes on email errors.
    """
    api_key = os.environ.get("BREVO_API_KEY", "")
    sender_name = os.environ.get("BREVO_SENDER_NAME", "Stewardwell")
    sender_email = os.environ.get("BREVO_SENDER_EMAIL", "")
    reply_to_email = os.environ.get("BREVO_REPLY_TO_EMAIL", "")

    if not api_key or not sender_email:
        import sys
        print(
            "[email] BREVO_API_KEY or BREVO_SENDER_EMAIL not configured — email not sent.",
            file=sys.stderr,
        )
        return False

    payload = {
        "sender": {"name": sender_name, "email": sender_email},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content,
    }
    if reply_to_email:
        payload["replyTo"] = {"email": reply_to_email}

    try:
        resp = requests.post(
            "https://api.brevo.com/v3/smtp/email",
            json=payload,
            headers={
                "api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=10,
        )
        if resp.status_code in (200, 201):
            return True
        import sys
        print(f"[email] Brevo error {resp.status_code}: {resp.text}", file=sys.stderr)
        return False
    except Exception as exc:
        import sys
        print(f"[email] Request failed: {exc}", file=sys.stderr)
        return False
