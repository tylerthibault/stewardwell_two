from functools import wraps

from flask import Blueprint, jsonify, request, session

from src.models.main import Family, Kid, TrustedDevice, db


kid_bp = Blueprint("kid", __name__, url_prefix="/api/kid")


def kid_login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("role") != "kid" or not session.get("kid_id"):
            return jsonify({"success": False, "message": "Kid login required."}), 401
        return func(*args, **kwargs)

    return wrapper


def _find_family_by_code(raw_code: str) -> Family | None:
    if not raw_code:
        return None
    hint = Family.hint_for(raw_code)
    possible = Family.query.filter_by(family_code_hint=hint, is_active=True).all()
    for family in possible:
        if family.verify_family_code(raw_code):
            return family
    return None


def _family_from_device_cookie() -> Family | None:
    token = request.cookies.get("family_device_token", "").strip()
    if not token:
        return None

    device = TrustedDevice.find_valid_by_token(token)
    if not device:
        return None

    device.last_seen_at = db.func.now()
    db.session.commit()
    return device.family


@kid_bp.post("/login")
def login_kid():
    payload = request.get_json(silent=True) or request.form
    pin = (payload.get("pin") or "").strip()
    family_code = (payload.get("family_code") or "").strip()
    kid_id = payload.get("kid_id")

    if not pin:
        return jsonify({"success": False, "message": "pin is required."}), 400

    family = _family_from_device_cookie()
    if family is None:
        if not family_code:
            return jsonify({"success": False, "message": "family_code is required on untrusted devices."}), 400
        family = _find_family_by_code(family_code)

    if family is None:
        return jsonify({"success": False, "message": "Invalid family code or device token."}), 401

    query = Kid.query.filter_by(family_id=family.id, is_active=True)
    authenticated_kid = None

    if kid_id:
        kid = query.filter_by(id=kid_id).first()
        if kid and kid.verify_pin(pin):
            authenticated_kid = kid
    else:
        for candidate in query.order_by(Kid.created_at.asc()).all():
            if candidate.verify_pin(pin):
                authenticated_kid = candidate
                break

    if authenticated_kid is None:
        return jsonify({"success": False, "message": "Invalid kid PIN."}), 401

    session.clear()
    session["role"] = "kid"
    session["kid_id"] = authenticated_kid.id
    session["family_id"] = family.id

    return jsonify(
        {
            "success": True,
            "message": "Kid logged in.",
            "kid": {
                "id": authenticated_kid.id,
                "display_name": authenticated_kid.display_name,
                "family_id": authenticated_kid.family_id,
            },
        }
    )


@kid_bp.get("/family/kids")
def list_kids_for_family_entry():
    family = _family_from_device_cookie()
    payload = request.get_json(silent=True) or {}

    if family is None:
        family_code = (request.args.get("family_code") or payload.get("family_code") or "").strip()
        family = _find_family_by_code(family_code)

    if family is None:
        return jsonify({"success": False, "message": "Family not found."}), 404

    kids = Kid.query.filter_by(family_id=family.id, is_active=True).order_by(Kid.display_name.asc()).all()
    return jsonify(
        {
            "success": True,
            "family": {"id": family.id, "name": family.name},
            "kids": [{"id": kid.id, "display_name": kid.display_name} for kid in kids],
        }
    )


@kid_bp.get("/me")
@kid_login_required
def kid_me():
    kid = Kid.query.get(session["kid_id"])
    if not kid:
        session.clear()
        return jsonify({"success": False, "message": "Kid not found."}), 404

    return jsonify(
        {
            "success": True,
            "kid": {
                "id": kid.id,
                "display_name": kid.display_name,
                "family_id": kid.family_id,
            },
        }
    )


@kid_bp.post("/logout")
def logout_kid():
    session.clear()
    return jsonify({"success": True, "message": "Logged out."})
