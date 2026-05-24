#!/usr/bin/env python
"""
CLI management script.

Usage:
    python manage.py make-superuser <email>
    python manage.py revoke-superuser <email>
    python manage.py list-superusers
"""
import sys
from src import create_app
from src.models.main import Parent, db


app = create_app()


def make_superuser(email: str) -> None:
    with app.app_context():
        parent = Parent.query.filter_by(email=email.lower().strip()).first()
        if not parent:
            print(f"ERROR: No parent found with email '{email}'")
            sys.exit(1)
        parent.is_superuser = True
        db.session.commit()
        print(f"OK: {parent.name} ({parent.email}) is now a superuser.")


def revoke_superuser(email: str) -> None:
    with app.app_context():
        parent = Parent.query.filter_by(email=email.lower().strip()).first()
        if not parent:
            print(f"ERROR: No parent found with email '{email}'")
            sys.exit(1)
        parent.is_superuser = False
        db.session.commit()
        print(f"OK: Superuser revoked from {parent.name} ({parent.email}).")


def list_superusers() -> None:
    with app.app_context():
        superusers = Parent.query.filter_by(is_superuser=True).all()
        if not superusers:
            print("No superusers found.")
            return
        for p in superusers:
            print(f"  {p.name} <{p.email}>  (id={p.id})")


COMMANDS = {
    "make-superuser": (make_superuser, "<email>"),
    "revoke-superuser": (revoke_superuser, "<email>"),
    "list-superusers": (list_superusers, ""),
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage:")
        for cmd, (_, args) in COMMANDS.items():
            print(f"  python manage.py {cmd} {args}".rstrip())
        sys.exit(1)

    cmd = sys.argv[1]
    fn, _ = COMMANDS[cmd]

    if cmd in ("make-superuser", "revoke-superuser"):
        if len(sys.argv) < 3:
            print(f"ERROR: '{cmd}' requires an email argument.")
            sys.exit(1)
        fn(sys.argv[2])
    else:
        fn()
