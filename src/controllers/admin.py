"""
Admin blueprint — /admin/ routes.
Only accessible to Parent accounts with is_superuser=True.
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Blueprint, abort, flash, jsonify, redirect,
    render_template, request, session, url_for, current_app,
)

from src.models.main import Family, Kid, Parent, PromoCode, PromoRedemption, TrustedDevice, db

admin_bp = Blueprint("admin", __name__, url_prefix="/steward-ops")


# ── Auth guard ────────────────────────────────────────────────────────────────

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("role") != "parent":
            return redirect(url_for("admin.admin_login"))
        parent = Parent.query.get(session.get("parent_id"))
        if not parent or not parent.is_superuser:
            session.clear()
            return redirect(url_for("admin.admin_login"))
        return f(*args, **kwargs)
    return decorated


# ── Login ─────────────────────────────────────────────────────────────────────

@admin_bp.route("/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "GET":
        return render_template("admin/login.html")

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "").strip()

    parent = Parent.query.filter_by(email=email).first()
    if not parent or not parent.verify_password(password) or not parent.is_superuser:
        flash("Invalid admin credentials.", "error")
        return render_template("admin/login.html")

    session["role"] = "parent"
    session["parent_id"] = parent.id
    session["family_id"] = parent.family_id
    session["admin"] = True
    return redirect(url_for("admin.admin_dashboard"))


@admin_bp.get("/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin.admin_login"))


# ── Dashboard ─────────────────────────────────────────────────────────────────

@admin_bp.get("/")
@admin_required
def admin_dashboard():
    total_families = Family.query.filter_by(is_active=True).count()
    pro_families = Family.query.filter_by(plan="pro", is_active=True).count()
    trialing_families = Family.query.filter(
        Family.trial_ends_at > datetime.utcnow(), Family.is_active == True
    ).count()
    total_parents = Parent.query.count()
    now = datetime.utcnow()
    new_this_week = Family.query.filter(
        Family.created_at >= now - timedelta(days=7),
        Family.is_active == True,
    ).count()
    new_this_month = Family.query.filter(
        Family.created_at >= now - timedelta(days=30),
        Family.is_active == True,
    ).count()
    past_due = Family.query.filter_by(subscription_status="past_due").count()

    return render_template(
        "admin/dashboard.html",
        total_families=total_families,
        pro_families=pro_families,
        trialing_families=trialing_families,
        total_parents=total_parents,
        new_this_week=new_this_week,
        new_this_month=new_this_month,
        past_due=past_due,
    )


# ── Families ──────────────────────────────────────────────────────────────────

@admin_bp.get("/families")
@admin_required
def admin_families():
    q = request.args.get("q", "").strip()
    query = Family.query
    if q:
        query = query.filter(Family.name.ilike(f"%{q}%"))
    families = query.order_by(Family.created_at.desc()).limit(200).all()
    return render_template("admin/families.html", families=families, q=q)


@admin_bp.get("/families/<int:family_id>")
@admin_required
def admin_family_detail(family_id: int):
    family = Family.query.get_or_404(family_id)
    kids = Kid.query.filter_by(family_id=family_id, is_active=True).all()
    devices = TrustedDevice.query.filter_by(family_id=family_id).all()
    return render_template(
        "admin/family_detail.html",
        family=family,
        kids=kids,
        devices=devices,
    )


@admin_bp.post("/families/<int:family_id>/set-plan")
@admin_required
def admin_set_plan(family_id: int):
    family = Family.query.get_or_404(family_id)
    plan = request.form.get("plan", "free")
    if plan not in ("free", "pro"):
        flash("Invalid plan.", "error")
        return redirect(url_for("admin.admin_family_detail", family_id=family_id))
    family.plan = plan
    if plan == "pro":
        family.subscription_status = "active"
    else:
        family.subscription_status = None
    db.session.commit()
    flash(f"Plan updated to {plan}.", "success")
    return redirect(url_for("admin.admin_family_detail", family_id=family_id))


@admin_bp.post("/families/<int:family_id>/extend-trial")
@admin_required
def admin_extend_trial(family_id: int):
    family = Family.query.get_or_404(family_id)
    days = int(request.form.get("days", 7))
    base = family.trial_ends_at if (family.trial_ends_at and family.trial_ends_at > datetime.utcnow()) else datetime.utcnow()
    family.trial_ends_at = base + timedelta(days=days)
    db.session.commit()
    flash(f"Trial extended by {days} days.", "success")
    return redirect(url_for("admin.admin_family_detail", family_id=family_id))


@admin_bp.post("/families/<int:family_id>/deactivate")
@admin_required
def admin_deactivate_family(family_id: int):
    family = Family.query.get_or_404(family_id)
    family.is_active = False
    db.session.commit()
    flash(f"Family '{family.name}' deactivated.", "success")
    return redirect(url_for("admin.admin_families"))


@admin_bp.post("/families/<int:family_id>/impersonate")
@admin_required
def admin_impersonate(family_id: int):
    family = Family.query.get_or_404(family_id)
    first_parent = family.parents[0] if family.parents else None
    if not first_parent:
        flash("No parents in this family.", "error")
        return redirect(url_for("admin.admin_family_detail", family_id=family_id))
    session["impersonating_as_admin"] = session.get("parent_id")
    session["role"] = "parent"
    session["parent_id"] = first_parent.id
    session["family_id"] = family.id
    session.pop("admin", None)
    flash(f"Now impersonating {family.name}. Visit /admin/stop-impersonating to return.", "warning")
    return redirect(url_for("public.parent_dashboard"))


@admin_bp.get("/stop-impersonating")
def stop_impersonating():
    original_id = session.get("impersonating_as_admin")
    if not original_id:
        return redirect(url_for("admin.admin_dashboard"))
    original = Parent.query.get(original_id)
    if not original:
        session.clear()
        return redirect(url_for("admin.admin_login"))
    session["role"] = "parent"
    session["parent_id"] = original.id
    session["family_id"] = original.family_id
    session["admin"] = True
    session.pop("impersonating_as_admin", None)
    flash("Impersonation ended.", "success")
    return redirect(url_for("admin.admin_dashboard"))


# ── Parents ───────────────────────────────────────────────────────────────────

@admin_bp.get("/parents")
@admin_required
def admin_parents():
    q = request.args.get("q", "").strip()
    query = Parent.query
    if q:
        query = query.filter(
            (Parent.email.ilike(f"%{q}%")) | (Parent.name.ilike(f"%{q}%"))
        )
    parents = query.order_by(Parent.created_at.desc()).limit(200).all()
    return render_template("admin/parents.html", parents=parents, q=q)


@admin_bp.post("/parents/<int:parent_id>/deactivate")
@admin_required
def admin_deactivate_parent(parent_id: int):
    parent = Parent.query.get_or_404(parent_id)
    # We don't have a hard is_active flag on Parent yet — revoke by corrupting password
    # In a future iteration add is_active to Parent model
    flash("Parent deactivation not yet implemented — add is_active to Parent model.", "info")
    return redirect(url_for("admin.admin_parents"))


@admin_bp.post("/parents/<int:parent_id>/reset-password")
@admin_required
def admin_trigger_password_reset(parent_id: int):
    from src.models.main import PasswordResetToken
    from src.utils.email import send_email
    import os
    parent = Parent.query.get_or_404(parent_id)
    PasswordResetToken.query.filter_by(parent_id=parent.id).filter(
        PasswordResetToken.used_at.is_(None)
    ).delete()
    token_record, plain_token = PasswordResetToken.create_for_parent(parent.id)
    db.session.add(token_record)
    db.session.commit()
    base_url = os.environ.get("APP_BASE_URL", "https://app.stewardwell.com")
    reset_url = f"{base_url}/reset-password/{plain_token}"
    html = f"<p>Hi {parent.name},</p><p>An admin has triggered a password reset for your account.</p><p><a href='{reset_url}'>Reset my password</a></p>"
    send_email(to_email=parent.email, to_name=parent.name, subject="Stewardwell password reset", html_content=html)
    flash(f"Password reset email sent to {parent.email}.", "success")
    return redirect(url_for("admin.admin_parents"))


# ── Promo Codes ───────────────────────────────────────────────────────────────

@admin_bp.get("/promo-codes")
@admin_required
def admin_promo_codes():
    codes = PromoCode.query.order_by(PromoCode.created_at.desc()).all()
    return render_template("admin/promo_codes.html", codes=codes)


@admin_bp.post("/promo-codes/create")
@admin_required
def admin_promo_codes_create():
    code_str = (request.form.get("code") or "").strip().upper()
    if not code_str:
        flash("Code is required.", "danger")
        return redirect(url_for("admin.admin_promo_codes"))

    if PromoCode.query.filter_by(code=code_str).first():
        flash(f"Code '{code_str}' already exists.", "danger")
        return redirect(url_for("admin.admin_promo_codes"))

    expires_raw = request.form.get("expires_at") or ""
    expires_at = None
    if expires_raw:
        try:
            expires_at = datetime.fromisoformat(expires_raw)
        except ValueError:
            pass

    benefit_days = None
    if request.form.get("benefit_days"):
        try:
            benefit_days = int(request.form["benefit_days"])
        except ValueError:
            pass

    max_uses = None
    if request.form.get("max_uses"):
        try:
            max_uses = int(request.form["max_uses"])
        except ValueError:
            pass

    promo = PromoCode(
        code=code_str,
        description=request.form.get("description") or None,
        behavior=request.form.get("behavior", "discount"),
        target_tier=request.form.get("target_tier", "pro"),
        billing_cycle=request.form.get("billing_cycle", "any"),
        expires_at=expires_at,
        benefit_days=benefit_days,
        max_uses=max_uses,
        stripe_promotion_code_id=request.form.get("stripe_promotion_code_id") or None,
    )
    db.session.add(promo)
    db.session.commit()
    flash(f"Promo code '{code_str}' created.", "success")
    return redirect(url_for("admin.admin_promo_codes"))


@admin_bp.post("/promo-codes/<int:promo_id>/toggle")
@admin_required
def admin_promo_toggle(promo_id: int):
    promo = PromoCode.query.get_or_404(promo_id)
    promo.is_active = not promo.is_active
    db.session.commit()
    state = "activated" if promo.is_active else "deactivated"
    flash(f"Promo code '{promo.code}' {state}.", "success")
    return redirect(url_for("admin.admin_promo_codes"))


@admin_bp.post("/promo-codes/<int:promo_id>/delete")
@admin_required
def admin_promo_delete(promo_id: int):
    promo = PromoCode.query.get_or_404(promo_id)
    db.session.delete(promo)
    db.session.commit()
    flash(f"Promo code deleted.", "success")
    return redirect(url_for("admin.admin_promo_codes"))
