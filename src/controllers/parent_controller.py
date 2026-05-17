from functools import wraps

from flask import Blueprint, jsonify, make_response, request, session

from src.models.main import (
    CoinTransaction,
    Family,
    Kid,
    Parent,
    TrustedDevice,
    db,
    generate_family_code,
)


parent_bp = Blueprint("parent", __name__, url_prefix="/api/parent")


def parent_login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("role") != "parent" or not session.get("parent_id"):
            return jsonify({"success": False, "message": "Parent login required."}), 401
        return func(*args, **kwargs)

    return wrapper


def _record_coin_transaction(
    kid: Kid,
    family_id: int,
    amount: int,
    kind: str,
    reason: str | None = None,
    ref_type: str | None = None,
    ref_id: int | None = None,
    parent_id: int | None = None,
) -> CoinTransaction:
    """Mutate kid.coin_balance by *amount* and append a CoinTransaction row.

    The caller is responsible for calling db.session.commit().
    Amount should be negative for debits (e.g. fines, purchases).
    """
    kid.coin_balance += amount
    tx = CoinTransaction(
        kid_id=kid.id,
        family_id=family_id,
        amount=amount,
        kind=kind,
        reason=reason,
        ref_type=ref_type,
        ref_id=ref_id,
        created_by_parent_id=parent_id,
    )
    db.session.add(tx)
    return tx


def _find_family_by_code(raw_code: str) -> Family | None:
    if not raw_code:
        return None
    hint = Family.hint_for(raw_code)
    possible = Family.query.filter_by(family_code_hint=hint, is_active=True).all()
    for family in possible:
        if family.verify_family_code(raw_code):
            return family
    return None


@parent_bp.post("/register")
def register_parent():
    payload = request.get_json(silent=True) or request.form
    family_name = (payload.get("family_name") or "").strip()
    parent_name = (payload.get("parent_name") or "").strip()
    email = (payload.get("email") or "").strip().lower()
    password = (payload.get("password") or "").strip()
    device_label = (payload.get("device_label") or "Parent Device").strip()

    if not family_name or not parent_name or not email or not password:
        return jsonify({"success": False, "message": "family_name, parent_name, email, and password are required."}), 400

    if len(password) < 8:
        return jsonify({"success": False, "message": "Password must be at least 8 characters."}), 400

    if Parent.query.filter_by(email=email).first():
        return jsonify({"success": False, "message": "Email already in use."}), 409

    plain_family_code = generate_family_code()
    family = Family(name=family_name)
    family.set_family_code(plain_family_code)

    parent = Parent(family=family, name=parent_name, email=email)
    parent.set_password(password)

    db.session.add(family)
    db.session.add(parent)
    db.session.flush()

    trusted_device, plain_device_token = TrustedDevice.create_for_family(
        family_id=family.id,
        parent_id=parent.id,
        device_label=device_label,
    )
    db.session.add(trusted_device)
    db.session.commit()

    session.clear()
    session["role"] = "parent"
    session["parent_id"] = parent.id
    session["family_id"] = family.id

    response = make_response(
        jsonify(
            {
                "success": True,
                "message": "Parent account created.",
                "family": {"id": family.id, "name": family.name, "family_code": plain_family_code},
                "parent": {"id": parent.id, "name": parent.name, "email": parent.email},
            }
        )
    )
    response.set_cookie(
        "family_device_token",
        plain_device_token,
        max_age=90 * 24 * 60 * 60,
        httponly=True,
        samesite="Lax",
    )
    return response, 201


@parent_bp.post("/login")
def login_parent():
    payload = request.get_json(silent=True) or request.form
    email = (payload.get("email") or "").strip().lower()
    password = (payload.get("password") or "").strip()
    device_label = (payload.get("device_label") or "Parent Device").strip()
    trust_device = str(payload.get("trust_device", "true")).lower() == "true"

    parent = Parent.query.filter_by(email=email).first()
    if not parent or not parent.verify_password(password):
        return jsonify({"success": False, "message": "Invalid email or password."}), 401

    parent.last_login_at = db.func.now()
    session.clear()
    session["role"] = "parent"
    session["parent_id"] = parent.id
    session["family_id"] = parent.family_id

    response = make_response(
        jsonify(
            {
                "success": True,
                "message": "Parent logged in.",
                "parent": {"id": parent.id, "name": parent.name, "email": parent.email},
                "family": {"id": parent.family.id, "name": parent.family.name},
            }
        )
    )

    if trust_device:
        trusted_device, plain_device_token = TrustedDevice.create_for_family(
            family_id=parent.family_id,
            parent_id=parent.id,
            device_label=device_label,
        )
        db.session.add(trusted_device)
        response.set_cookie(
            "family_device_token",
            plain_device_token,
            max_age=90 * 24 * 60 * 60,
            httponly=True,
            samesite="Lax",
        )

    db.session.commit()
    return response


@parent_bp.post("/kids")
@parent_login_required
def create_kid():
    payload = request.get_json(silent=True) or request.form
    display_name = (payload.get("display_name") or "").strip()
    pin = (payload.get("pin") or "").strip()

    if not display_name:
        return jsonify({"success": False, "message": "display_name is required."}), 400

    if not pin.isdigit() or len(pin) != 4:
        return jsonify({"success": False, "message": "pin must be exactly 4 digits."}), 400

    family_id = session["family_id"]
    kid = Kid(family_id=family_id, display_name=display_name)
    kid.set_pin(pin)

    db.session.add(kid)
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": "Kid created.",
            "kid": {"id": kid.id, "display_name": kid.display_name, "family_id": kid.family_id},
        }
    ), 201


@parent_bp.get("/kids")
@parent_login_required
def list_kids():
    family_id = session["family_id"]
    kids = Kid.query.filter_by(family_id=family_id, is_active=True).order_by(Kid.created_at.asc()).all()

    return jsonify(
        {
            "success": True,
            "kids": [
                {
                    "id": kid.id,
                    "display_name": kid.display_name,
                    "created_at": kid.created_at.isoformat(),
                }
                for kid in kids
            ],
        }
    )


@parent_bp.post("/logout")
def logout_parent():
    session.clear()
    return jsonify({"success": True, "message": "Logged out."})


@parent_bp.post("/family/rotate-code")
@parent_login_required
def rotate_family_code():
    family = Family.query.get(session["family_id"])
    if not family:
        return jsonify({"success": False, "message": "Family not found."}), 404

    new_code = generate_family_code()
    family.set_family_code(new_code)
    db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": "Family code rotated.",
            "family": {"id": family.id, "family_code": new_code},
        }
    )


@parent_bp.post("/family/revoke-device")
@parent_login_required
def revoke_device():
    payload = request.get_json(silent=True) or request.form
    token = (payload.get("token") or request.cookies.get("family_device_token") or "").strip()
    if not token:
        return jsonify({"success": False, "message": "Device token required."}), 400

    device = TrustedDevice.find_valid_by_token(token)
    if not device or device.family_id != session["family_id"]:
        return jsonify({"success": False, "message": "Device not found."}), 404

    device.revoked_at = db.func.now()
    db.session.commit()
    return jsonify({"success": True, "message": "Device revoked."})


# ---------------------------------------------------------------------------
# Coin Fines
# ---------------------------------------------------------------------------

@parent_bp.post("/kids/<int:kid_id>/fines")
@parent_login_required
def fine_kid(kid_id: int):
    """Deduct coins from a kid as a fine, with a required reason."""
    payload = request.get_json(silent=True) or {}
    amount_raw = payload.get("amount")
    reason = (payload.get("reason") or "").strip()

    if not reason:
        return jsonify({"success": False, "message": "A reason is required for a fine."}), 400

    try:
        amount = int(amount_raw)
    except (TypeError, ValueError):
        return jsonify({"success": False, "message": "amount must be a positive integer."}), 400

    if amount <= 0:
        return jsonify({"success": False, "message": "amount must be greater than zero."}), 400

    family_id = session["family_id"]
    parent_id = session["parent_id"]
    kid = Kid.query.get(kid_id)
    if not kid or kid.family_id != family_id:
        return jsonify({"success": False, "message": "Kid not found."}), 404

    tx = _record_coin_transaction(
        kid=kid,
        family_id=family_id,
        amount=-amount,
        kind="fine",
        reason=reason,
        parent_id=parent_id,
    )
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Fined {kid.display_name} {amount} coins.",
        "coin_balance": kid.coin_balance,
        "transaction_id": tx.id,
    })


# ---------------------------------------------------------------------------
# Transaction Log
# ---------------------------------------------------------------------------

@parent_bp.get("/transactions")
@parent_login_required
def list_transactions():
    """Return all coin transactions for the parent's family, newest first."""
    from datetime import datetime

    family_id = session["family_id"]
    query = CoinTransaction.query.filter_by(family_id=family_id)

    kid_id_raw = request.args.get("kid_id")
    if kid_id_raw:
        try:
            query = query.filter_by(kid_id=int(kid_id_raw))
        except ValueError:
            pass

    kind_filter = request.args.get("kind")
    if kind_filter:
        query = query.filter_by(kind=kind_filter)

    transactions = query.order_by(CoinTransaction.created_at.desc()).all()

    return jsonify({
        "success": True,
        "transactions": [
            {
                "id": tx.id,
                "kid_id": tx.kid_id,
                "kid_name": tx.kid.display_name if tx.kid else None,
                "amount": tx.amount,
                "kind": tx.kind,
                "reason": tx.reason,
                "ref_type": tx.ref_type,
                "ref_id": tx.ref_id,
                "created_by_parent_id": tx.created_by_parent_id,
                "created_at": tx.created_at.isoformat(),
            }
            for tx in transactions
        ],
    })
