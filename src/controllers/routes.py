import os
import secrets
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

import math

from src.models.main import (
	Challenge,
	ChallengeSubmission,
	Chore,
	ChoreCategory,
	ChoreScheduleSlot,
	ChoreSubmission,
	CoinTransaction,
	Family,
	GuardianJoinRequest,
	Kid,
	Parent,
	PasswordResetToken,
	PendingDeviceRegistration,
	StoreItem,
	StoreRedemption,
	StoreRedemptionParticipant,
	StoreRedemptionVote,
	StoreSessionParticipant,
	StoreSessionTurn,
	StoreTimedSession,
	Task,
	TaskClaim,
	Donation,
	PromoCode,
	PromoRedemption,
	TrustedDevice,
	db,
	generate_family_code,
)
from src.utils.email import send_email
from src.utils.limits import can_add, limit_reached_message
from src.controllers.parent_controller import _record_coin_transaction


public_bp = Blueprint("public", __name__)


# ── PWA support ──────────────────────────────────────────────────────────────
# The service worker MUST be served from root scope to intercept all requests.
@public_bp.route("/sw.js")
def service_worker():
    return send_from_directory(
        current_app.static_folder, "sw.js",
        mimetype="application/javascript"
    )


@public_bp.route("/manifest.json")
def web_manifest():
    return send_from_directory(
        current_app.static_folder, "manifest.json",
        mimetype="application/manifest+json"
    )
# ─────────────────────────────────────────────────────────────────────────────


def parent_web_login_required(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		if session.get("role") != "parent" or not session.get("parent_id"):
			flash("Please log in as a parent to continue.", "error")
			return redirect(url_for("public.login"))
		return func(*args, **kwargs)

	return wrapper


def kid_web_login_required(func):
	@wraps(func)
	def wrapper(*args, **kwargs):
		if session.get("role") != "kid" or not session.get("kid_id"):
			flash("Please log in as a kid to continue.", "error")
			return redirect(url_for("public.kid_login"))
		return func(*args, **kwargs)

	return wrapper


def _load_parent_and_family():
	parent = Parent.query.get(session.get("parent_id"))
	family = Family.query.get(session.get("family_id"))
	return parent, family


def _load_kid_and_family():
	kid = Kid.query.get(session.get("kid_id"))
	family = Family.query.get(session.get("family_id"))
	return kid, family


def _split_coin_shares(total_coins: int, participant_kid_ids: list[int], primary_kid_id: int | None = None) -> dict[int, int]:
	if total_coins <= 0 or not participant_kid_ids:
		return {}

	unique_ids: list[int] = []
	for kid_id in participant_kid_ids:
		if kid_id not in unique_ids:
			unique_ids.append(kid_id)

	ordered_ids: list[int] = []
	if primary_kid_id in unique_ids:
		ordered_ids.append(primary_kid_id)
	for kid_id in unique_ids:
		if kid_id != primary_kid_id:
			ordered_ids.append(kid_id)

	participant_count = len(ordered_ids)
	if participant_count == 0:
		return {}

	base_share = total_coins // participant_count
	remainder = total_coins % participant_count
	shares: dict[int, int] = {}
	for idx, kid_id in enumerate(ordered_ids):
		shares[kid_id] = base_share + (1 if idx < remainder else 0)
	return shares


def _active_store_session_for_kid(kid_id: int):
	legacy_session = (
		StoreTimedSession.query.filter(
			StoreTimedSession.status == "active",
			(
				(StoreTimedSession.started_by_kid_id == kid_id)
				| (StoreTimedSession.participant_kid_id == kid_id)
			),
		)
		.order_by(StoreTimedSession.started_at.desc())
		.first()
	)
	if legacy_session:
		return legacy_session

	return (
		StoreTimedSession.query.join(
			StoreSessionParticipant,
			StoreSessionParticipant.timed_session_id == StoreTimedSession.id,
		)
		.filter(
			StoreTimedSession.status == "active",
			StoreSessionParticipant.kid_id == kid_id,
		)
		.order_by(StoreTimedSession.started_at.desc())
		.first()
	)


def _active_store_session_for_item(family_id: int, item_id: int):
	return (
		StoreTimedSession.query.filter_by(
			family_id=family_id,
			store_item_id=item_id,
			status="active",
		)
		.order_by(StoreTimedSession.started_at.desc())
		.first()
	)


def _active_store_sessions_by_item(family_id: int) -> dict[int, StoreTimedSession]:
	active_sessions = (
		StoreTimedSession.query.filter_by(family_id=family_id, status="active")
		.order_by(StoreTimedSession.started_at.desc())
		.all()
	)
	return {active_session.store_item_id: active_session for active_session in active_sessions}


def _family_parent_password_valid(family_id: int, password: str) -> bool:
	if not password:
		return False
	return any(parent.verify_password(password) for parent in Parent.query.filter_by(family_id=family_id).all())


def _close_store_session_turn(turn: StoreSessionTurn, ended_at: datetime | None = None) -> None:
	if turn.ended_at is not None:
		return

	turn.ended_at = ended_at or datetime.utcnow()
	turn.elapsed_seconds = max(0, int((turn.ended_at - turn.started_at).total_seconds()))


def _turn_minute_rate(turn: StoreSessionTurn) -> int:
	item = turn.timed_session.store_item if turn.timed_session else None
	participant = turn.participant
	if not item or item.session_rate_type != "per_minute" or not participant or not participant.charges_coins:
		return 0
	return item.session_coin_per_minute or 0


def _turn_start_cost(timed_session: StoreTimedSession, participant: StoreSessionParticipant) -> int:
	if not timed_session or not participant or not participant.charges_coins:
		return 0

	item = timed_session.store_item
	if not item:
		return 0

	if item.session_rate_type == "flat":
		return item.session_flat_cost or 0
	if item.session_rate_type == "per_minute":
		return item.session_coin_per_minute or 0
	return 0


def _turn_paid_minutes(turn: StoreSessionTurn) -> int:
	rate = _turn_minute_rate(turn)
	if rate <= 0:
		return 0
	return turn.coins_charged // rate


def _charge_next_turn_minute(turn: StoreSessionTurn) -> bool:
	rate = _turn_minute_rate(turn)
	if rate <= 0:
		return True

	kid = turn.participant.kid if turn.participant else None
	if not kid or kid.coin_balance < rate:
		return False

	kid.coin_balance -= rate
	turn.coins_charged += rate
	db.session.add(CoinTransaction(
		kid_id=kid.id,
		family_id=turn.family_id,
		amount=-rate,
		kind="timed_session",
		reason="Timed session charge (per minute)",
		ref_type="store_session_turn",
		ref_id=turn.id,
	))
	return True


def _charge_turn_start(turn: StoreSessionTurn) -> bool:
	cost = _turn_start_cost(turn.timed_session, turn.participant)
	if cost <= 0:
		return True

	kid = turn.participant.kid if turn.participant else None
	if not kid or kid.coin_balance < cost:
		return False

	kid.coin_balance -= cost
	turn.coins_charged += cost
	db.session.add(CoinTransaction(
		kid_id=kid.id,
		family_id=turn.family_id,
		amount=-cost,
		kind="timed_session",
		reason="Timed session charge (start cost)",
		ref_type="store_session_turn",
		ref_id=turn.id,
	))
	return True


def _sync_active_store_session_billing(timed_session: StoreTimedSession) -> bool:
	"""Charge newly-started minutes and close the turn once no next minute is affordable."""
	if not timed_session or timed_session.status != "active":
		return False

	turn = timed_session.current_turn
	if not turn or turn.ended_at is not None:
		return False

	rate = _turn_minute_rate(turn)
	if rate <= 0:
		return False

	now = datetime.utcnow()
	changed = False
	elapsed_seconds = max(0, int((now - turn.started_at).total_seconds()))
	minutes_needed = (elapsed_seconds // 60) + 1

	while _turn_paid_minutes(turn) < minutes_needed:
		if not _charge_next_turn_minute(turn):
			paid_seconds = _turn_paid_minutes(turn) * 60
			turn.ended_at = turn.started_at + timedelta(seconds=paid_seconds)
			if turn.ended_at > now:
				turn.ended_at = now
			turn.elapsed_seconds = max(0, int((turn.ended_at - turn.started_at).total_seconds()))
			return True
		changed = True

	return changed


def _participant_elapsed_seconds(timed_session: StoreTimedSession) -> dict[int, int]:
	elapsed_by_participant = {}
	for turn in timed_session.turns or []:
		elapsed_seconds = turn.elapsed_seconds
		if turn.ended_at is None:
			elapsed_seconds = turn.live_elapsed_seconds
		elapsed_by_participant[turn.participant_id] = elapsed_by_participant.get(turn.participant_id, 0) + elapsed_seconds
	return elapsed_by_participant


def _charge_shared_store_session(timed_session: StoreTimedSession) -> list[dict]:
	item = timed_session.store_item
	if not item:
		return []

	charge_summary = []
	total_charged = 0
	seconds_by_participant = _participant_elapsed_seconds(timed_session)
	participant_by_id = {participant.id: participant for participant in timed_session.participants or []}
	coins_by_participant = {}
	for turn in timed_session.turns or []:
		coins_by_participant[turn.participant_id] = coins_by_participant.get(turn.participant_id, 0) + (turn.coins_charged or 0)

	for participant_id, elapsed_seconds in seconds_by_participant.items():
		participant = participant_by_id.get(participant_id)
		if not participant:
			continue

		coins_due = coins_by_participant.get(participant_id, 0)

		total_charged += coins_due
		charge_summary.append(
			{
				"name": participant.display_name,
				"seconds": elapsed_seconds,
				"coins": coins_due,
				"charges_coins": participant.charges_coins,
			}
		)

	timed_session.total_coins_charged = total_charged
	return charge_summary


def _vote_summary_for_redemptions(redemptions: list[StoreRedemption]) -> dict[int, dict[str, int]]:
	summary = {}
	for redemption in redemptions:
		yes_votes = sum(1 for vote in redemption.votes if vote.vote == "yes")
		no_votes = sum(1 for vote in redemption.votes if vote.vote == "no")
		summary[redemption.id] = {"yes": yes_votes, "no": no_votes}
	return summary


def _redirect_to_next_or_default(next_path: str | None, default_endpoint: str, **default_kwargs):
	if next_path and next_path.startswith("/") and not next_path.startswith("//"):
		return redirect(next_path)
	return redirect(url_for(default_endpoint, **default_kwargs))


def _find_family_by_code(raw_code: str) -> "Family | None":
	if not raw_code:
		return None
	hint = Family.hint_for(raw_code)
	possible = Family.query.filter_by(family_code_hint=hint, is_active=True).all()
	for family in possible:
		if family.verify_family_code(raw_code):
			return family
	return None


def _build_schedule_preview(chores: list[Chore], days: int = 14) -> list[dict]:
	start_date = date.today()
	preview = []
	for offset in range(days):
		target_date = start_date + timedelta(days=offset)
		items = []
		for chore in chores:
			for assignment in chore.assignments_for_date(target_date):
				items.append(
					{
						"chore_name": chore.name,
						"kid_name": assignment.kid.display_name,
						"coin_reward": chore.coin_reward,
						"point_value": chore.point_value,
					}
				)

		preview.append(
			{
				"date": target_date,
				"label": target_date.strftime("%a %b %d"),
				"entries": items,
			}
		)

	return preview


def _parse_chore_categories(form_data, family_id: int) -> list[ChoreCategory] | None:
	selected_ids_raw = form_data.getlist("category_ids") if hasattr(form_data, "getlist") else []
	new_category_raw = (form_data.get("new_category_name", "") or "").strip()

	selected_categories = []
	seen_ids = set()

	for raw_id in selected_ids_raw:
		if not raw_id:
			continue
		try:
			category_id = int(raw_id)
		except ValueError:
			flash("Invalid category selection.", "error")
			return None

		if category_id in seen_ids:
			continue
		seen_ids.add(category_id)

		category = ChoreCategory.query.get(category_id)
		if not category or category.family_id != family_id:
			flash("Category not found for this family.", "error")
			return None

		selected_categories.append(category)

	if new_category_raw:
		candidate_names = [name.strip() for name in new_category_raw.split(",") if name.strip()]
		for candidate_name in candidate_names:
			existing = ChoreCategory.query.filter_by(family_id=family_id, name=candidate_name).first()
			if existing:
				if existing.id not in seen_ids:
					selected_categories.append(existing)
					seen_ids.add(existing.id)
				continue

			new_category = ChoreCategory(family_id=family_id, name=candidate_name)
			db.session.add(new_category)
			db.session.flush()
			selected_categories.append(new_category)
			seen_ids.add(new_category.id)

	return selected_categories


def _parse_chore_form_data(form_data, family_id: int) -> dict | None:
	name = form_data.get("name", "").strip()
	description = form_data.get("description", "").strip()
	schedule_kind = form_data.get("schedule_kind", "unscheduled").strip()
	anchor_date_raw = form_data.get("anchor_date", "").strip()
	coin_reward_raw = form_data.get("coin_reward", "0").strip()
	point_value_raw = form_data.get("point_value", "0").strip()
	max_concurrent_claims_raw = form_data.get("max_concurrent_claims", "1").strip()
	requires_photo_proof = (form_data.get("requires_photo_proof") or "").strip().lower() in {"on", "true", "1", "yes"}

	if not name:
		flash("Chore name is required.", "error")
		return None

	if schedule_kind not in {"unscheduled", "weekly", "alternating"}:
		flash("Please choose a valid schedule type.", "error")
		return None

	try:
		coin_reward = max(0, int(coin_reward_raw))
	except ValueError:
		flash("Coin reward must be a number.", "error")
		return None

	try:
		point_value = max(0, int(point_value_raw))
	except ValueError:
		flash("Point value must be a number.", "error")
		return None

	try:
		max_concurrent_claims = int(max_concurrent_claims_raw)
	except ValueError:
		flash("Simultaneous kid limit must be a number.", "error")
		return None

	if max_concurrent_claims < 1:
		flash("Simultaneous kid limit must be at least 1.", "error")
		return None

	try:
		anchor_date = date.fromisoformat(anchor_date_raw) if anchor_date_raw else date.today()
	except ValueError:
		flash("Start week date is invalid.", "error")
		return None

	kids = Kid.query.filter_by(family_id=family_id, is_active=True).all()
	valid_kid_ids = {kid.id for kid in kids}
	rotation_cycle_weeks = 2 if schedule_kind == "alternating" else 1
	slots_to_create = []

	if schedule_kind != "unscheduled":
		for weekday in range(7):
			primary_kid_raw = form_data.get(f"week0_day_{weekday}", "").strip()
			if primary_kid_raw:
				try:
					primary_kid_id = int(primary_kid_raw)
				except ValueError:
					flash("Invalid kid selected for schedule.", "error")
					return None

				if primary_kid_id not in valid_kid_ids:
					flash("Scheduled kid must belong to this family.", "error")
					return None

				slots_to_create.append({"kid_id": primary_kid_id, "weekday": weekday, "cycle_week_index": 0})

			if schedule_kind == "alternating":
				alternate_kid_raw = form_data.get(f"week1_day_{weekday}", "").strip()
				if alternate_kid_raw:
					try:
						alternate_kid_id = int(alternate_kid_raw)
					except ValueError:
						flash("Invalid alternate-week kid selected for schedule.", "error")
						return None

					if alternate_kid_id not in valid_kid_ids:
						flash("Alternate-week kid must belong to this family.", "error")
						return None

					slots_to_create.append({"kid_id": alternate_kid_id, "weekday": weekday, "cycle_week_index": 1})

		if not slots_to_create:
			flash("Add at least one scheduled kid slot for a scheduled chore.", "error")
			return None

	return {
		"name": name,
		"description": description or None,
		"requires_photo_proof": requires_photo_proof,
		"schedule_kind": schedule_kind,
		"anchor_date": anchor_date,
		"coin_reward": coin_reward,
		"point_value": point_value,
		"max_concurrent_claims": max_concurrent_claims,
		"rotation_cycle_weeks": rotation_cycle_weeks,
		"slots": slots_to_create,
	}


ALLOWED_CHORE_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


def _save_chore_photo(file_storage, family_id: int, kid_id: int, photo_type: str) -> str | None:
	if not file_storage or not file_storage.filename:
		return None

	filename = secure_filename(file_storage.filename)
	extension = os.path.splitext(filename)[1].lower()
	if extension not in ALLOWED_CHORE_IMAGE_EXTENSIONS:
		flash("Photos must be JPG, PNG, or WEBP.", "error")
		return None

	upload_root = os.path.join(current_app.instance_path, "uploads", "chore_photos")
	os.makedirs(upload_root, exist_ok=True)

	generated = f"family{family_id}_kid{kid_id}_{photo_type}_{secrets.token_hex(8)}{extension}"
	absolute_path = os.path.join(upload_root, generated)
	file_storage.save(absolute_path)

	return os.path.join("chore_photos", generated)


def _active_chore_submission_for_chore(chore: Chore) -> ChoreSubmission | None:
	return ChoreSubmission.query.filter(
		ChoreSubmission.chore_id == chore.id,
		ChoreSubmission.reset_version == chore.daily_reset_version,
		ChoreSubmission.status.in_(["claimed", "submitted"]),
	).order_by(ChoreSubmission.claimed_at.desc()).first()


def _submission_day_key(submission: ChoreSubmission) -> str:
	return submission.claimed_at.date().isoformat()


def _claimed_slots_for_today(chore: Chore) -> int:
	today_iso = date.today().isoformat()
	return ChoreSubmission.query.filter(
		ChoreSubmission.chore_id == chore.id,
		ChoreSubmission.reset_version == chore.daily_reset_version,
		db.func.date(ChoreSubmission.claimed_at) == today_iso,
		ChoreSubmission.status.in_(["claimed", "submitted", "approved"]),
	).count()


def _remaining_claim_slots_for_today(chore: Chore) -> int:
	return max(0, chore.max_concurrent_claims - _claimed_slots_for_today(chore))


def _recalculate_chore_split_rewards(chore: Chore, reset_version: int, claimed_day_iso: str) -> None:
	approved_submissions = (
		ChoreSubmission.query.filter(
			ChoreSubmission.chore_id == chore.id,
			ChoreSubmission.reset_version == reset_version,
			db.func.date(ChoreSubmission.claimed_at) == claimed_day_iso,
			ChoreSubmission.status == "approved",
		)
		.order_by(ChoreSubmission.claimed_at.asc(), ChoreSubmission.id.asc())
		.all()
	)

	if not approved_submissions:
		return

	count = len(approved_submissions)
	coin_base = chore.coin_reward // count
	coin_remainder = chore.coin_reward % count
	point_base = chore.point_value // count
	point_remainder = chore.point_value % count

	for index, approved_submission in enumerate(approved_submissions):
		target_coin_award = coin_base + (1 if index < coin_remainder else 0)
		target_point_award = point_base + (1 if index < point_remainder else 0)

		coin_delta = target_coin_award - (approved_submission.awarded_coin_amount or 0)
		point_delta = target_point_award - (approved_submission.awarded_point_amount or 0)

		if coin_delta:
			approved_submission.kid.coin_balance += coin_delta
			approved_submission.awarded_coin_amount = target_coin_award
			db.session.add(CoinTransaction(
				kid_id=approved_submission.kid.id,
				family_id=approved_submission.family_id,
				amount=coin_delta,
				kind="chore_reward",
				reason=f"Chore approved: {approved_submission.chore.name}",
				ref_type="chore_submission",
				ref_id=approved_submission.id,
				created_by_parent_id=approved_submission.resolved_by_parent_id,
			))

		if point_delta:
			approved_submission.family.family_points_balance += point_delta
			approved_submission.awarded_point_amount = target_point_award


def _apply_chore_award(submission: ChoreSubmission, target_coin_award: int, target_point_award: int) -> None:
	coin_delta = target_coin_award - (submission.awarded_coin_amount or 0)
	point_delta = target_point_award - (submission.awarded_point_amount or 0)

	if coin_delta:
		submission.kid.coin_balance += coin_delta
		db.session.add(CoinTransaction(
			kid_id=submission.kid.id,
			family_id=submission.family_id,
			amount=coin_delta,
			kind="chore_reward",
			reason=f"Chore approved: {submission.chore.name}",
			ref_type="chore_submission",
			ref_id=submission.id,
			created_by_parent_id=submission.resolved_by_parent_id,
		))

	if point_delta:
		submission.family.family_points_balance += point_delta

	submission.awarded_coin_amount = target_coin_award
	submission.awarded_point_amount = target_point_award


def _is_chore_locked_today(chore: Chore) -> bool:
	return _remaining_claim_slots_for_today(chore) <= 0


def _build_chore_slot_lookup(chore: Chore) -> dict[tuple[int, int], int]:
	return {(slot.cycle_week_index, slot.weekday): slot.kid_id for slot in chore.schedule_slots}


@public_bp.get("/")
def landing():
	donate_url = os.environ.get("STRIPE_DONATE_URL", "")
	return render_template("public/landing/index.html", donate_url=donate_url)


@public_bp.get("/terms")
def terms():
	return render_template("public/legal/terms.html")


@public_bp.get("/privacy")
def privacy():
	return render_template("public/legal/privacy.html")


@public_bp.route("/login", methods=["GET", "POST"])
def login():
	if request.method == "GET":
		return render_template("public/auth/login.html")

	email = request.form.get("email", "").strip().lower()
	password = request.form.get("password", "").strip()

	if not email or not password:
		flash("Please enter both email and password.", "error")
		return render_template("public/auth/login.html")

	parent = Parent.query.filter_by(email=email).first()
	if not parent or not parent.verify_password(password):
		flash("Invalid email or password.", "error")
		return render_template("public/auth/login.html")

	qr_token = session.get("qr_confirm_token")  # save before clear
	session.clear()
	session["role"] = "parent"
	session["parent_id"] = parent.id
	session["family_id"] = parent.family_id
	db.session.commit()

	# If parent was redirected here to confirm a QR device registration, go back
	if qr_token:
		flash("Welcome back! You are logged in.", "success")
		return redirect(url_for("public.device_qr_confirm_page", token=qr_token))

	response = redirect(url_for("public.parent_dashboard"))
	flash("Welcome back! You are logged in.", "success")
	return response


@public_bp.route("/register", methods=["GET", "POST"])
def register():
	if request.method == "GET":
		return render_template("public/auth/register.html")

	first_name = request.form.get("first_name", "").strip()
	last_name = request.form.get("last_name", "").strip()
	email = request.form.get("email", "").strip().lower()
	password = request.form.get("password", "").strip()
	confirm_password = request.form.get("confirm_password", "").strip()
	household_name = request.form.get("household_name", "").strip()

	if not all([first_name, last_name, email, password, confirm_password, household_name]):
		flash("Please complete all registration fields.", "error")
		return render_template("public/auth/register.html")

	if password != confirm_password:
		flash("Passwords do not match.", "error")
		return render_template("public/auth/register.html")

	if len(password) < 8:
		flash("Password must be at least 8 characters.", "error")
		return render_template("public/auth/register.html")

	if Parent.query.filter_by(email=email).first():
		flash("That email is already registered.", "error")
		return render_template("public/auth/register.html")

	family_code = generate_family_code()
	family = Family(name=household_name)
	family.set_family_code(family_code)
	# Start 14-day Pro trial for all new families
	family.trial_ends_at = datetime.utcnow() + timedelta(days=14)
	family.subscription_status = "trialing"

	parent_name = f"{first_name} {last_name}".strip()
	parent = Parent(family=family, name=parent_name, email=email)
	parent.set_password(password)

	# Generate email-verification token
	verify_token = parent.generate_verify_token()

	db.session.add(family)
	db.session.add(parent)
	db.session.commit()

	# Send verification email
	base_url = os.environ.get("APP_BASE_URL", request.host_url.rstrip("/"))
	verify_url = f"{base_url}/verify-email/{verify_token}"
	_send_verify_email(parent, verify_url)

	session.clear()
	session["role"] = "parent"
	session["parent_id"] = parent.id
	session["family_id"] = family.id

	response = redirect(url_for("public.parent_dashboard"))
	flash(f"Account created! Save your family code: {family_code}", "success")
	flash("A verification email has been sent. Please verify your email address within 24 hours.", "info")
	return response


# ---------------------------------------------------------------------------
# Forgot / Reset Password
# ---------------------------------------------------------------------------

@public_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
	if request.method == "GET":
		return render_template("public/auth/forgot_password.html")

	email = request.form.get("email", "").strip().lower()
	if not email:
		flash("Please enter your email address.", "error")
		return render_template("public/auth/forgot_password.html")

	# Always show the same success message to avoid email enumeration.
	parent = Parent.query.filter_by(email=email).first()
	if parent:
		# Invalidate any existing unused tokens for this parent.
		from datetime import datetime as _dt
		PasswordResetToken.query.filter_by(parent_id=parent.id).filter(
			PasswordResetToken.used_at.is_(None)
		).delete()

		token_record, plain_token = PasswordResetToken.create_for_parent(parent.id)
		db.session.add(token_record)
		db.session.commit()

		base_url = os.environ.get("APP_BASE_URL", request.host_url.rstrip("/"))
		reset_url = f"{base_url}/reset-password/{plain_token}"

		html = f"""
		<p>Hi {parent.name},</p>
		<p>We received a request to reset your Stewardwell password.
		Click the button below to choose a new password. This link expires in 1 hour.</p>
		<p style="text-align:center;margin:24px 0;">
			<a href="{reset_url}"
			   style="background:#4f8ef7;color:#fff;padding:12px 28px;border-radius:8px;
			          text-decoration:none;font-weight:700;font-size:15px;">
				Reset my password
			</a>
		</p>
		<p>Or copy this link into your browser:<br>
		<a href="{reset_url}">{reset_url}</a></p>
		<p style="color:#888;font-size:12px;">
			If you didn't request this, you can safely ignore this email.
		</p>
		"""
		send_email(
			to_email=parent.email,
			to_name=parent.name,
			subject="Reset your Stewardwell password",
			html_content=html,
		)

	flash("If that email is registered, you'll receive a reset link shortly.", "success")
	return redirect(url_for("public.forgot_password"))


@public_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token: str):
	token_record = PasswordResetToken.find_valid(token)
	if not token_record:
		flash("This reset link is invalid or has expired. Please request a new one.", "error")
		return redirect(url_for("public.forgot_password"))

	if request.method == "GET":
		return render_template("public/auth/reset_password.html", token=token)

	password = request.form.get("password", "").strip()
	confirm = request.form.get("confirm_password", "").strip()

	if not password or len(password) < 8:
		flash("Password must be at least 8 characters.", "error")
		return render_template("public/auth/reset_password.html", token=token)

	if password != confirm:
		flash("Passwords do not match.", "error")
		return render_template("public/auth/reset_password.html", token=token)

	parent = token_record.parent
	parent.set_password(password)
	token_record.used_at = datetime.utcnow()
	db.session.commit()

	flash("Password updated! Please log in with your new password.", "success")
	return redirect(url_for("public.login"))


@public_bp.get("/health")
def health():
	return jsonify({"success": True, "message": "ok"})


# ---------------------------------------------------------------------------
# Email-verification helpers
# ---------------------------------------------------------------------------

def _send_verify_email(parent: "Parent", verify_url: str) -> None:
	html = f"""
	<p>Hi {parent.name},</p>
	<p>Thanks for signing up for Stewardwell! Click the button below to verify
	your email address. This link expires in 24 hours.</p>
	<p style="text-align:center;margin:24px 0;">
		<a href="{verify_url}"
		   style="background:#4f8ef7;color:#fff;padding:12px 28px;border-radius:8px;
		          text-decoration:none;font-weight:700;font-size:15px;">
			Verify my email
		</a>
	</p>
	<p>Or copy this link:<br><a href="{verify_url}">{verify_url}</a></p>
	<p style="color:#888;font-size:12px;">If you didn\u2019t create a Stewardwell account, you can ignore this email.</p>
	"""
	send_email(
		to_email=parent.email,
		to_name=parent.name,
		subject="Verify your Stewardwell email address",
		html_content=html,
	)


@public_bp.route("/verify-email/<token>", methods=["GET"])
def verify_email(token: str):
	# Find parents whose verify token matches
	token_hash = __import__("hashlib").sha256(token.encode()).hexdigest()
	from datetime import datetime as _dt
	parent = Parent.query.filter_by(email_verify_token_hash=token_hash).first()
	if not parent:
		flash("Verification link is invalid or has already been used.", "error")
		return redirect(url_for("public.login"))
	if parent.email_verify_expires_at and _dt.utcnow() > parent.email_verify_expires_at:
		flash("Verification link has expired. Please request a new one.", "error")
		return redirect(url_for("public.resend_verification"))
	parent.email_verified = True
	parent.email_verify_token_hash = None
	parent.email_verify_expires_at = None
	db.session.commit()
	flash("Email verified! Welcome to Stewardwell.", "success")
	return redirect(url_for("public.login"))


@public_bp.route("/resend-verification", methods=["GET", "POST"])
def resend_verification():
	if request.method == "GET":
		return render_template("public/auth/resend_verification.html")
	email = request.form.get("email", "").strip().lower()
	parent = Parent.query.filter_by(email=email).first()
	if parent and not parent.email_verified:
		verify_token = parent.generate_verify_token()
		db.session.commit()
		base_url = os.environ.get("APP_BASE_URL", request.host_url.rstrip("/"))
		verify_url = f"{base_url}/verify-email/{verify_token}"
		_send_verify_email(parent, verify_url)
	flash("If your email is registered and unverified, a new verification link has been sent.", "success")
	return redirect(url_for("public.login"))


# ---------------------------------------------------------------------------
# Stripe billing
# ---------------------------------------------------------------------------

def _get_stripe():
	try:
		import stripe as _stripe
		_stripe.api_key = os.environ.get("STRIPE_SECRET_KEY", "")
		return _stripe
	except ImportError:
		return None


@public_bp.get("/billing/upgrade")
@parent_web_login_required
def billing_upgrade():
	stripe = _get_stripe()
	parent, family = _load_parent_and_family()
	if not stripe or not os.environ.get("STRIPE_SECRET_KEY"):
		flash("Billing is not yet configured. Please check back soon.", "info")
		return redirect(url_for("public.parent_settings"))

	price_id = os.environ.get("STRIPE_PRICE_ID_MONTHLY")
	base_url = os.environ.get("APP_BASE_URL", request.host_url.rstrip("/"))

	try:
		# Create or reuse Stripe customer
		if not family.stripe_customer_id:
			customer = stripe.Customer.create(
				email=parent.email,
				name=family.name,
				metadata={"family_id": family.id},
			)
			family.stripe_customer_id = customer.id
			db.session.commit()

		checkout = stripe.checkout.Session.create(
			customer=family.stripe_customer_id,
			payment_method_types=["card"],
			line_items=[{"price": price_id, "quantity": 1}],
			mode="subscription",
			allow_promotion_codes=True,
			success_url=f"{base_url}/billing/success?session_id={{CHECKOUT_SESSION_ID}}",
			cancel_url=f"{base_url}/billing/cancel",
			metadata={"family_id": family.id},
		)
		return redirect(checkout.url, code=303)
	except Exception as exc:
		current_app.logger.error("Stripe checkout error: %s", exc)
		flash("Could not start checkout. Please try again.", "error")
		return redirect(url_for("public.parent_settings"))


@public_bp.get("/billing/success")
@parent_web_login_required
def billing_success():
	session_id = request.args.get("session_id", "")
	stripe = _get_stripe()
	parent, family = _load_parent_and_family()
	if stripe and session_id:
		try:
			checkout_session = stripe.checkout.Session.retrieve(session_id)
			sub = stripe.Subscription.retrieve(checkout_session.subscription)
			family.plan = "pro"
			family.stripe_subscription_id = sub.id
			family.subscription_status = sub.status
			db.session.commit()
		except Exception as exc:
			current_app.logger.error("Stripe success handler error: %s", exc)
	flash("You're now on Stewardwell Pro! Enjoy unlimited access.", "success")
	return redirect(url_for("public.parent_dashboard"))


@public_bp.get("/billing/cancel")
@parent_web_login_required
def billing_cancel():
	flash("Upgrade cancelled. You can upgrade anytime from Settings.", "info")
	return redirect(url_for("public.parent_settings"))


@public_bp.post("/billing/apply-promo")
@parent_web_login_required
def billing_apply_promo():
	"""Apply a `grant_trial` promo code to extend the family's trial."""
	parent, family = _load_parent_and_family()
	code_str = (request.form.get("promo_code") or "").strip().upper()
	if not code_str:
		flash("Please enter a promo code.", "danger")
		return redirect(url_for("public.parent_settings"))

	promo = PromoCode.query.filter_by(code=code_str).first()

	# Validate
	if not promo:
		flash("Promo code not found.", "danger")
		return redirect(url_for("public.parent_settings"))
	if not promo.is_usable:
		flash("That promo code is no longer valid.", "danger")
		return redirect(url_for("public.parent_settings"))
	if promo.behavior != "grant_trial":
		flash("That code must be applied at checkout.", "info")
		return redirect(url_for("public.parent_settings"))

	# Check not already redeemed by this family
	already = PromoRedemption.query.filter_by(
		promo_code_id=promo.id, family_id=family.id
	).first()
	if already:
		flash("Your family has already redeemed that code.", "warning")
		return redirect(url_for("public.parent_settings"))

	# Extend trial
	benefit = promo.benefit_days or 30
	from datetime import datetime, timedelta
	before = family.trial_ends_at or datetime.utcnow()
	family.trial_ends_at = max(before, datetime.utcnow()) + timedelta(days=benefit)
	promo.record_use(family.id)
	db.session.commit()
	flash(f"🎉 Promo applied! Your trial has been extended by {benefit} days.", "success")
	return redirect(url_for("public.parent_settings"))


@public_bp.post("/billing/portal")
@parent_web_login_required
def billing_portal():
	stripe = _get_stripe()
	parent, family = _load_parent_and_family()
	base_url = os.environ.get("APP_BASE_URL", request.host_url.rstrip("/"))
	if not stripe or not family.stripe_customer_id:
		flash("No billing account found.", "error")
		return redirect(url_for("public.parent_settings"))
	try:
		portal = stripe.billing_portal.Session.create(
			customer=family.stripe_customer_id,
			return_url=f"{base_url}/parent/settings",
		)
		return redirect(portal.url, code=303)
	except Exception as exc:
		current_app.logger.error("Stripe portal error: %s", exc)
		flash("Could not open billing portal. Please try again.", "error")
		return redirect(url_for("public.parent_settings"))


@public_bp.post("/webhooks/stripe")
def stripe_webhook():
	stripe = _get_stripe()
	if not stripe:
		return jsonify({"error": "stripe not configured"}), 500

	payload = request.get_data(as_text=True)
	sig_header = request.headers.get("Stripe-Signature", "")
	webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "")

	try:
		event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
	except (ValueError, stripe.error.SignatureVerificationError) as exc:
		current_app.logger.warning("Stripe webhook bad signature: %s", exc)
		return jsonify({"error": "invalid signature"}), 400

	obj = event["data"]["object"]
	family_id = None

	# Try to resolve family from metadata or subscription
	if event["type"] == "checkout.session.completed":
		family_id = obj.get("metadata", {}).get("family_id")
		if family_id:
			family = Family.query.get(int(family_id))
			if family:
				sub = stripe.Subscription.retrieve(obj["subscription"])
				family.plan = "pro"
				family.stripe_subscription_id = sub.id
				family.subscription_status = sub.status
				db.session.commit()

	elif event["type"] == "invoice.payment_succeeded":
		sub_id = obj.get("subscription")
		if sub_id:
			family = Family.query.filter_by(stripe_subscription_id=sub_id).first()
			if family:
				family.subscription_status = "active"
				db.session.commit()

	elif event["type"] == "invoice.payment_failed":
		sub_id = obj.get("subscription")
		if sub_id:
			family = Family.query.filter_by(stripe_subscription_id=sub_id).first()
			if family:
				family.subscription_status = "past_due"
				db.session.commit()
				# Send dunning email to all parents
				_send_payment_failed_email(family)

	elif event["type"] == "payment_intent.succeeded":
		# Log one-time donation from Stripe Payment Link
		pi_id = obj.get("id")
		if pi_id and not Donation.query.filter_by(stripe_payment_intent_id=pi_id).first():
			billing = obj.get("charges", {}).get("data", [{}])
			charge = billing[0] if billing else {}
			billing_details = charge.get("billing_details") or obj.get("payment_method_options", {})
			donor_email = (charge.get("billing_details") or {}).get("email") or obj.get("receipt_email")
			donor_name  = (charge.get("billing_details") or {}).get("name")
			donation = Donation(
				stripe_payment_intent_id=pi_id,
				amount_cents=obj.get("amount_received", obj.get("amount", 0)),
				currency=obj.get("currency", "usd"),
				donor_email=donor_email,
				donor_name=donor_name,
			)
			db.session.add(donation)
			db.session.commit()
			current_app.logger.info("Donation logged: %s %s", pi_id, donation.amount_display)

	elif event["type"] == "customer.subscription.deleted":
		sub_id = obj.get("id")
		if sub_id:
			family = Family.query.filter_by(stripe_subscription_id=sub_id).first()
			if family:
				family.plan = "free"
				family.subscription_status = "canceled"
				family.stripe_subscription_id = None
				db.session.commit()

	return jsonify({"received": True}), 200


def _send_payment_failed_email(family: "Family") -> None:
	base_url = os.environ.get("APP_BASE_URL", "https://app.stewardwell.com")
	for parent in family.parents:
		html = f"""
		<p>Hi {parent.name},</p>
		<p>We were unable to process your Stewardwell Pro payment. Your account has been
		flagged as <strong>past due</strong>. Please update your payment method to keep your Pro access.</p>
		<p style="text-align:center;margin:24px 0;">
			<a href="{base_url}/billing/portal"
			   style="background:#e53e3e;color:#fff;padding:12px 28px;border-radius:8px;
			          text-decoration:none;font-weight:700;font-size:15px;">
				Update Payment Method
			</a>
		</p>
		<p style="color:#888;font-size:12px;">If you have questions, reply to this email.</p>
		"""
		send_email(
			to_email=parent.email,
			to_name=parent.name,
			subject="Action required: Stewardwell payment failed",
			html_content=html,
		)


def _run_daily_chore_reset(family: "Family") -> None:
	"""Lazy daily reset: bumps daily_reset_version on all active scheduled chores
	and archives prior-day approved submissions. Runs at most once per family per
	calendar day (checked via family.last_reset_date)."""
	today = date.today()
	if family.last_reset_date == today:
		return  # already ran today

	scheduled_chores = Chore.query.filter(
		Chore.family_id == family.id,
		Chore.schedule_kind != "unscheduled",
		Chore.is_active == True,
	).all()

	for chore in scheduled_chores:
		chore.daily_reset_version += 1

	# Archive approved submissions from before today for all chores in this family
	if family.last_reset_date is not None:
		ChoreSubmission.query.filter(
			ChoreSubmission.family_id == family.id,
			ChoreSubmission.status == "approved",
			ChoreSubmission.resolved_at < datetime.combine(today, datetime.min.time()),
		).update({"status": "archived"}, synchronize_session=False)

	family.last_reset_date = today
	db.session.commit()


@public_bp.get("/parent/dashboard")
@parent_web_login_required
def parent_dashboard():
	parent, family = _load_parent_and_family()

	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	_run_daily_chore_reset(family)

	kids = Kid.query.filter_by(family_id=family.id, is_active=True).order_by(Kid.created_at.asc()).all()
	pending_chore_submissions = (
		ChoreSubmission.query.filter_by(family_id=family.id, status="submitted")
		.order_by(ChoreSubmission.submitted_at.desc())
		.limit(8)
		.all()
	)
	pending_store_requests = (
		StoreRedemption.query.join(StoreItem, StoreRedemption.store_item_id == StoreItem.id)
		.filter(
			StoreRedemption.family_id == family.id,
			StoreRedemption.status == "pending",
			StoreItem.item_scope.in_(["kid", "family"]),
		)
		.order_by(StoreRedemption.requested_at.desc())
		.limit(8)
		.all()
	)
	pending_approvals_count = len(pending_chore_submissions) + ChallengeSubmission.query.filter_by(
		family_id=family.id,
		status="submitted",
	).count()
	is_new_family = (
		Chore.query.filter_by(family_id=family.id).count() == 0
		and StoreItem.query.filter_by(family_id=family.id).count() == 0
		and Challenge.query.filter_by(family_id=family.id).count() == 0
	)

	return render_template(
		"private/parents/dashboard.html",
		parent=parent,
		family=family,
		kids=kids,
		pending_approvals_count=pending_approvals_count,
		pending_chore_submissions=pending_chore_submissions,
		pending_store_requests=pending_store_requests,
		is_new_family=is_new_family,
	)


@public_bp.get("/parent/chores")
@parent_web_login_required
def parent_chores():
	parent, family = _load_parent_and_family()

	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	_run_daily_chore_reset(family)

	kids = Kid.query.filter_by(family_id=family.id, is_active=True).order_by(Kid.display_name.asc()).all()
	chores = Chore.query.filter_by(family_id=family.id).order_by(Chore.sort_order.asc(), Chore.created_at.asc()).all()
	pending_submissions = (
		ChoreSubmission.query.filter_by(family_id=family.id, status="submitted")
		.order_by(ChoreSubmission.submitted_at.desc())
		.limit(30)
		.all()
	)
	scheduled_chores = [chore for chore in chores if chore.is_active and chore.schedule_kind != "unscheduled"]
	return render_template(
		"private/parents/chores/index.html",
		parent=parent,
		family=family,
		kids=kids,
		chores=chores,
		categories=ChoreCategory.query.filter_by(family_id=family.id).order_by(ChoreCategory.name.asc()).all(),
		pending_submissions=pending_submissions,
		total_family_points=sum(chore.point_value for chore in chores if chore.is_active),
		schedule_preview=_build_schedule_preview(scheduled_chores),
		weekday_labels=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
	)


@public_bp.post("/parent/chores/reorder")
@parent_web_login_required
def parent_reorder_chores():
	parent, family = _load_parent_and_family()
	if not parent or not family:
		return jsonify({"error": "unauthorized"}), 401
	data = request.get_json(silent=True)
	if not data or "order" not in data:
		return jsonify({"error": "bad request"}), 400
	ordered_ids = data["order"]
	# Validate all IDs belong to this family
	chores_by_id = {c.id: c for c in Chore.query.filter_by(family_id=family.id).all()}
	for position, chore_id in enumerate(ordered_ids):
		chore = chores_by_id.get(chore_id)
		if chore:
			chore.sort_order = position
	db.session.commit()
	return jsonify({"success": True})


@public_bp.get("/parent/schedule")
@parent_web_login_required
def parent_schedule():
	parent, family = _load_parent_and_family()
	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	_run_daily_chore_reset(family)

	try:
		week_offset = int(request.args.get("week", 0))
		week_offset = max(-52, min(52, week_offset))
	except (ValueError, TypeError):
		week_offset = 0

	today = date.today()
	# Monday of the target week
	week_start = today - timedelta(days=today.weekday()) + timedelta(weeks=week_offset)
	week_end = week_start + timedelta(days=6)
	days = [week_start + timedelta(days=i) for i in range(7)]

	kids = Kid.query.filter_by(family_id=family.id, is_active=True).order_by(Kid.display_name.asc()).all()
	all_chores = Chore.query.filter_by(family_id=family.id, is_active=True).all()
	scheduled_chores = [c for c in all_chores if c.schedule_kind != "unscheduled"]
	unscheduled_count = len(all_chores) - len(scheduled_chores)

	# Build grid: kid_id -> { date_iso -> [{chore_name, coin_reward, point_value}] }
	grid = {kid.id: {day.isoformat(): [] for day in days} for kid in kids}
	for chore in scheduled_chores:
		for day in days:
			for slot in chore.assignments_for_date(day):
				if slot.kid_id in grid:
					grid[slot.kid_id][day.isoformat()].append({
						"chore_name": chore.name,
						"coin_reward": chore.coin_reward,
						"point_value": chore.point_value,
					})

	return render_template(
		"private/parents/schedule/index.html",
		parent=parent,
		family=family,
		kids=kids,
		days=days,
		week_start=week_start,
		week_end=week_end,
		week_offset=week_offset,
		today=today,
		grid=grid,
		scheduled_chore_count=len(scheduled_chores),
		unscheduled_count=unscheduled_count,
		loop_colors=["#58cc02", "#1cb0f6", "#ff9600", "#a855f7", "#ef4444", "#14b8a6"],
	)


@public_bp.post("/parent/chores/create")
@parent_web_login_required
def parent_create_chore():
	# Tier limit check
	_fam = Family.query.get(session["family_id"])
	if _fam:
		_current = Chore.query.filter_by(family_id=_fam.id, is_active=True).count()
		if not can_add(_fam, "chores", _current):
			flash(limit_reached_message("chores"), "warning")
			return redirect(url_for("public.parent_chores"))

	parsed = _parse_chore_form_data(request.form, session["family_id"])
	if parsed is None:
		return redirect(url_for("public.parent_chores"))

	parsed_categories = _parse_chore_categories(request.form, session["family_id"])
	if parsed_categories is None:
		return redirect(url_for("public.parent_chores"))

	chore = Chore(
		family_id=session["family_id"],
		created_by_parent_id=session["parent_id"],
		name=parsed["name"],
		description=parsed["description"],
		requires_photo_proof=parsed["requires_photo_proof"],
		coin_reward=parsed["coin_reward"],
		point_value=parsed["point_value"],
		max_concurrent_claims=parsed["max_concurrent_claims"],
		schedule_kind=parsed["schedule_kind"],
		rotation_cycle_weeks=parsed["rotation_cycle_weeks"],
		anchor_date=parsed["anchor_date"],
	)
	db.session.add(chore)
	db.session.flush()
	chore.categories = parsed_categories

	for slot in parsed["slots"]:
		db.session.add(ChoreScheduleSlot(chore_id=chore.id, **slot))

	db.session.commit()

	flash(f'Created chore "{parsed["name"]}".', "success")
	return redirect(url_for("public.parent_chores"))


@public_bp.route("/parent/chores/<int:chore_id>/edit", methods=["GET", "POST"])
@parent_web_login_required
def parent_edit_chore(chore_id: int):
	parent, family = _load_parent_and_family()
	chore = Chore.query.get(chore_id)

	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	if not chore or chore.family_id != family.id:
		flash("Chore not found.", "error")
		return redirect(url_for("public.parent_chores"))

	if request.method == "POST":
		parsed = _parse_chore_form_data(request.form, family.id)
		if parsed is None:
			return redirect(url_for("public.parent_edit_chore", chore_id=chore.id))

		parsed_categories = _parse_chore_categories(request.form, family.id)
		if parsed_categories is None:
			return redirect(url_for("public.parent_edit_chore", chore_id=chore.id))

		chore.name = parsed["name"]
		chore.description = parsed["description"]
		chore.requires_photo_proof = parsed["requires_photo_proof"]
		chore.coin_reward = parsed["coin_reward"]
		chore.point_value = parsed["point_value"]
		chore.max_concurrent_claims = parsed["max_concurrent_claims"]
		chore.schedule_kind = parsed["schedule_kind"]
		chore.rotation_cycle_weeks = parsed["rotation_cycle_weeks"]
		chore.anchor_date = parsed["anchor_date"]
		chore.categories = parsed_categories
		chore.schedule_slots.clear()
		db.session.flush()

		for slot in parsed["slots"]:
			db.session.add(ChoreScheduleSlot(chore_id=chore.id, **slot))

		db.session.commit()
		flash(f'Updated chore "{chore.name}".', "success")
		return redirect(url_for("public.parent_chores"))

	kids = Kid.query.filter_by(family_id=family.id, is_active=True).order_by(Kid.display_name.asc()).all()
	return render_template(
		"private/parents/chores/edit.html",
		parent=parent,
		family=family,
		kids=kids,
		categories=ChoreCategory.query.filter_by(family_id=family.id).order_by(ChoreCategory.name.asc()).all(),
		chore=chore,
		weekday_labels=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
		slot_lookup=_build_chore_slot_lookup(chore),
		requires_photo_proof_checked=bool(chore.requires_photo_proof),
		selected_category_ids={str(category.id) for category in chore.categories},
	)


@public_bp.post("/parent/chores/toggle/<int:chore_id>")
@parent_web_login_required
def parent_toggle_chore(chore_id: int):
	chore = Chore.query.get(chore_id)
	if not chore or chore.family_id != session.get("family_id"):
		flash("Chore not found.", "error")
		return redirect(url_for("public.parent_chores"))

	chore.is_active = not chore.is_active
	db.session.commit()
	flash(f'Chore "{chore.name}" is now {"active" if chore.is_active else "paused"}.', "success")
	return redirect(url_for("public.parent_chores"))


@public_bp.post("/parent/chores/<int:chore_id>/reset-day")
@parent_web_login_required
def parent_reset_chore_day(chore_id: int):
	parent = Parent.query.get(session.get("parent_id"))
	chore = Chore.query.get(chore_id)

	if not parent or not chore or chore.family_id != session.get("family_id"):
		flash("Chore not found.", "error")
		return redirect(url_for("public.parent_chores"))

	active_submissions = ChoreSubmission.query.filter(
		ChoreSubmission.chore_id == chore.id,
		ChoreSubmission.reset_version == chore.daily_reset_version,
		ChoreSubmission.status.in_(["claimed", "submitted"]),
	).all()

	for submission in active_submissions:
		submission.status = "rejected"
		submission.resolved_at = datetime.utcnow()
		submission.resolved_by_parent_id = parent.id
		submission.resolution_note = "Reset by parent"

	chore.daily_reset_version += 1
	db.session.commit()

	flash(f'"{chore.name}" is reset and can be claimed again today.', "success")
	return redirect(url_for("public.parent_chores"))


@public_bp.post("/parent/chores/<int:chore_id>/delete")
@parent_web_login_required
def parent_delete_chore(chore_id: int):
	parent, family = _load_parent_and_family()
	if not parent or not family:
		return redirect(url_for("public.login"))
	chore = Chore.query.get(chore_id)
	if not chore or chore.family_id != family.id:
		flash("Chore not found.", "error")
		return redirect(url_for("public.parent_chores"))
	name = chore.name
	db.session.delete(chore)
	db.session.commit()
	flash(f'"{name}" deleted.', "success")
	return redirect(url_for("public.parent_chores"))


@public_bp.get("/parent/chores/submissions/<int:submission_id>/photo/<string:photo_type>")
@parent_web_login_required
def parent_view_chore_submission_photo(submission_id: int, photo_type: str):
	submission = ChoreSubmission.query.get(submission_id)
	if not submission or submission.family_id != session.get("family_id"):
		abort(404)

	if photo_type not in {"before", "after"}:
		abort(404)

	photo_path = submission.before_photo_path if photo_type == "before" else submission.after_photo_path
	if not photo_path:
		abort(404)

	filename = os.path.basename(photo_path)
	directory = os.path.join(current_app.instance_path, "uploads", "chore_photos")
	return send_from_directory(directory, filename)


@public_bp.post("/parent/chores/submissions/<int:submission_id>/decision")
@parent_web_login_required
def parent_chore_submission_decision(submission_id: int):
	parent = Parent.query.get(session.get("parent_id"))
	submission = ChoreSubmission.query.get(submission_id)
	action = (request.form.get("action") or "").strip().lower()
	resolution_note = (request.form.get("resolution_note") or "").strip()
	reward_percent_raw = (request.form.get("reward_percent") or "100").strip()

	if not parent or not submission or submission.family_id != session.get("family_id"):
		flash("Submission not found.", "error")
		return redirect(url_for("public.parent_chores"))

	if submission.status != "submitted":
		flash("Only submitted chores can be reviewed.", "error")
		return redirect(url_for("public.parent_chores"))

	if action not in {"approve", "reject"}:
		flash("Invalid decision.", "error")
		return redirect(url_for("public.parent_chores"))

	try:
		reward_percent = int(reward_percent_raw)
	except ValueError:
		flash("Reward percent must be a number between 0 and 100.", "error")
		return redirect(url_for("public.parent_chores"))

	if reward_percent < 0 or reward_percent > 100:
		flash("Reward percent must be between 0 and 100.", "error")
		return redirect(url_for("public.parent_chores"))

	submission.status = "approved" if action == "approve" else "rejected"
	submission.resolved_at = datetime.utcnow()
	submission.resolved_by_parent_id = parent.id
	submission.resolution_note = resolution_note or None

	if action == "reject":
		submission.awarded_coin_amount = 0
		submission.awarded_point_amount = 0

	if action == "approve":
		if submission.chore.max_concurrent_claims > 1:
			if reward_percent != 100:
				flash(
					"Partial rewards currently apply only to chores with 1 claim slot; full reward was used for this shared chore.",
					"info",
				)
			_recalculate_chore_split_rewards(
				submission.chore,
				submission.reset_version,
				_submission_day_key(submission),
			)
		else:
			target_coin_award = (submission.chore.coin_reward * reward_percent) // 100
			target_point_award = (submission.chore.point_value * reward_percent) // 100
			_apply_chore_award(submission, target_coin_award, target_point_award)

	db.session.commit()
	flash(
		f"{submission.kid.display_name}'s submission for '{submission.chore.name}' was {submission.status}.",
		"success" if action == "approve" else "info",
	)
	return redirect(url_for("public.parent_chores"))


@public_bp.get("/parent/store")
@parent_web_login_required
def parent_store():
	parent, family = _load_parent_and_family()

	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	active_tab = request.args.get("tab", "kid")
	if active_tab not in {"kid", "family"}:
		active_tab = "kid"

	kid_items = (
		StoreItem.query.filter_by(family_id=family.id, item_scope="kid", is_active=True)
		.order_by(StoreItem.created_at.desc())
		.all()
	)
	family_items = (
		StoreItem.query.filter_by(family_id=family.id, item_scope="family", is_active=True)
		.order_by(StoreItem.created_at.desc())
		.all()
	)
	kids = Kid.query.filter_by(family_id=family.id, is_active=True).order_by(Kid.display_name.asc()).all()

	family_redemptions = (
		StoreRedemption.query.join(StoreItem, StoreRedemption.store_item_id == StoreItem.id)
		.filter(StoreRedemption.family_id == family.id, StoreItem.item_scope == "family")
		.order_by(StoreRedemption.requested_at.desc())
		.limit(30)
		.all()
	)
	pending_kid_redemptions = (
		StoreRedemption.query.join(StoreItem, StoreRedemption.store_item_id == StoreItem.id)
		.filter(
			StoreRedemption.family_id == family.id,
			StoreRedemption.status == "pending",
			StoreItem.item_scope == "kid",
		)
		.order_by(StoreRedemption.requested_at.desc())
		.limit(30)
		.all()
	)
	vote_summary = _vote_summary_for_redemptions(family_redemptions)

	active_sessions = (
		StoreTimedSession.query.filter_by(family_id=family.id, status="active")
		.order_by(StoreTimedSession.started_at.desc())
		.all()
	)
	recent_sessions = (
		StoreTimedSession.query.filter(
			StoreTimedSession.family_id == family.id,
			StoreTimedSession.status.in_(["completed", "cancelled"]),
		)
		.order_by(StoreTimedSession.ended_at.desc())
		.limit(20)
		.all()
	)

	return render_template(
		"private/parents/store/index.html",
		parent=parent,
		family=family,
		kids=kids,
		kid_items=kid_items,
		family_items=family_items,
		family_redemptions=family_redemptions,
		pending_kid_redemptions=pending_kid_redemptions,
		vote_summary=vote_summary,
		active_tab=active_tab,
		active_sessions=active_sessions,
		recent_sessions=recent_sessions,
	)


@public_bp.post("/parent/store/items/create")
@parent_web_login_required
def parent_store_create_item():
	# Tier limit check
	_fam = Family.query.get(session["family_id"])
	if _fam:
		_current = StoreItem.query.filter_by(family_id=_fam.id, is_active=True).count()
		if not can_add(_fam, "store_items", _current):
			flash(limit_reached_message("store_items"), "warning")
			return redirect(url_for("public.parent_store"))

	name = (request.form.get("name") or "").strip()
	description = (request.form.get("description") or "").strip()
	item_scope = (request.form.get("item_scope") or "").strip()
	item_type = (request.form.get("item_type") or "basic").strip()
	kid_coin_cost_raw = (request.form.get("kid_coin_cost") or "0").strip()
	family_point_cost_raw = (request.form.get("family_point_cost") or "0").strip()

	# Timed session fields
	session_rate_type = (request.form.get("session_rate_type") or "per_minute").strip()
	session_flat_cost_raw = (request.form.get("session_flat_cost") or "0").strip()
	session_per_min_raw = (request.form.get("session_coin_per_minute") or "0").strip()
	session_max_raw = (request.form.get("session_max_participants") or "1").strip()
	stock_qty_raw = (request.form.get("stock_qty") or "-1").strip()
	require_parent_approval = (request.form.get("require_parent_approval") or "").strip().lower() in {"on", "true", "1", "yes"}

	if not name:
		flash("Item name is required.", "error")
		return redirect(url_for("public.parent_store", tab="kid"))

	if item_scope not in {"kid", "family"}:
		flash("Please choose a valid store type.", "error")
		return redirect(url_for("public.parent_store", tab="kid"))

	if item_type not in {"basic", "timed_session"}:
		item_type = "basic"
	if item_scope == "family":
		item_type = "basic"

	try:
		kid_coin_cost = max(0, int(kid_coin_cost_raw))
	except ValueError:
		flash("Kid coin cost must be a number.", "error")
		return redirect(url_for("public.parent_store", tab=item_scope))

	try:
		family_point_cost = max(0, int(family_point_cost_raw))
	except ValueError:
		flash("Family point cost must be a number.", "error")
		return redirect(url_for("public.parent_store", tab=item_scope))

	# Cost validation: basic items require cost; timed_session validates session fields instead
	if item_scope == "kid" and item_type == "basic" and kid_coin_cost <= 0:
		flash("Kid items must cost at least 1 coin.", "error")
		return redirect(url_for("public.parent_store", tab="kid"))

	if item_scope == "family" and family_point_cost <= 0:
		flash("Family items must cost at least 1 family point.", "error")
		return redirect(url_for("public.parent_store", tab="family"))

	# Parse timed session fields
	session_duration_minutes = None
	session_flat_cost = 0
	session_coin_per_minute = 0
	session_max_participants = 1
	if item_type == "timed_session":
		if session_rate_type not in {"flat", "per_minute"}:
			session_rate_type = "per_minute"
		try:
			session_flat_cost = max(0, int(session_flat_cost_raw))
		except ValueError:
			session_flat_cost = 0
		try:
			session_coin_per_minute = max(0, int(session_per_min_raw))
		except ValueError:
			session_coin_per_minute = 0
		try:
			session_max_participants = max(1, int(session_max_raw))
		except ValueError:
			session_max_participants = 1
		if session_rate_type == "per_minute" and session_coin_per_minute <= 0:
			flash("Turn timers need a coin-per-minute cost.", "error")
			return redirect(url_for("public.parent_store", tab="kid"))

	try:
		stock_qty = max(-1, int(stock_qty_raw))
	except ValueError:
		stock_qty = -1

	item = StoreItem(
		family_id=session["family_id"],
		created_by_parent_id=session["parent_id"],
		name=name,
		description=description or None,
		item_scope=item_scope,
		item_type=item_type,
		kid_coin_cost=kid_coin_cost if item_scope == "kid" and item_type == "basic" else 0,
		family_point_cost=family_point_cost if item_scope == "family" else 0,
		timing_mode=None,
		session_duration_minutes=session_duration_minutes,
		session_rate_type=session_rate_type if item_type == "timed_session" else None,
		session_flat_cost=session_flat_cost,
		session_coin_per_minute=session_coin_per_minute,
		session_max_participants=session_max_participants,
		stock_qty=stock_qty,
		require_parent_approval=(require_parent_approval if item_scope == "kid" and item_type == "basic" else False),
	)
	db.session.add(item)
	db.session.commit()

	flash(f'Added "{item.name}" to the {item_scope} store.', "success")
	return redirect(url_for("public.parent_store", tab=item_scope))


@public_bp.post("/parent/store/items/<int:item_id>/toggle")
@parent_web_login_required
def parent_store_toggle_item(item_id: int):
	item = StoreItem.query.get(item_id)
	if not item or item.family_id != session.get("family_id"):
		flash("Store item not found.", "error")
		return redirect(url_for("public.parent_store"))

	item.is_active = not item.is_active
	db.session.commit()
	flash(f'"{item.name}" is now {"active" if item.is_active else "paused"}.', "success")
	return redirect(url_for("public.parent_store", tab=item.item_scope))


@public_bp.post("/parent/store/items/<int:item_id>/edit")
@parent_web_login_required
def parent_store_edit_item(item_id: int):
	item = StoreItem.query.get(item_id)
	if not item or item.family_id != session.get("family_id"):
		flash("Store item not found.", "error")
		return redirect(url_for("public.parent_store"))

	name = (request.form.get("name") or "").strip()
	description = (request.form.get("description") or "").strip()
	item_type = (request.form.get("item_type") or item.item_type).strip()
	kid_coin_cost_raw = (request.form.get("kid_coin_cost") or "0").strip()
	family_point_cost_raw = (request.form.get("family_point_cost") or "0").strip()
	session_rate_type = (request.form.get("session_rate_type") or item.session_rate_type or "per_minute").strip()
	session_flat_cost_raw = (request.form.get("session_flat_cost") or "0").strip()
	session_per_min_raw = (request.form.get("session_coin_per_minute") or "0").strip()
	session_max_raw = (request.form.get("session_max_participants") or "1").strip()
	stock_qty_raw = (request.form.get("stock_qty") or "-1").strip()
	require_parent_approval = (request.form.get("require_parent_approval") or "").strip().lower() in {"on", "true", "1", "yes"}

	if not name:
		flash("Item name is required.", "error")
		return redirect(url_for("public.parent_store", tab=item.item_scope))

	if item_type not in {"basic", "timed_session"}:
		item_type = "basic"
	if item.item_scope == "family":
		item_type = "basic"

	try:
		kid_coin_cost = max(0, int(kid_coin_cost_raw))
	except ValueError:
		kid_coin_cost = 0

	try:
		family_point_cost = max(0, int(family_point_cost_raw))
	except ValueError:
		family_point_cost = 0

	if item.item_scope == "kid" and item_type == "basic" and kid_coin_cost <= 0:
		flash("Kid items must cost at least 1 coin.", "error")
		return redirect(url_for("public.parent_store", tab="kid"))

	if item.item_scope == "family" and family_point_cost <= 0:
		flash("Family items must cost at least 1 family point.", "error")
		return redirect(url_for("public.parent_store", tab="family"))

	session_flat_cost = 0
	session_coin_per_minute = 0
	session_max_participants = 1
	if item_type == "timed_session":
		if session_rate_type not in {"flat", "per_minute"}:
			session_rate_type = "per_minute"
		try:
			session_flat_cost = max(0, int(session_flat_cost_raw))
		except ValueError:
			session_flat_cost = 0
		try:
			session_coin_per_minute = max(0, int(session_per_min_raw))
		except ValueError:
			session_coin_per_minute = 0
		try:
			session_max_participants = max(1, int(session_max_raw))
		except ValueError:
			session_max_participants = 1
		if session_rate_type == "per_minute" and session_coin_per_minute <= 0:
			flash("Turn timers need a coin-per-minute cost.", "error")
			return redirect(url_for("public.parent_store", tab="kid"))

	try:
		stock_qty = max(-1, int(stock_qty_raw))
	except ValueError:
		stock_qty = -1

	item.name = name
	item.description = description or None
	item.item_type = item_type
	item.kid_coin_cost = kid_coin_cost if item.item_scope == "kid" and item_type == "basic" else 0
	item.family_point_cost = family_point_cost if item.item_scope == "family" else 0
	item.session_rate_type = session_rate_type if item_type == "timed_session" else None
	item.session_flat_cost = session_flat_cost
	item.session_coin_per_minute = session_coin_per_minute
	item.session_max_participants = session_max_participants
	item.stock_qty = stock_qty
	item.require_parent_approval = require_parent_approval if item.item_scope == "kid" and item_type == "basic" else False
	db.session.commit()

	flash(f'"{item.name}" updated.', "success")
	return redirect(url_for("public.parent_store", tab=item.item_scope))


@public_bp.post("/parent/store/items/<int:item_id>/delete")
@parent_web_login_required
def parent_store_delete_item(item_id: int):
	item = StoreItem.query.get(item_id)
	if not item or item.family_id != session.get("family_id"):
		flash("Store item not found.", "error")
		return redirect(url_for("public.parent_store"))

	item_name = item.name
	item_scope = item.item_scope
	db.session.delete(item)
	db.session.commit()

	flash(f'"{item_name}" deleted.', "success")
	return redirect(url_for("public.parent_store", tab=item_scope))


@public_bp.post("/parent/store/family-points/add")
@parent_web_login_required
def parent_store_add_family_points():
	family = Family.query.get(session.get("family_id"))
	points_raw = (request.form.get("points") or "0").strip()
	next_path = (request.form.get("next") or "").strip()

	if not family:
		flash("Family not found.", "error")
		return _redirect_to_next_or_default(next_path, "public.parent_store", tab="family")

	try:
		points = int(points_raw)
	except ValueError:
		flash("Points must be a number.", "error")
		return _redirect_to_next_or_default(next_path, "public.parent_store", tab="family")

	if points <= 0:
		flash("Points must be greater than zero.", "error")
		return _redirect_to_next_or_default(next_path, "public.parent_store", tab="family")

	family.family_points_balance += points
	db.session.commit()
	flash(f"Added {points} family points.", "success")
	return _redirect_to_next_or_default(next_path, "public.parent_store", tab="family")


@public_bp.post("/parent/store/kid-coins/add")
@parent_web_login_required
def parent_store_add_kid_coins():
	kid_id_raw = (request.form.get("kid_id") or "").strip()
	coins_raw = (request.form.get("coins") or "0").strip()
	reason = (request.form.get("reason") or "").strip()
	next_path = (request.form.get("next") or "").strip()

	try:
		kid_id = int(kid_id_raw)
	except ValueError:
		flash("Please choose a valid kid.", "error")
		return _redirect_to_next_or_default(next_path, "public.parent_store", tab="kid")

	try:
		coins = int(coins_raw)
	except ValueError:
		flash("Coins must be a number.", "error")
		return _redirect_to_next_or_default(next_path, "public.parent_store", tab="kid")

	if coins <= 0:
		flash("Coins must be greater than zero.", "error")
		return _redirect_to_next_or_default(next_path, "public.parent_store", tab="kid")

	kid = Kid.query.get(kid_id)
	if not kid or kid.family_id != session.get("family_id"):
		flash("Kid not found.", "error")
		return _redirect_to_next_or_default(next_path, "public.parent_store", tab="kid")

	kid.coin_balance += coins
	tx_reason = reason if reason else "Rewarded by parent"
	db.session.add(CoinTransaction(
		kid_id=kid.id,
		family_id=kid.family_id,
		amount=coins,
		kind="manual_add",
		reason=tx_reason,
		created_by_parent_id=session.get("parent_id"),
	))
	db.session.commit()
	flash(f"Rewarded {kid.display_name} with {coins} coins.", "success")
	return _redirect_to_next_or_default(next_path, "public.parent_store", tab="kid")


@public_bp.post("/parent/store/kid-coins/cash-to-coins")
@parent_web_login_required
def parent_store_cash_to_coins():
	kid_id_raw = (request.form.get("kid_id") or "").strip()
	dollars_raw = (request.form.get("dollars") or "0").strip()
	next_path = (request.form.get("next") or "").strip()

	try:
		kid_id = int(kid_id_raw)
	except ValueError:
		flash("Please choose a valid kid.", "error")
		return _redirect_to_next_or_default(next_path, "public.parent_store", tab="kid")

	try:
		dollars = float(dollars_raw)
	except ValueError:
		flash("Dollar amount must be a number.", "error")
		return _redirect_to_next_or_default(next_path, "public.parent_store", tab="kid")

	if dollars <= 0:
		flash("Dollar amount must be greater than zero.", "error")
		return _redirect_to_next_or_default(next_path, "public.parent_store", tab="kid")

	kid = Kid.query.get(kid_id)
	if not kid or kid.family_id != session.get("family_id"):
		flash("Kid not found.", "error")
		return _redirect_to_next_or_default(next_path, "public.parent_store", tab="kid")

	family = Family.query.get(kid.family_id)
	rate = (family.coins_per_dollar if family and family.coins_per_dollar else 10)
	coins = int(dollars * rate)

	if coins <= 0:
		flash("Amount too small to convert to coins.", "error")
		return _redirect_to_next_or_default(next_path, "public.parent_store", tab="kid")

	kid.coin_balance += coins
	db.session.add(CoinTransaction(
		kid_id=kid.id,
		family_id=kid.family_id,
		amount=coins,
		kind="manual_add",
		reason=f"Cash to coins: ${dollars:.2f} = {coins} coins",
		created_by_parent_id=session.get("parent_id"),
	))
	db.session.commit()
	flash(f"Converted ${dollars:.2f} → {coins} coins for {kid.display_name}.", "success")
	return _redirect_to_next_or_default(next_path, "public.parent_store", tab="kid")


@public_bp.post("/parent/store/family/redemptions/<int:redemption_id>/approve")
@parent_web_login_required
def parent_store_approve_family_redemption(redemption_id: int):
	redemption = StoreRedemption.query.get(redemption_id)
	family = Family.query.get(session.get("family_id"))

	if not redemption or not family:
		flash("Family goal request not found.", "error")
		return redirect(url_for("public.parent_store", tab="family"))

	item = redemption.store_item
	if redemption.family_id != family.id or not item or item.item_scope != "family":
		flash("Family goal request not found.", "error")
		return redirect(url_for("public.parent_store", tab="family"))

	if redemption.status != "pending":
		flash("Only pending requests can be approved.", "error")
		return redirect(url_for("public.parent_store", tab="family"))

	if family.family_points_balance < item.family_point_cost:
		flash("Not enough family points to approve this request.", "error")
		return redirect(url_for("public.parent_store", tab="family"))

	family.family_points_balance -= item.family_point_cost
	redemption.status = "approved"
	redemption.resolved_at = datetime.utcnow()
	redemption.resolved_by_parent_id = session["parent_id"]
	db.session.commit()

	flash(f'Approved "{item.name}" for {redemption.requested_by_kid.display_name}.', "success")
	return redirect(url_for("public.parent_store", tab="family"))


@public_bp.post("/parent/store/family/redemptions/<int:redemption_id>/reject")
@parent_web_login_required
def parent_store_reject_family_redemption(redemption_id: int):
	redemption = StoreRedemption.query.get(redemption_id)

	if not redemption or redemption.family_id != session.get("family_id"):
		flash("Family goal request not found.", "error")
		return redirect(url_for("public.parent_store", tab="family"))

	item = redemption.store_item
	if not item or item.item_scope != "family":
		flash("Family goal request not found.", "error")
		return redirect(url_for("public.parent_store", tab="family"))

	if redemption.status != "pending":
		flash("Only pending requests can be rejected.", "error")
		return redirect(url_for("public.parent_store", tab="family"))

	redemption.status = "rejected"
	redemption.resolved_at = datetime.utcnow()
	redemption.resolved_by_parent_id = session["parent_id"]
	db.session.commit()

	flash(f'Rejected "{item.name}" request.', "success")
	return redirect(url_for("public.parent_store", tab="family"))


@public_bp.post("/parent/store/family/redemptions/<int:redemption_id>/fulfill")
@parent_web_login_required
def parent_store_fulfill_family_redemption(redemption_id: int):
	redemption = StoreRedemption.query.get(redemption_id)

	if not redemption or redemption.family_id != session.get("family_id"):
		flash("Family goal request not found.", "error")
		return redirect(url_for("public.parent_store", tab="family"))

	item = redemption.store_item
	if not item or item.item_scope != "family":
		flash("Family goal request not found.", "error")
		return redirect(url_for("public.parent_store", tab="family"))

	if redemption.status != "approved":
		flash("Only approved requests can be fulfilled.", "error")
		return redirect(url_for("public.parent_store", tab="family"))

	redemption.status = "fulfilled"
	redemption.resolved_at = datetime.utcnow()
	redemption.resolved_by_parent_id = session["parent_id"]
	db.session.commit()

	flash(f'Fulfilled "{item.name}".', "success")
	return redirect(url_for("public.parent_store", tab="family"))


@public_bp.post("/parent/store/kid/redemptions/<int:redemption_id>/approve")
@parent_web_login_required
def parent_store_approve_kid_redemption(redemption_id: int):
	redemption = StoreRedemption.query.get(redemption_id)

	if not redemption or redemption.family_id != session.get("family_id"):
		flash("Kid purchase request not found.", "error")
		return redirect(url_for("public.parent_store", tab="kid"))

	item = redemption.store_item
	kid = redemption.requested_by_kid
	if not item or item.item_scope != "kid" or item.item_type != "basic":
		flash("Kid purchase request not found.", "error")
		return redirect(url_for("public.parent_store", tab="kid"))

	if redemption.status != "pending":
		flash("Only pending requests can be approved.", "error")
		return redirect(url_for("public.parent_store", tab="kid"))

	if item.stock_qty == 0:
		flash(f'"{item.name}" is out of stock. Reject this request or restock first.', "error")
		return redirect(url_for("public.parent_store", tab="kid"))

	participants = list(redemption.participants or [])
	if participants:
		participant_ids = [participant.kid_id for participant in participants]
		participant_kids = {
			participant_kid.id: participant_kid
			for participant_kid in Kid.query.filter(
				Kid.family_id == redemption.family_id,
				Kid.id.in_(participant_ids),
				Kid.is_active.is_(True),
			).all()
		}
		insufficient_kids: list[str] = []
		for participant in participants:
			participant_kid = participant_kids.get(participant.kid_id)
			if not participant_kid:
				insufficient_kids.append("Missing participant")
				continue
			if participant_kid.coin_balance < participant.coin_share:
				insufficient_kids.append(participant_kid.display_name)
		if insufficient_kids:
			flash(f"Not enough coins to approve this split purchase: {', '.join(insufficient_kids)}.", "error")
			return redirect(url_for("public.parent_store", tab="kid"))

		for participant in participants:
			participant_kid = participant_kids.get(participant.kid_id)
			if not participant_kid:
				continue
			participant_kid.coin_balance -= participant.coin_share
			db.session.add(CoinTransaction(
				kid_id=participant_kid.id,
				family_id=participant_kid.family_id,
				amount=-participant.coin_share,
				kind="store_purchase",
				reason=f"Store split purchase approved: {item.name}",
				ref_type="store_redemption",
				ref_id=redemption.id,
				created_by_parent_id=session.get("parent_id"),
			))
	else:
		if not kid or kid.coin_balance < item.kid_coin_cost:
			flash(f"{kid.display_name if kid else 'Kid'} no longer has enough coins for this purchase.", "error")
			return redirect(url_for("public.parent_store", tab="kid"))

		kid.coin_balance -= item.kid_coin_cost
		db.session.add(CoinTransaction(
			kid_id=kid.id,
			family_id=kid.family_id,
			amount=-item.kid_coin_cost,
			kind="store_purchase",
			reason=f"Store purchase approved: {item.name}",
			ref_type="store_redemption",
			ref_id=redemption.id,
			created_by_parent_id=session.get("parent_id"),
		))

	if item.stock_qty > 0:
		item.stock_qty -= 1

	redemption.status = "fulfilled"
	redemption.resolved_at = datetime.utcnow()
	redemption.resolved_by_parent_id = session["parent_id"]
	db.session.commit()

	if participants and len(participants) > 1:
		flash(f'Approved split purchase "{item.name}" for {len(participants)} kids.', "success")
	else:
		flash(f'Approved purchase "{item.name}" for {kid.display_name}.', "success")
	return redirect(url_for("public.parent_store", tab="kid"))


@public_bp.post("/parent/store/kid/redemptions/<int:redemption_id>/reject")
@parent_web_login_required
def parent_store_reject_kid_redemption(redemption_id: int):
	redemption = StoreRedemption.query.get(redemption_id)

	if not redemption or redemption.family_id != session.get("family_id"):
		flash("Kid purchase request not found.", "error")
		return redirect(url_for("public.parent_store", tab="kid"))

	item = redemption.store_item
	if not item or item.item_scope != "kid" or item.item_type != "basic":
		flash("Kid purchase request not found.", "error")
		return redirect(url_for("public.parent_store", tab="kid"))

	if redemption.status != "pending":
		flash("Only pending requests can be rejected.", "error")
		return redirect(url_for("public.parent_store", tab="kid"))

	redemption.status = "rejected"
	redemption.resolved_at = datetime.utcnow()
	redemption.resolved_by_parent_id = session["parent_id"]
	db.session.commit()

	flash(f'Rejected purchase request for "{item.name}".', "success")
	return redirect(url_for("public.parent_store", tab="kid"))


@public_bp.post("/parent/store/sessions/<int:timed_session_id>/cancel")
@parent_web_login_required
def parent_cancel_store_session(timed_session_id: int):
	timed_session = StoreTimedSession.query.get(timed_session_id)
	if not timed_session or timed_session.family_id != session.get("family_id"):
		flash("Session not found.", "error")
		return redirect(url_for("public.parent_store", tab="kid"))

	if timed_session.status != "active":
		flash("Only active sessions can be cancelled.", "info")
		return redirect(url_for("public.parent_store", tab="kid"))

	timed_session.status = "cancelled"
	timed_session.ended_at = datetime.utcnow()
	item = timed_session.store_item
	refunded_coins = 0
	for turn in timed_session.turns or []:
		if turn.ended_at is None:
			_close_store_session_turn(turn, timed_session.ended_at)
		if turn.coins_charged and turn.participant and turn.participant.charges_coins and turn.participant.kid:
			turn.participant.kid.coin_balance += turn.coins_charged
			refunded_coins += turn.coins_charged
			turn.coins_charged = 0
	timed_session.total_coins_charged = 0

	# Restore stock slot
	if item and item.stock_qty >= 0:
		item.stock_qty += 1

	db.session.commit()
	if refunded_coins:
		flash(f'Session for "{timed_session.store_item.name if timed_session.store_item else "item"}" cancelled and {refunded_coins} coins refunded.', "success")
	else:
		flash(f'Session for "{timed_session.store_item.name if timed_session.store_item else "item"}" cancelled.', "success")
	return redirect(url_for("public.parent_store", tab="kid"))


# ── CHALLENGES ─────────────────────────────────────────────────────────────────

@public_bp.get("/parent/challenges")
@parent_web_login_required
def parent_challenges():
	parent, family = _load_parent_and_family()
	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	challenges = Challenge.query.filter_by(family_id=family.id).order_by(Challenge.sort_order.asc(), Challenge.created_at.asc()).all()
	pending_submissions = (
		ChallengeSubmission.query.filter_by(family_id=family.id, status="submitted")
		.order_by(ChallengeSubmission.submitted_at.desc())
		.all()
	)
	return render_template(
		"private/parents/challenges/index.html",
		parent=parent,
		family=family,
		challenges=challenges,
		pending_submissions=pending_submissions,
	)


@public_bp.post("/parent/store/reorder")
@parent_web_login_required
def parent_store_reorder_items():
	parent, family = _load_parent_and_family()
	if not parent or not family:
		return jsonify({"error": "unauthorized"}), 401
	data = request.get_json(silent=True)
	if not data or "order" not in data:
		return jsonify({"error": "bad request"}), 400
	items_by_id = {i.id: i for i in StoreItem.query.filter_by(family_id=family.id).all()}
	for position, item_id in enumerate(data["order"]):
		item = items_by_id.get(item_id)
		if item:
			item.sort_order = position
	db.session.commit()
	return jsonify({"success": True})


@public_bp.post("/parent/challenges/reorder")
@parent_web_login_required
def parent_reorder_challenges():
	parent, family = _load_parent_and_family()
	if not parent or not family:
		return jsonify({"error": "unauthorized"}), 401
	data = request.get_json(silent=True)
	if not data or "order" not in data:
		return jsonify({"error": "bad request"}), 400
	challenges_by_id = {c.id: c for c in Challenge.query.filter_by(family_id=family.id).all()}
	for position, challenge_id in enumerate(data["order"]):
		challenge = challenges_by_id.get(challenge_id)
		if challenge:
			challenge.sort_order = position
	db.session.commit()
	return jsonify({"success": True})


@public_bp.post("/parent/tasks/reorder")
@parent_web_login_required
def parent_reorder_tasks():
	parent = Parent.query.get(session["parent_id"])
	family_id = session["family_id"]
	if not parent:
		return jsonify({"error": "unauthorized"}), 401
	data = request.get_json(silent=True)
	if not data or "order" not in data:
		return jsonify({"error": "bad request"}), 400
	tasks_by_id = {t.id: t for t in Task.query.filter_by(family_id=family_id).all()}
	for position, task_id in enumerate(data["order"]):
		task = tasks_by_id.get(task_id)
		if task:
			task.sort_order = position
	db.session.commit()
	return jsonify({"success": True})


@public_bp.post("/parent/challenges/create")
@parent_web_login_required
def parent_challenge_create():
	parent, family = _load_parent_and_family()
	if not parent or not family:
		return redirect(url_for("public.login"))

	# Tier limit check
	_current = Challenge.query.filter_by(family_id=family.id, is_active=True).count()
	if not can_add(family, "challenges", _current):
		flash(limit_reached_message("challenges"), "warning")
		return redirect(url_for("public.parent_challenges"))

	title = (request.form.get("title") or "").strip()
	description = (request.form.get("description") or "").strip()
	difficulty = (request.form.get("difficulty") or "bronze").strip()
	coin_reward = int(request.form.get("coin_reward") or 0)
	point_value = int(request.form.get("point_value") or 0)
	requires_proof = request.form.get("requires_proof") == "1"
	is_repeatable = request.form.get("is_repeatable") == "1"

	if not title:
		flash("Challenge title is required.", "error")
		return redirect(url_for("public.parent_challenges"))

	if difficulty not in {"bronze", "silver", "gold"}:
		difficulty = "bronze"

	challenge = Challenge(
		family_id=family.id,
		created_by_parent_id=parent.id,
		title=title,
		description=description or None,
		difficulty=difficulty,
		coin_reward=max(0, coin_reward),
		point_value=max(0, point_value),
		requires_proof=requires_proof,
		is_repeatable=is_repeatable,
	)
	db.session.add(challenge)
	db.session.commit()
	flash(f"Challenge '{title}' created!", "success")
	return redirect(url_for("public.parent_challenges"))


@public_bp.post("/parent/challenges/<int:challenge_id>/toggle")
@parent_web_login_required
def parent_challenge_toggle(challenge_id: int):
	parent, family = _load_parent_and_family()
	if not parent or not family:
		return redirect(url_for("public.login"))

	challenge = Challenge.query.get(challenge_id)
	if not challenge or challenge.family_id != family.id:
		flash("Challenge not found.", "error")
		return redirect(url_for("public.parent_challenges"))

	challenge.is_active = not challenge.is_active
	db.session.commit()
	state = "activated" if challenge.is_active else "deactivated"
	flash(f"'{challenge.title}' {state}.", "success")
	return redirect(url_for("public.parent_challenges"))


@public_bp.post("/parent/challenges/<int:challenge_id>/edit")
@parent_web_login_required
def parent_challenge_edit(challenge_id: int):
	parent, family = _load_parent_and_family()
	if not parent or not family:
		return redirect(url_for("public.login"))

	challenge = Challenge.query.get(challenge_id)
	if not challenge or challenge.family_id != family.id:
		flash("Challenge not found.", "error")
		return redirect(url_for("public.parent_challenges"))

	title = (request.form.get("title") or "").strip()
	if title:
		challenge.title = title
	description = request.form.get("description")
	if description is not None:
		challenge.description = description.strip() or None
	difficulty = (request.form.get("difficulty") or "").strip()
	if difficulty in {"bronze", "silver", "gold"}:
		challenge.difficulty = difficulty
	coin_reward = request.form.get("coin_reward")
	if coin_reward is not None:
		challenge.coin_reward = max(0, int(coin_reward or 0))
	point_value = request.form.get("point_value")
	if point_value is not None:
		challenge.point_value = max(0, int(point_value or 0))
	challenge.requires_proof = request.form.get("requires_proof") == "1"
	challenge.is_repeatable = request.form.get("is_repeatable") == "1"
	db.session.commit()
	flash(f"'{challenge.title}' updated.", "success")
	return redirect(url_for("public.parent_challenges"))


@public_bp.post("/parent/challenges/<int:challenge_id>/delete")
@parent_web_login_required
def parent_delete_challenge(challenge_id: int):
	parent, family = _load_parent_and_family()
	if not parent or not family:
		return redirect(url_for("public.login"))
	challenge = Challenge.query.get(challenge_id)
	if not challenge or challenge.family_id != family.id:
		flash("Challenge not found.", "error")
		return redirect(url_for("public.parent_challenges"))
	title = challenge.title
	db.session.delete(challenge)
	db.session.commit()
	flash(f"'{title}' deleted.", "success")
	return redirect(url_for("public.parent_challenges"))


@public_bp.post("/parent/challenges/submissions/<int:submission_id>/decision")
@parent_web_login_required
def parent_challenge_submission_decision(submission_id: int):
	parent, family = _load_parent_and_family()
	if not parent or not family:
		return redirect(url_for("public.login"))

	submission = ChallengeSubmission.query.get(submission_id)
	action = (request.form.get("action") or "").strip().lower()
	resolution_note = (request.form.get("resolution_note") or "").strip()

	if not submission or submission.family_id != family.id:
		flash("Submission not found.", "error")
		return redirect(url_for("public.parent_challenges"))

	if submission.status != "submitted":
		flash("Only submitted challenges can be reviewed.", "error")
		return redirect(url_for("public.parent_challenges"))

	if action not in {"approve", "reject"}:
		flash("Invalid decision.", "error")
		return redirect(url_for("public.parent_challenges"))

	submission.resolved_at = datetime.utcnow()
	submission.resolved_by_parent_id = parent.id
	submission.resolution_note = resolution_note or None

	if action == "reject":
		submission.status = "rejected"
		submission.awarded_coin_amount = 0
		submission.awarded_point_amount = 0
	else:
		submission.status = "approved"
		submission.awarded_coin_amount = submission.challenge.coin_reward
		submission.awarded_point_amount = submission.challenge.point_value
		kid = submission.kid
		kid.coin_balance += submission.awarded_coin_amount
		family.family_points_balance = (family.family_points_balance or 0) + submission.awarded_point_amount
		tx = CoinTransaction(
			kid_id=kid.id,
			family_id=family.id,
			amount=submission.awarded_coin_amount,
			kind="challenge_reward",
			reason=f"Challenge: {submission.challenge.title}",
			ref_type="challenge_submission",
			ref_id=submission.id,
			created_by_parent_id=parent.id,
		)
		db.session.add(tx)

	db.session.commit()
	flash(
		f"{submission.kid.display_name}'s challenge '{submission.challenge.title}' was {submission.status}.",
		"success" if action == "approve" else "info",
	)
	return redirect(url_for("public.parent_challenges"))


@public_bp.get("/parent/activities")
@parent_web_login_required
def parent_activities():
	return render_template("private/parents/coming_soon.html", page_title="Activities")



@public_bp.get("/parent/history")
@parent_web_login_required
def parent_history():
	parent, family = _load_parent_and_family()
	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	kids = Kid.query.filter_by(family_id=family.id, is_active=True).order_by(Kid.display_name.asc()).all()

	purchase_history = (
		StoreRedemption.query.filter_by(family_id=family.id)
		.order_by(StoreRedemption.requested_at.desc())
		.all()
	)
	chore_submissions = (
		ChoreSubmission.query.filter_by(family_id=family.id)
		.order_by(ChoreSubmission.claimed_at.desc())
		.all()
	)
	chores = Chore.query.filter_by(family_id=family.id, is_active=True).order_by(Chore.name.asc()).all()

	return render_template(
		"private/parents/history/index.html",
		parent=parent,
		family=family,
		kids=kids,
		purchase_history=purchase_history,
		chore_submissions=chore_submissions,
		chores=chores,
		game_sessions=[],
	)


@public_bp.post("/parent/add-kid")
@parent_web_login_required
def parent_add_kid():
	display_name = request.form.get("display_name", "").strip()
	pin = request.form.get("pin", "").strip()

	# Tier limit check
	_fam = Family.query.get(session["family_id"])
	if _fam:
		_current = Kid.query.filter_by(family_id=_fam.id, is_active=True).count()
		if not can_add(_fam, "kids", _current):
			flash(limit_reached_message("kids"), "warning")
			return redirect(url_for("public.parent_dashboard"))

	if not display_name:
		flash("Kid name is required.", "error")
		return redirect(url_for("public.parent_dashboard"))

	if not pin.isdigit() or len(pin) != 4:
		flash("PIN must be exactly 4 digits.", "error")
		return redirect(url_for("public.parent_dashboard"))

	kid = Kid(family_id=session["family_id"], display_name=display_name)
	kid.set_pin(pin)
	db.session.add(kid)
	db.session.commit()

	flash(f"Added {display_name}.", "success")
	return redirect(url_for("public.parent_dashboard"))


@public_bp.post("/parent/rotate-family-code")
@parent_web_login_required
def parent_rotate_family_code():
	family = Family.query.get(session.get("family_id"))
	if not family:
		flash("Family not found.", "error")
		return redirect(url_for("public.parent_dashboard"))

	new_code = generate_family_code()
	family.set_family_code(new_code)
	db.session.commit()

	flash(f"Family code rotated. New code: {new_code}", "success")
	return redirect(url_for("public.parent_dashboard"))


@public_bp.post("/parent/register-device")
@parent_web_login_required
def parent_register_device():
	parent, family = _load_parent_and_family()
	if not parent or not family:
		session.clear()
		return redirect(url_for("public.login"))

	device_label = (request.form.get("device_label") or "").strip()
	if not device_label:
		device_label = "Registered Device"

	trusted_device, plain_device_token = TrustedDevice.create_for_family(
		family_id=family.id,
		parent_id=parent.id,
		device_label=device_label,
		user_agent=(request.headers.get("User-Agent") or "").strip(),
		ip_address=(request.remote_addr or "").strip(),
	)
	db.session.add(trusted_device)
	db.session.commit()

	response = redirect(url_for("public.parent_dashboard"))
	response.set_cookie(
		"family_device_token",
		plain_device_token,
		max_age=90 * 24 * 60 * 60,
		httponly=True,
		samesite="Lax",
	)
	flash(f"Device \"{device_label}\" registered. Kids can now log in here with just their name and PIN.", "success")
	return response


@public_bp.post("/parent/revoke-this-device")
@parent_web_login_required
def parent_revoke_this_device():
	token = (request.cookies.get("family_device_token") or "").strip()
	if not token:
		flash("No trusted device token found on this browser.", "error")
		return redirect(url_for("public.parent_dashboard"))

	device = TrustedDevice.find_valid_by_token(token)
	if not device or device.family_id != session.get("family_id"):
		flash("Current device is not active or was already revoked.", "error")
		return redirect(url_for("public.parent_dashboard"))

	device.revoked_at = db.func.now()
	db.session.commit()

	response = redirect(url_for("public.parent_dashboard"))
	response.delete_cookie("family_device_token")
	flash("This device was revoked successfully.", "success")
	return response


@public_bp.post("/parent/revoke-device/<int:device_id>")
@parent_web_login_required
def parent_revoke_device(device_id: int):
	parent, family = _load_parent_and_family()
	if not parent or not family:
		session.clear()
		return redirect(url_for("public.login"))

	device = TrustedDevice.query.filter_by(id=device_id, family_id=family.id).first()
	if not device:
		flash("Device not found.", "error")
		return redirect(url_for("public.parent_settings"))
	if device.revoked_at:
		flash("Device was already revoked.", "info")
		return redirect(url_for("public.parent_settings"))

	device.revoked_at = db.func.now()
	db.session.commit()

	# If the parent is revoking the device they're currently on, clear its cookie too
	current_token = (request.cookies.get("family_device_token") or "").strip()
	current_device = TrustedDevice.find_valid_by_token(current_token) if current_token else None
	response = redirect(url_for("public.parent_settings"))
	if current_device and current_device.id == device_id:
		response.delete_cookie("family_device_token")
	flash(f'"{device.device_label}" has been revoked.', "success")
	return response


@public_bp.post("/parent/logout")
def parent_logout():
	session.clear()
	response = redirect(url_for("public.login"))
	flash("You are logged out.", "success")
	return response


@public_bp.post("/parent/switch-to-kid/<int:kid_id>")
@parent_web_login_required
def parent_switch_to_kid(kid_id: int):
	parent, family = _load_parent_and_family()
	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	kid = Kid.query.get(kid_id)
	if not kid or kid.family_id != family.id or not kid.is_active:
		flash("Kid not found.", "error")
		return redirect(url_for("public.parent_dashboard"))

	# Save parent context so we can return to it
	session["impersonating_parent_id"] = parent.id
	session["impersonating_parent_family_id"] = family.id

	# Switch to kid session
	session["role"] = "kid"
	session["kid_id"] = kid.id
	session["family_id"] = family.id

	flash(f"You're now viewing as {kid.display_name}. Tap 'Return to Parent' to go back.", "info")
	return redirect(url_for("public.kid_chores"))


@public_bp.post("/parent/switch-back")
def parent_switch_back():
	parent_id = session.get("impersonating_parent_id")
	family_id = session.get("impersonating_parent_family_id")

	if not parent_id or not family_id:
		flash("No parent session to return to.", "error")
		return redirect(url_for("public.login"))

	parent = Parent.query.get(parent_id)
	if not parent:
		session.clear()
		flash("Parent account not found. Please log in again.", "error")
		return redirect(url_for("public.login"))

	# Restore parent session, clearing kid + impersonation keys
	session["role"] = "parent"
	session["parent_id"] = parent.id
	session["family_id"] = family_id
	session.pop("kid_id", None)
	session.pop("impersonating_parent_id", None)
	session.pop("impersonating_parent_family_id", None)

	flash(f"Welcome back, {parent.name}!", "success")
	return redirect(url_for("public.parent_dashboard"))


# ── QR-code device registration ──────────────────────────────────────────────

@public_bp.post("/device/qr-init")
def device_qr_init():
	"""Kid's browser calls this to get a fresh registration token for the QR code."""
	# Clean up stale expired records occasionally
	try:
		db.session.query(PendingDeviceRegistration).filter(
			PendingDeviceRegistration.expires_at < datetime.utcnow()
		).delete()
		db.session.commit()
	except Exception:
		db.session.rollback()

	rec, plain_token = PendingDeviceRegistration.create()
	db.session.add(rec)
	db.session.commit()
	return jsonify({
		"token": plain_token,
		"expires_in": PendingDeviceRegistration.TTL_SECONDS,
	})


@public_bp.get("/device/qr-status/<token>")
def device_qr_status(token: str):
	"""Kid's browser polls this to find out if a parent has confirmed."""
	rec = PendingDeviceRegistration.find_valid(token)
	if rec is None:
		return jsonify({"status": "expired"})
	if rec.confirmed_at and rec.confirmed_device_token:
		return jsonify({"status": "confirmed"})
	return jsonify({"status": "pending"})


@public_bp.get("/device/qr-confirm/<token>")
def device_qr_confirm_page(token: str):
	"""Parent opens this URL (scanned from QR). Must be logged in as a parent."""
	rec = PendingDeviceRegistration.find_valid(token)
	if rec is None:
		return render_template("public/auth/device_qr_expired.html"), 410
	if rec.confirmed_at:
		return render_template("public/auth/device_qr_already_confirmed.html"), 200

	parent_id = session.get("parent_id")
	if not parent_id:
		# Store token in session so we can return after login
		session["qr_confirm_token"] = token
		flash("Please log in as a parent to register this device.", "info")
		return redirect(url_for("public.login"))

	parent, family = _load_parent_and_family()
	if not parent or not family:
		session["qr_confirm_token"] = token
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	return render_template(
		"public/auth/device_qr_confirm.html",
		token=token,
		family=family,
	)


@public_bp.post("/device/qr-confirm/<token>")
def device_qr_confirm_submit(token: str):
	"""Parent submits the confirmation form — creates the TrustedDevice."""
	parent_id = session.get("parent_id")
	if not parent_id:
		flash("You must be logged in as a parent to register a device.", "error")
		return redirect(url_for("public.login"))

	parent, family = _load_parent_and_family()
	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	rec = PendingDeviceRegistration.find_valid(token)
	if rec is None:
		flash("This QR code has expired. Please ask the kid's device to refresh and show a new QR code.", "error")
		return redirect(url_for("public.parent_dashboard"))
	if rec.confirmed_at:
		flash("This QR code was already used.", "info")
		return redirect(url_for("public.parent_dashboard"))

	device_label = (request.form.get("device_label") or "").strip() or "Kid's Device"

	trusted_device, plain_device_token = TrustedDevice.create_for_family(
		family_id=family.id,
		parent_id=parent.id,
		device_label=device_label,
	)
	db.session.add(trusted_device)

	rec.family_id = family.id
	rec.device_label = device_label
	rec.confirmed_at = datetime.utcnow()
	rec.confirmed_device_token = plain_device_token
	db.session.commit()

	return render_template("public/auth/device_qr_success.html", device_label=device_label)


@public_bp.get("/device/qr-complete/<token>")
def device_qr_complete(token: str):
	"""Kid's browser calls this after polling detects confirmed.
	Sets the TrustedDevice cookie on the kid's device and redirects to login."""
	rec = PendingDeviceRegistration.find_valid(token)
	if rec is None or not rec.confirmed_at or not rec.confirmed_device_token:
		flash("QR registration not found or already used.", "error")
		return redirect(url_for("public.kid_login"))

	plain_device_token = rec.confirmed_device_token
	device_label = rec.device_label or "Kid's Device"

	# Mark consumed so it can't be replayed
	rec.completed_at = datetime.utcnow()
	rec.confirmed_device_token = None  # clear plaintext token
	db.session.commit()

	response = redirect(url_for("public.kid_login"))
	response.set_cookie(
		"family_device_token",
		plain_device_token,
		max_age=90 * 24 * 60 * 60,
		httponly=True,
		samesite="Lax",
	)
	flash(f"✅ Device \"{device_label}\" registered! Kids can now log in here with just their name and PIN.", "success")
	return response


@public_bp.get("/kid/login")
def kid_login():
	device_token = (request.cookies.get("family_device_token") or "").strip()
	device = TrustedDevice.find_valid_by_token(device_token) if device_token else None
	if not device:
		device = TrustedDevice.find_valid_by_fingerprint(
			(request.headers.get("User-Agent") or "").strip(),
			(request.remote_addr or "").strip(),
		)
	kids = []
	if device:
		kids = Kid.query.filter_by(family_id=device.family_id, is_active=True).order_by(Kid.display_name.asc()).all()
	return render_template("public/auth/kid_login.html", device=device, kids=kids)


@public_bp.post("/kid/login")
def kid_login_submit():
	pin = (request.form.get("pin") or "").strip()
	kid_id_raw = (request.form.get("kid_id") or "").strip()

	if not pin:
		flash("PIN is required.", "error")
		return redirect(url_for("public.kid_login"))

	# --- Trusted device path (no family code needed) ---
	device_token = (request.cookies.get("family_device_token") or "").strip()
	device = TrustedDevice.find_valid_by_token(device_token) if device_token else None
	if not device:
		device = TrustedDevice.find_valid_by_fingerprint(
			(request.headers.get("User-Agent") or "").strip(),
			(request.remote_addr or "").strip(),
		)

	if device:
		family = Family.query.get(device.family_id)
		if not family:
			flash("Device family not found.", "error")
			return redirect(url_for("public.kid_login"))
		device.last_seen_at = datetime.utcnow()
	else:
		# --- Full path: family code required ---
		family_code = (request.form.get("family_code") or "").strip()
		if not family_code:
			flash("Family code and PIN are required.", "error")
			return redirect(url_for("public.kid_login"))
		family = _find_family_by_code(family_code)
		if not family:
			flash("Family code was not found.", "error")
			return redirect(url_for("public.kid_login"))

	kid_query = Kid.query.filter_by(family_id=family.id, is_active=True)
	authenticated_kid = None

	if kid_id_raw:
		try:
			kid_id = int(kid_id_raw)
		except ValueError:
			flash("Please choose a valid kid.", "error")
			return redirect(url_for("public.kid_login"))
		candidate = kid_query.filter_by(id=kid_id).first()
		if candidate and candidate.verify_pin(pin):
			authenticated_kid = candidate
	else:
		for candidate in kid_query.order_by(Kid.display_name.asc()).all():
			if candidate.verify_pin(pin):
				authenticated_kid = candidate
				break

	if not authenticated_kid:
		flash("Name or PIN is not valid.", "error")
		return redirect(url_for("public.kid_login"))

	db.session.commit()

	session.clear()
	session["role"] = "kid"
	session["kid_id"] = authenticated_kid.id
	session["family_id"] = family.id

	flash(f"Welcome, {authenticated_kid.display_name}!", "success")
	return redirect(url_for("public.kid_chores"))


@public_bp.get("/kid/store")
@kid_web_login_required
def kid_store():
	kid, family = _load_kid_and_family()

	if not kid or not family or kid.family_id != family.id:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.kid_login"))

	active_tab = request.args.get("tab", "kid")
	if active_tab not in {"kid", "family"}:
		active_tab = "kid"

	kid_items = (
		StoreItem.query.filter_by(family_id=family.id, item_scope="kid", is_active=True)
		.order_by(StoreItem.created_at.desc())
		.all()
	)
	family_items = (
		StoreItem.query.filter_by(family_id=family.id, item_scope="family", is_active=True)
		.order_by(StoreItem.created_at.desc())
		.all()
	)

	family_redemptions = (
		StoreRedemption.query.join(StoreItem, StoreRedemption.store_item_id == StoreItem.id)
		.filter(StoreRedemption.family_id == family.id, StoreItem.item_scope == "family")
		.order_by(StoreRedemption.requested_at.desc())
		.limit(30)
		.all()
	)
	vote_lookup = {
		vote.redemption_id: vote.vote
		for vote in StoreRedemptionVote.query.filter_by(kid_id=kid.id).all()
	}
	vote_summary = _vote_summary_for_redemptions(family_redemptions)

	active_session = _active_store_session_for_kid(kid.id)
	family_kids = Kid.query.filter_by(family_id=family.id, is_active=True).order_by(Kid.display_name.asc()).all()
	active_session_by_item_id = _active_store_sessions_by_item(family.id)
	billing_changed = False
	for timed_session in active_session_by_item_id.values():
		billing_changed = _sync_active_store_session_billing(timed_session) or billing_changed
	if billing_changed:
		db.session.commit()
	active_session_elapsed_seconds = {
		active_session.id: _participant_elapsed_seconds(active_session)
		for active_session in active_session_by_item_id.values()
	}
	active_session_charged_coins = {}
	for active_store_session in active_session_by_item_id.values():
		charged_by_participant = {}
		for turn in active_store_session.turns or []:
			charged_by_participant[turn.participant_id] = charged_by_participant.get(turn.participant_id, 0) + (turn.coins_charged or 0)
		active_session_charged_coins[active_store_session.id] = charged_by_participant
	recent_timed_sessions = (
		StoreTimedSession.query.filter(
			StoreTimedSession.family_id == family.id,
			StoreTimedSession.status.in_(["completed", "cancelled"]),
		)
		.order_by(StoreTimedSession.ended_at.desc())
		.limit(8)
		.all()
	)

	return render_template(
		"private/kids/store/index.html",
		kid=kid,
		family=family,
		family_kids=family_kids,
		kid_items=kid_items,
		family_items=family_items,
		family_redemptions=family_redemptions,
		vote_lookup=vote_lookup,
		vote_summary=vote_summary,
		active_tab=active_tab,
		active_session=active_session,
		active_session_by_item_id=active_session_by_item_id,
		active_session_elapsed_seconds=active_session_elapsed_seconds,
		active_session_charged_coins=active_session_charged_coins,
		recent_timed_sessions=recent_timed_sessions,
	)


@public_bp.get("/kid/chores")
@kid_web_login_required
def kid_chores():
	kid, family = _load_kid_and_family()

	if not kid or not family or kid.family_id != family.id:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.kid_login"))

	_run_daily_chore_reset(family)

	chores = (
		Chore.query.filter_by(family_id=family.id, is_active=True)
		.order_by(Chore.created_at.desc())
		.all()
	)
	active_claims_raw = (
		ChoreSubmission.query.filter(
			ChoreSubmission.family_id == family.id,
			ChoreSubmission.kid_id == kid.id,
			ChoreSubmission.status.in_(["claimed", "submitted"]),
		)
		.order_by(ChoreSubmission.claimed_at.desc())
		.all()
	)
	active_claims = [claim for claim in active_claims_raw if claim.reset_version == claim.chore.daily_reset_version]
	active_claim_by_chore_id = {claim.chore_id: claim for claim in active_claims}

	open_claims_raw = (
		ChoreSubmission.query.filter(
			ChoreSubmission.family_id == family.id,
			ChoreSubmission.status.in_(["claimed", "submitted"]),
		)
		.order_by(ChoreSubmission.claimed_at.desc())
		.all()
	)
	open_claims = [claim for claim in open_claims_raw if claim.reset_version == claim.chore.daily_reset_version]
	open_claim_by_chore_id = {claim.chore_id: claim for claim in open_claims}
	remaining_slots_by_chore_id = {chore.id: _remaining_claim_slots_for_today(chore) for chore in chores}
	locked_chore_ids = {chore.id for chore in chores if _is_chore_locked_today(chore)}

	return render_template(
		"private/kids/chores/index.html",
		kid=kid,
		family=family,
		chores=chores,
		active_claims=active_claims,
		active_claim_by_chore_id=active_claim_by_chore_id,
		open_claim_by_chore_id=open_claim_by_chore_id,
		remaining_slots_by_chore_id=remaining_slots_by_chore_id,
		locked_chore_ids=locked_chore_ids,
	)


@public_bp.post("/kid/chores/<int:chore_id>/claim")
@kid_web_login_required
def kid_claim_chore(chore_id: int):
	kid = Kid.query.get(session.get("kid_id"))
	chore = Chore.query.get(chore_id)
	before_file = request.files.get("before_photo")

	if not kid or kid.family_id != session.get("family_id"):
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.kid_login"))

	if not chore or chore.family_id != kid.family_id or not chore.is_active:
		flash("Chore not available.", "error")
		return redirect(url_for("public.kid_chores"))

	if _is_chore_locked_today(chore):
		flash("This chore is already done for today. Ask a parent to reset it.", "error")
		return redirect(url_for("public.kid_chores"))

	if _remaining_claim_slots_for_today(chore) <= 0:
		flash("No open slots remain for this chore today.", "error")
		return redirect(url_for("public.kid_chores"))

	if chore.requires_photo_proof and (not before_file or not before_file.filename):
		flash("Take a before photo when claiming this chore.", "error")
		return redirect(url_for("public.kid_chores"))

	existing_claim = _active_chore_submission_for_chore(chore)
	if existing_claim and existing_claim.kid_id == kid.id:
		flash("You already claimed this chore.", "info")
		return redirect(url_for("public.kid_chores"))

	existing_kid_submission_today = ChoreSubmission.query.filter(
		ChoreSubmission.chore_id == chore.id,
		ChoreSubmission.kid_id == kid.id,
		ChoreSubmission.reset_version == chore.daily_reset_version,
		db.func.date(ChoreSubmission.claimed_at) == date.today().isoformat(),
		ChoreSubmission.status.in_(["claimed", "submitted", "approved"]),
	).first()
	if existing_kid_submission_today:
		flash("You already worked on this chore today.", "error")
		return redirect(url_for("public.kid_chores"))

	before_path = None
	if before_file and before_file.filename:
		before_path = _save_chore_photo(before_file, kid.family_id, kid.id, "before")
		if not before_path:
			return redirect(url_for("public.kid_chores"))

	submission = ChoreSubmission(
		chore_id=chore.id,
		family_id=kid.family_id,
		kid_id=kid.id,
		reset_version=chore.daily_reset_version,
		before_photo_path=before_path,
		status="claimed",
	)
	db.session.add(submission)
	db.session.commit()

	flash(f"You claimed '{chore.name}'. Before photo saved — go do it and come back for the final photo.", "success")
	return redirect(url_for("public.kid_chores"))


@public_bp.post("/kid/chores/submissions/<int:submission_id>/submit")
@kid_web_login_required
def kid_submit_chore(submission_id: int):
	kid = Kid.query.get(session.get("kid_id"))
	submission = ChoreSubmission.query.get(submission_id)

	if not kid or kid.family_id != session.get("family_id"):
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.kid_login"))

	if not submission or submission.family_id != kid.family_id or submission.kid_id != kid.id:
		flash("Submission not found.", "error")
		return redirect(url_for("public.kid_chores"))

	if submission.status != "claimed":
		flash("Only claimed chores can be submitted.", "error")
		return redirect(url_for("public.kid_chores"))

	before_file = request.files.get("before_photo")
	after_file = request.files.get("after_photo")

	if submission.chore.requires_photo_proof:
		if not submission.before_photo_path and (not before_file or not before_file.filename):
			flash("Before photo is required before final submission.", "error")
			return redirect(url_for("public.kid_chores"))
		if not after_file or not after_file.filename:
			flash("After photo is required for this chore.", "error")
			return redirect(url_for("public.kid_chores"))

	if before_file and before_file.filename:
		before_path = _save_chore_photo(before_file, kid.family_id, kid.id, "before")
		if not before_path:
			return redirect(url_for("public.kid_chores"))
		submission.before_photo_path = before_path

	after_path = None
	if after_file and after_file.filename:
		after_path = _save_chore_photo(after_file, kid.family_id, kid.id, "after")
	if after_file and after_file.filename and not after_path:
		return redirect(url_for("public.kid_chores"))

	if after_path:
		submission.after_photo_path = after_path

	if submission.chore.requires_photo_proof and (not submission.before_photo_path or not submission.after_photo_path):
		flash("Both before and after photos are required for this chore.", "error")
		return redirect(url_for("public.kid_chores"))

	submission.status = "submitted"
	submission.submitted_at = datetime.utcnow()
	db.session.commit()

	flash(f"Submitted '{submission.chore.name}' for parent approval.", "success")
	return redirect(url_for("public.kid_chores"))


# ── KID CHALLENGES ─────────────────────────────────────────────────────────────

@public_bp.get("/kid/challenges")
@kid_web_login_required
def kid_challenges():
	kid, family = _load_kid_and_family()
	if not kid or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.kid_login"))

	challenges = Challenge.query.filter_by(family_id=family.id, is_active=True).order_by(Challenge.created_at.desc()).all()

	# Find submissions for this kid
	my_submissions = (
		ChallengeSubmission.query.filter_by(family_id=family.id, kid_id=kid.id)
		.order_by(ChallengeSubmission.claimed_at.desc())
		.all()
	)
	# Map challenge_id -> latest submission
	my_sub_by_challenge = {}
	for sub in my_submissions:
		if sub.challenge_id not in my_sub_by_challenge:
			my_sub_by_challenge[sub.challenge_id] = sub

	return render_template(
		"private/kids/challenges/index.html",
		kid=kid,
		family=family,
		challenges=challenges,
		my_sub_by_challenge=my_sub_by_challenge,
	)


@public_bp.post("/kid/challenges/<int:challenge_id>/claim")
@kid_web_login_required
def kid_claim_challenge(challenge_id: int):
	kid = Kid.query.get(session.get("kid_id"))
	challenge = Challenge.query.get(challenge_id)

	if not kid or kid.family_id != session.get("family_id"):
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.kid_login"))

	if not challenge or challenge.family_id != kid.family_id or not challenge.is_active:
		flash("Challenge not available.", "error")
		return redirect(url_for("public.kid_challenges"))

	# Check if already has an active submission (unless repeatable & no open one)
	existing = ChallengeSubmission.query.filter(
		ChallengeSubmission.challenge_id == challenge_id,
		ChallengeSubmission.kid_id == kid.id,
		ChallengeSubmission.status.in_(["claimed", "submitted"]),
	).first()
	if existing:
		flash("You already have this challenge in progress!", "info")
		return redirect(url_for("public.kid_challenges"))

	submission = ChallengeSubmission(
		challenge_id=challenge_id,
		family_id=kid.family_id,
		kid_id=kid.id,
		status="claimed",
	)
	db.session.add(submission)
	db.session.commit()
	flash(f"You picked up the '{challenge.title}' challenge! Submit it when done.", "success")
	return redirect(url_for("public.kid_challenges"))


@public_bp.post("/kid/challenges/submissions/<int:submission_id>/submit")
@kid_web_login_required
def kid_submit_challenge(submission_id: int):
	kid = Kid.query.get(session.get("kid_id"))
	submission = ChallengeSubmission.query.get(submission_id)

	if not kid or kid.family_id != session.get("family_id"):
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.kid_login"))

	if not submission or submission.kid_id != kid.id:
		flash("Submission not found.", "error")
		return redirect(url_for("public.kid_challenges"))

	if submission.status != "claimed":
		flash("This challenge is already submitted or resolved.", "info")
		return redirect(url_for("public.kid_challenges"))

	proof_note = (request.form.get("proof_note") or "").strip()

	# Handle optional proof photo
	proof_file = request.files.get("proof_photo")
	proof_path = None
	if proof_file and proof_file.filename:
		upload_folder = os.path.join(current_app.instance_path, "uploads", "challenge_photos")
		os.makedirs(upload_folder, exist_ok=True)
		ext = os.path.splitext(secure_filename(proof_file.filename))[1].lower()
		filename = f"challenge_{submission.id}_{secrets.token_hex(6)}{ext}"
		proof_file.save(os.path.join(upload_folder, filename))
		proof_path = filename

	if submission.challenge.requires_proof and not proof_note and not proof_path:
		flash("This challenge requires a note or photo as proof.", "error")
		return redirect(url_for("public.kid_challenges"))

	submission.proof_note = proof_note or None
	submission.proof_photo_path = proof_path
	submission.status = "submitted"
	submission.submitted_at = datetime.utcnow()
	db.session.commit()

	flash(f"'{submission.challenge.title}' submitted for parent approval! 🎉", "success")
	return redirect(url_for("public.kid_challenges"))


@public_bp.post("/kid/store/cash-out")
@kid_web_login_required
def kid_cash_out_coins():
	kid = Kid.query.get(session.get("kid_id"))
	if not kid or kid.family_id != session.get("family_id"):
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.kid_login"))

	try:
		coins = int(request.form.get("coins", 0))
	except (ValueError, TypeError):
		flash("Invalid coin amount.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	family = Family.query.get(kid.family_id)
	rate = (family.coins_per_dollar if family and family.coins_per_dollar else 10)

	if coins <= 0 or coins % rate != 0:
		flash(f"Coin amount must be a positive multiple of {rate}.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	if kid.coin_balance < coins:
		flash("You don't have enough coins.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	dollars = coins / rate
	kid.coin_balance -= coins
	db.session.add(CoinTransaction(
		kid_id=kid.id,
		family_id=kid.family_id,
		amount=-coins,
		kind="cash_out",
		reason=f"Cash out: {coins} coins = ${dollars:.2f}",
	))
	db.session.commit()
	flash(f'Cashed out {coins} coins for ${dollars:.2f}. Ask a parent to pay you out!', "success")
	return redirect(url_for("public.kid_store", tab="kid"))


@public_bp.post("/kid/store/items/<int:item_id>/purchase")
@kid_web_login_required
def kid_purchase_store_item(item_id: int):
	kid = Kid.query.get(session.get("kid_id"))
	item = StoreItem.query.get(item_id)

	if not kid or kid.family_id != session.get("family_id"):
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.kid_login"))

	if not item or item.family_id != kid.family_id or not item.is_active or item.item_scope != "kid" or item.item_type != "basic":
		flash("Store item not found.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	if item.stock_qty == 0:
		flash("This item is out of stock.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	raw_split_ids = request.form.getlist("split_kid_ids")
	split_participant_ids = [kid.id]
	for raw_kid_id in raw_split_ids:
		try:
			split_kid_id = int(raw_kid_id)
		except (TypeError, ValueError):
			continue
		if split_kid_id != kid.id and split_kid_id not in split_participant_ids:
			split_participant_ids.append(split_kid_id)

	participant_kids = Kid.query.filter(
		Kid.family_id == kid.family_id,
		Kid.id.in_(split_participant_ids),
		Kid.is_active.is_(True),
	).all()
	participant_ids_found = {participant.id for participant in participant_kids}
	if participant_ids_found != set(split_participant_ids):
		flash("One or more split participants are invalid.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	coin_shares = _split_coin_shares(
		total_coins=item.kid_coin_cost,
		participant_kid_ids=split_participant_ids,
		primary_kid_id=kid.id,
	)
	if not coin_shares:
		flash("Unable to split this purchase.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	insufficient = [
		participant.display_name
		for participant in participant_kids
		if participant.coin_balance < coin_shares.get(participant.id, 0)
	]
	if insufficient:
		flash(f"Not enough coins for split purchase: {', '.join(insufficient)}.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	if item.require_parent_approval:
		existing_pending = StoreRedemption.query.filter_by(
			store_item_id=item.id,
			family_id=kid.family_id,
			requested_by_kid_id=kid.id,
			status="pending",
		).first()
		if existing_pending:
			flash("You already have a pending request for this item.", "info")
			return redirect(url_for("public.kid_store", tab="kid"))

		redemption = StoreRedemption(
			store_item_id=item.id,
			family_id=kid.family_id,
			requested_by_kid_id=kid.id,
			status="pending",
		)
		db.session.add(redemption)
		db.session.flush()
		for participant in participant_kids:
			db.session.add(StoreRedemptionParticipant(
				redemption_id=redemption.id,
				kid_id=participant.id,
				coin_share=coin_shares.get(participant.id, 0),
			))
		db.session.commit()
		if len(participant_kids) > 1:
			flash(f'Requested split purchase approval for "{item.name}".', "success")
		else:
			flash(f'Requested purchase approval for "{item.name}".', "success")
		return redirect(url_for("public.kid_store", tab="kid"))

	for participant in participant_kids:
		participant.coin_balance -= coin_shares.get(participant.id, 0)

	if item.stock_qty > 0:
		item.stock_qty -= 1

	redemption = StoreRedemption(
		store_item_id=item.id,
		family_id=kid.family_id,
		requested_by_kid_id=kid.id,
		status="fulfilled",
		resolved_at=datetime.utcnow(),
	)
	db.session.add(redemption)
	db.session.flush()
	for participant in participant_kids:
		share = coin_shares.get(participant.id, 0)
		db.session.add(StoreRedemptionParticipant(
			redemption_id=redemption.id,
			kid_id=participant.id,
			coin_share=share,
		))
		tx_reason = f"Store purchase: {item.name}" if len(participant_kids) == 1 else f"Store split purchase: {item.name}"
		db.session.add(CoinTransaction(
			kid_id=participant.id,
			family_id=participant.family_id,
			amount=-share,
			kind="store_purchase",
			reason=tx_reason,
			ref_type="store_redemption",
			ref_id=redemption.id,
		))
	db.session.commit()

	if len(participant_kids) > 1:
		flash(f'Purchased "{item.name}" as a split purchase with {len(participant_kids)} kids.', "success")
	else:
		flash(f'Purchased "{item.name}" for {item.kid_coin_cost} coins.', "success")
	return redirect(url_for("public.kid_store", tab="kid"))


@public_bp.post("/kid/store/family/request")
@kid_web_login_required
def kid_request_family_goal():
	kid = Kid.query.get(session.get("kid_id"))
	item_id_raw = (request.form.get("item_id") or "").strip()

	if not kid or kid.family_id != session.get("family_id"):
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.kid_login"))

	try:
		item_id = int(item_id_raw)
	except ValueError:
		flash("Please choose a valid family goal.", "error")
		return redirect(url_for("public.kid_store", tab="family"))

	item = StoreItem.query.get(item_id)
	if not item or item.family_id != kid.family_id or not item.is_active or item.item_scope != "family":
		flash("Family goal not found.", "error")
		return redirect(url_for("public.kid_store", tab="family"))

	redemption = StoreRedemption(
		store_item_id=item.id,
		family_id=kid.family_id,
		requested_by_kid_id=kid.id,
		status="pending",
	)
	db.session.add(redemption)
	db.session.commit()

	flash(f'Requested family goal "{item.name}".', "success")
	return redirect(url_for("public.kid_store", tab="family"))


@public_bp.post("/kid/store/family/redemptions/<int:redemption_id>/vote")
@kid_web_login_required
def kid_vote_family_goal(redemption_id: int):
	kid = Kid.query.get(session.get("kid_id"))
	vote_value = (request.form.get("vote") or "").strip().lower()

	if vote_value not in {"yes", "no"}:
		flash("Invalid vote option.", "error")
		return redirect(url_for("public.kid_store", tab="family"))

	if not kid or kid.family_id != session.get("family_id"):
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.kid_login"))

	redemption = StoreRedemption.query.get(redemption_id)
	if not redemption or redemption.family_id != kid.family_id:
		flash("Family goal request not found.", "error")
		return redirect(url_for("public.kid_store", tab="family"))

	item = redemption.store_item
	if not item or item.item_scope != "family":
		flash("Family goal request not found.", "error")
		return redirect(url_for("public.kid_store", tab="family"))

	if redemption.status != "pending":
		flash("Voting is only available while pending.", "error")
		return redirect(url_for("public.kid_store", tab="family"))

	vote = StoreRedemptionVote.query.filter_by(redemption_id=redemption.id, kid_id=kid.id).first()
	if vote is None:
		vote = StoreRedemptionVote(redemption_id=redemption.id, kid_id=kid.id, vote=vote_value)
		db.session.add(vote)
	else:
		vote.vote = vote_value

	db.session.commit()
	flash(f"Your vote was recorded: {vote_value.upper()}.", "success")
	return redirect(url_for("public.kid_store", tab="family"))


# ── Timed Store Sessions ──────────────────────────────────────────────────────

@public_bp.get("/kid/store/sessions/new/<int:item_id>")
@kid_web_login_required
def kid_store_session_setup(item_id: int):
	flash("Start turns directly from the timer card now.", "info")
	return redirect(url_for("public.kid_store", tab="kid"))


@public_bp.post("/kid/store/sessions/new/<int:item_id>")
@kid_web_login_required
def kid_store_session_setup_submit(item_id: int):
	flash("Start turns directly from the timer card now.", "info")
	return redirect(url_for("public.kid_store", tab="kid"))

@public_bp.post("/kid/store/sessions/start")
@kid_web_login_required
def kid_start_store_session():
	kid = Kid.query.get(session.get("kid_id"))
	item_id_raw = (request.form.get("item_id") or "").strip()
	joined_kid_ids_raw = request.form.getlist("joined_kid_ids")
	guest_names_raw = request.form.getlist("guest_names")
	legacy_guest_name = (request.form.get("guest_name") or "").strip()
	parent_password = (request.form.get("parent_password") or "").strip()
	first_turn_raw = (request.form.get("first_turn") or "").strip()

	if not kid or kid.family_id != session.get("family_id"):
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.kid_login"))

	try:
		item_id = int(item_id_raw)
	except ValueError:
		flash("Invalid item.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	item = StoreItem.query.get(item_id)
	if not item or item.family_id != kid.family_id or not item.is_active or item.item_scope != "kid" or item.item_type != "timed_session":
		flash("Session item not found.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	if item.stock_qty == 0:
		flash("This session is out of stock.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	if _active_store_session_for_item(kid.family_id, item.id):
		flash("This timer already has a turn running. Stop and commit it first.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	joined_kid_ids = []
	for raw_id in joined_kid_ids_raw:
		try:
			joined_kid_id = int(raw_id)
		except ValueError:
			flash("Choose valid kids for this session.", "error")
			return redirect(url_for("public.kid_store", tab="kid"))
		if joined_kid_id not in joined_kid_ids:
			joined_kid_ids.append(joined_kid_id)

	joined_kids = []
	for joined_kid_id in joined_kid_ids:
		joined_kid = Kid.query.get(joined_kid_id)
		if not joined_kid or joined_kid.family_id != kid.family_id or not joined_kid.is_active:
			flash("Choose valid kids for this session.", "error")
			return redirect(url_for("public.kid_store", tab="kid"))
		if joined_kid.id != kid.id:
			kid_pin = (request.form.get(f"kid_pin_{joined_kid.id}") or "").strip()
			if not kid_pin or not joined_kid.verify_pin(kid_pin):
				flash(f"{joined_kid.display_name}'s PIN is invalid.", "error")
				return redirect(url_for("public.kid_store", tab="kid"))
		if _active_store_session_for_kid(joined_kid.id):
			flash(f"{joined_kid.display_name} already has a session running.", "error")
			return redirect(url_for("public.kid_store", tab="kid"))
		joined_kids.append(joined_kid)

	guest_names = []
	for raw_guest_name in guest_names_raw:
		guest_name = (raw_guest_name or "").strip()
		if guest_name:
			guest_names.append(guest_name[:120])
	if legacy_guest_name and not guest_names:
		guest_names.append(legacy_guest_name[:120])

	guest_requested = bool(guest_names)
	if guest_requested and not _family_parent_password_valid(kid.family_id, parent_password):
		flash("Parent password is required for a guest.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	if not joined_kids and not guest_requested:
		flash("Add at least one player before starting the session.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	if item.stock_qty > 0:
		item.stock_qty -= 1

	timed_session = StoreTimedSession(
		store_item_id=item.id,
		family_id=kid.family_id,
		started_by_kid_id=kid.id,
		status="active",
		timing_mode="stopwatch",
		planned_duration_minutes=None,
		total_coins_charged=0,
	)
	db.session.add(timed_session)
	db.session.flush()

	participants = []
	for joined_kid in joined_kids:
		participant = StoreSessionParticipant(
			timed_session_id=timed_session.id,
			family_id=kid.family_id,
			kid_id=joined_kid.id,
			participant_type="kid",
		)
		db.session.add(participant)
		participants.append(participant)

	guest_participants = []
	for guest_name in guest_names:
		participant = StoreSessionParticipant(
			timed_session_id=timed_session.id,
			family_id=kid.family_id,
			participant_type="guest",
			guest_name=guest_name,
		)
		db.session.add(participant)
		participants.append(participant)
		guest_participants.append(participant)

	db.session.flush()

	first_participant = None
	if first_turn_raw.startswith("kid:"):
		try:
			first_kid_id = int(first_turn_raw.split(":", 1)[1])
		except ValueError:
			first_kid_id = None
		first_participant = next((participant for participant in participants if participant.kid_id == first_kid_id), None)
	elif first_turn_raw.startswith("guest:"):
		try:
			first_guest_index = int(first_turn_raw.split(":", 1)[1])
		except ValueError:
			first_guest_index = None
		if first_guest_index is not None and 0 <= first_guest_index < len(guest_participants):
			first_participant = guest_participants[first_guest_index]
	elif first_turn_raw == "guest":
		first_participant = guest_participants[0] if guest_participants else None

	if first_participant is None:
		first_participant = participants[0]

	first_turn = StoreSessionTurn(
		timed_session_id=timed_session.id,
		participant_id=first_participant.id,
		family_id=kid.family_id,
	)
	db.session.add(first_turn)
	db.session.flush()

	if not _charge_turn_start(first_turn):
		start_cost = _turn_start_cost(timed_session, first_participant)
		db.session.rollback()
		flash(f"{first_participant.display_name} needs at least {start_cost} coin{'s' if start_cost != 1 else ''} to start a turn.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	db.session.commit()

	flash(f'"{item.name}" session started.', "success")
	return redirect(url_for("public.kid_store", tab="kid"))


@public_bp.post("/kid/store/sessions/<int:timed_session_id>/switch")
@kid_web_login_required
def kid_switch_store_session_turn(timed_session_id: int):
	kid = Kid.query.get(session.get("kid_id"))
	timed_session = StoreTimedSession.query.get(timed_session_id)
	participant_id_raw = (request.form.get("participant_id") or "").strip()

	if not kid or kid.family_id != session.get("family_id"):
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.kid_login"))

	if not timed_session or timed_session.family_id != kid.family_id:
		flash("Session not found.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	if timed_session.status != "active":
		flash("This session is already ended.", "info")
		return redirect(url_for("public.kid_store", tab="kid"))

	_sync_active_store_session_billing(timed_session)

	try:
		participant_id = int(participant_id_raw)
	except ValueError:
		flash("Choose a player for the next turn.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	next_participant = StoreSessionParticipant.query.get(participant_id)
	if not next_participant or next_participant.timed_session_id != timed_session.id:
		flash("That player is not part of this session.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	start_cost = _turn_start_cost(timed_session, next_participant)
	if (
		next_participant.charges_coins
		and next_participant.kid.coin_balance < start_cost
	):
		db.session.commit()
		flash(f"{next_participant.display_name} needs at least {start_cost} coin{'s' if start_cost != 1 else ''} to start a turn.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	current_turn = timed_session.current_turn
	if current_turn and current_turn.participant_id == next_participant.id:
		db.session.commit()
		flash(f"{next_participant.display_name} is already taking a turn.", "info")
		return redirect(url_for("public.kid_store", tab="kid"))

	now = datetime.utcnow()
	if current_turn:
		_close_store_session_turn(current_turn, now)

	next_turn = StoreSessionTurn(
		timed_session_id=timed_session.id,
		participant_id=next_participant.id,
		family_id=timed_session.family_id,
		started_at=now,
	)
	db.session.add(next_turn)
	db.session.flush()

	if not _charge_turn_start(next_turn):
		db.session.rollback()
		flash(f"{next_participant.display_name} needs at least {start_cost} coin{'s' if start_cost != 1 else ''} to start a turn.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	db.session.commit()

	flash(f"Switched to {next_participant.display_name}.", "success")
	return redirect(url_for("public.kid_store", tab="kid"))


@public_bp.post("/kid/store/sessions/<int:timed_session_id>/end")
@kid_web_login_required
def kid_end_store_session(timed_session_id: int):
	kid = Kid.query.get(session.get("kid_id"))
	timed_session = StoreTimedSession.query.get(timed_session_id)

	if not kid or kid.family_id != session.get("family_id"):
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.kid_login"))

	if (
		not timed_session
		or timed_session.family_id != kid.family_id
	):
		flash("Session not found.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	if timed_session.status != "active":
		flash("This session is already ended.", "info")
		return redirect(url_for("public.kid_store", tab="kid"))

	_sync_active_store_session_billing(timed_session)

	now = datetime.utcnow()
	current_turn = timed_session.current_turn
	if current_turn:
		_close_store_session_turn(current_turn, now)

	timed_session.ended_at = now
	timed_session.status = "completed"
	charge_summary = _charge_shared_store_session(timed_session)

	db.session.commit()
	charged_parts = [
		f"{entry['name']}: {entry['coins']} coin{'s' if entry['coins'] != 1 else ''}"
		for entry in charge_summary
		if entry["coins"] > 0
	]
	if charged_parts:
		flash(f"Session ended. {'; '.join(charged_parts)}.", "success")
	else:
		flash("Session ended. No coins charged.", "success")
	return redirect(url_for("public.kid_store", tab="kid"))


@public_bp.get("/kid/store/sessions/<int:timed_session_id>/status")
@kid_web_login_required
def kid_store_session_status(timed_session_id: int):
	kid = Kid.query.get(session.get("kid_id"))
	timed_session = StoreTimedSession.query.get(timed_session_id)

	if not kid or not timed_session or timed_session.family_id != kid.family_id:
		return jsonify({"error": "Not found"}), 404

	changed = _sync_active_store_session_billing(timed_session)
	if changed:
		db.session.commit()

	item = timed_session.store_item
	current_turn = timed_session.current_turn
	elapsed_by_participant = _participant_elapsed_seconds(timed_session)
	charged_by_participant = {}
	for turn in timed_session.turns or []:
		charged_by_participant[turn.participant_id] = charged_by_participant.get(turn.participant_id, 0) + (turn.coins_charged or 0)
	current_turn_paid_seconds = (_turn_paid_minutes(current_turn) * 60) if current_turn else 0
	return jsonify({
		"session_id": timed_session.id,
		"status": timed_session.status,
		"started_by_kid_id": timed_session.started_by_kid_id,
		"started_by_kid_name": timed_session.started_by_kid.display_name if timed_session.started_by_kid else None,
		"timing_mode": timed_session.timing_mode,
		"elapsed_seconds": timed_session.elapsed_seconds,
		"current_turn_id": current_turn.id if current_turn else None,
		"current_participant_id": current_turn.participant_id if current_turn else None,
		"current_participant_name": current_turn.participant.display_name if current_turn and current_turn.participant else None,
		"current_turn_elapsed_seconds": current_turn.live_elapsed_seconds if current_turn else 0,
		"current_turn_paid_seconds": current_turn_paid_seconds,
		"participant_elapsed_seconds": elapsed_by_participant,
		"participant_charged_coins": charged_by_participant,
		"planned_duration_minutes": timed_session.planned_duration_minutes,
		"remaining_seconds": timed_session.remaining_seconds,
		"total_coins_charged": timed_session.total_coins_charged,
		"session_rate_type": item.session_rate_type if item else None,
		"session_coin_per_minute": item.session_coin_per_minute if item else 0,
	})


@public_bp.post("/kid/logout")
def kid_logout_web():
	session.clear()
	flash("You are logged out.", "success")
	return redirect(url_for("public.kid_login"))


# ── Settings ──────────────────────────────────────────────────────────────────

@public_bp.post("/parent/settings/coin-rate")
@parent_web_login_required
def parent_settings_update_coin_rate():
	parent, family = _load_parent_and_family()
	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))
	try:
		rate = int(request.form.get("coins_per_dollar", 10))
	except (ValueError, TypeError):
		flash("Invalid exchange rate.", "error")
		return redirect(url_for("public.parent_settings"))
	if rate < 1 or rate > 1000:
		flash("Exchange rate must be between 1 and 1000 coins per dollar.", "error")
		return redirect(url_for("public.parent_settings"))
	family.coins_per_dollar = rate
	db.session.commit()
	flash(f"Cash-out rate updated: {rate} coins = $1.", "success")
	return redirect(url_for("public.parent_settings"))


@public_bp.get("/parent/settings")
@parent_web_login_required
def parent_settings():
	parent, family = _load_parent_and_family()
	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	kids = Kid.query.filter_by(family_id=family.id, is_active=True).order_by(Kid.created_at.asc()).all()
	co_guardians = Parent.query.filter(
		Parent.family_id == family.id,
		Parent.id != parent.id,
	).order_by(Parent.created_at.asc()).all()
	pending_requests = (
		GuardianJoinRequest.query
		.filter_by(family_id=family.id, status="pending")
		.order_by(GuardianJoinRequest.created_at.asc())
		.all()
	)

	now = datetime.utcnow()
	active_devices = TrustedDevice.query.filter(
		TrustedDevice.family_id == family.id,
		TrustedDevice.revoked_at.is_(None),
		TrustedDevice.expires_at > now,
	).order_by(TrustedDevice.last_seen_at.desc()).all()

	return render_template(
		"private/parents/settings/index.html",
		parent=parent,
		family=family,
		kids=kids,
		co_guardians=co_guardians,
		pending_requests=pending_requests,
		active_devices=active_devices,
		starter_chores=[{**c, "already_exists": c["name"] in {ch.name for ch in Chore.query.filter_by(family_id=family.id).all()}} for c in _STARTER_CHORES],
		starter_kid_store=[{**s, "already_exists": s["name"] in {si.name for si in StoreItem.query.filter_by(family_id=family.id).all()}} for s in _STARTER_KID_STORE],
		starter_family_store=[{**s, "already_exists": s["name"] in {si.name for si in StoreItem.query.filter_by(family_id=family.id).all()}} for s in _STARTER_FAMILY_STORE],
		starter_challenges=[{**c, "already_exists": c["title"] in {ch.title for ch in Challenge.query.filter_by(family_id=family.id).all()}} for c in _STARTER_CHALLENGES],
	)


@public_bp.post("/parent/settings/update-profile")
@parent_web_login_required
def parent_update_profile():
	parent, _ = _load_parent_and_family()
	if not parent:
		return redirect(url_for("public.login"))

	name = request.form.get("name", "").strip()
	email = request.form.get("email", "").strip().lower()
	current_password = request.form.get("current_password", "").strip()
	new_password = request.form.get("new_password", "").strip()
	confirm_new_password = request.form.get("confirm_new_password", "").strip()

	if not name or not email:
		flash("Name and email are required.", "error")
		return redirect(url_for("public.parent_settings"))

	if not parent.verify_password(current_password):
		flash("Current password is incorrect.", "error")
		return redirect(url_for("public.parent_settings"))

	existing = Parent.query.filter_by(email=email).first()
	if existing and existing.id != parent.id:
		flash("That email is already in use.", "error")
		return redirect(url_for("public.parent_settings"))

	if new_password:
		if len(new_password) < 8:
			flash("New password must be at least 8 characters.", "error")
			return redirect(url_for("public.parent_settings"))
		if new_password != confirm_new_password:
			flash("New passwords do not match.", "error")
			return redirect(url_for("public.parent_settings"))
		parent.set_password(new_password)

	parent.name = name
	parent.email = email
	db.session.commit()

	flash("Profile updated.", "success")
	return redirect(url_for("public.parent_settings"))


@public_bp.post("/parent/settings/add-kid")
@parent_web_login_required
def parent_settings_add_kid():
	display_name = request.form.get("display_name", "").strip()
	pin = request.form.get("pin", "").strip()

	if not display_name:
		flash("Kid name is required.", "error")
		return redirect(url_for("public.parent_settings"))

	if not pin.isdigit() or len(pin) != 4:
		flash("PIN must be exactly 4 digits.", "error")
		return redirect(url_for("public.parent_settings"))

	kid = Kid(family_id=session["family_id"], display_name=display_name)
	kid.set_pin(pin)
	db.session.add(kid)
	db.session.commit()

	flash(f"Added {display_name} to your family.", "success")
	return redirect(url_for("public.parent_settings"))


@public_bp.post("/parent/settings/update-kid/<int:kid_id>")
@parent_web_login_required
def parent_settings_update_kid(kid_id: int):
	kid = Kid.query.get(kid_id)
	if not kid or kid.family_id != session.get("family_id"):
		flash("Kid not found.", "error")
		return redirect(url_for("public.parent_settings"))

	new_display_name = (request.form.get("display_name") or "").strip()
	new_pin = (request.form.get("pin") or "").strip()

	if not new_display_name:
		flash("Kid name is required.", "error")
		return redirect(url_for("public.parent_settings"))

	if new_pin and (not new_pin.isdigit() or len(new_pin) != 4):
		flash("PIN must be exactly 4 digits if provided.", "error")
		return redirect(url_for("public.parent_settings"))

	kid.display_name = new_display_name
	if new_pin:
		kid.set_pin(new_pin)

	db.session.commit()
	flash(f"Updated {kid.display_name}'s profile.", "success")
	return redirect(url_for("public.parent_settings"))


@public_bp.post("/parent/settings/remove-kid/<int:kid_id>")
@parent_web_login_required
def parent_settings_remove_kid(kid_id: int):
	kid = Kid.query.get(kid_id)
	if not kid or kid.family_id != session.get("family_id"):
		flash("Kid not found.", "error")
		return redirect(url_for("public.parent_settings"))

	kid.is_active = False
	db.session.commit()
	flash(f"{kid.display_name} has been removed from your family.", "success")
	return redirect(url_for("public.parent_settings"))


@public_bp.post("/parent/settings/rotate-family-code")
@parent_web_login_required
def parent_settings_rotate_family_code():
	family = Family.query.get(session.get("family_id"))
	if not family:
		flash("Family not found.", "error")
		return redirect(url_for("public.parent_settings"))

	new_code = generate_family_code()
	family.set_family_code(new_code)
	db.session.commit()

	flash(f"New family code generated: {new_code} — Share this with your co-guardian. It will not be shown again.", "success")
	return redirect(url_for("public.parent_settings"))


@public_bp.post("/parent/settings/request-join-family")
@parent_web_login_required
def parent_request_join_family():
	family_code = request.form.get("family_code", "").strip()
	if not family_code:
		flash("Please enter a family code.", "error")
		return redirect(url_for("public.parent_settings"))

	target_family = _find_family_by_code(family_code)
	if not target_family:
		flash("That family code was not found.", "error")
		return redirect(url_for("public.parent_settings"))

	if target_family.id == session["family_id"]:
		flash("You are already part of that family.", "error")
		return redirect(url_for("public.parent_settings"))

	existing_req = GuardianJoinRequest.query.filter_by(
		family_id=target_family.id,
		requester_parent_id=session["parent_id"],
		status="pending",
	).first()
	if existing_req:
		flash("You already have a pending request to join that family.", "error")
		return redirect(url_for("public.parent_settings"))

	req = GuardianJoinRequest(
		family_id=target_family.id,
		requester_parent_id=session["parent_id"],
	)
	db.session.add(req)
	db.session.commit()

	flash(f"Join request sent to the {target_family.name} family. A guardian there must approve it.", "success")
	return redirect(url_for("public.parent_settings"))


@public_bp.post("/parent/settings/accept-guardian/<int:request_id>")
@parent_web_login_required
def parent_accept_guardian(request_id: int):
	join_req = GuardianJoinRequest.query.get(request_id)
	if not join_req or join_req.family_id != session["family_id"] or join_req.status != "pending":
		flash("Request not found.", "error")
		return redirect(url_for("public.parent_settings"))

	join_req.status = "accepted"
	join_req.resolved_at = datetime.utcnow()
	join_req.resolved_by_parent_id = session["parent_id"]

	requester = Parent.query.get(join_req.requester_parent_id)
	if requester:
		requester.family_id = session["family_id"]

	db.session.commit()
	flash(f"{requester.name if requester else 'Guardian'} has been added to your family.", "success")
	return redirect(url_for("public.parent_settings"))


@public_bp.post("/parent/settings/reject-guardian/<int:request_id>")
@parent_web_login_required
def parent_reject_guardian(request_id: int):
	join_req = GuardianJoinRequest.query.get(request_id)
	if not join_req or join_req.family_id != session["family_id"] or join_req.status != "pending":
		flash("Request not found.", "error")
		return redirect(url_for("public.parent_settings"))

	join_req.status = "rejected"
	join_req.resolved_at = datetime.utcnow()
	join_req.resolved_by_parent_id = session["parent_id"]

	db.session.commit()
	flash("Join request declined.", "success")
	return redirect(url_for("public.parent_settings"))


# ---------------------------------------------------------------------------
# Getting Started / Starter Data
# ---------------------------------------------------------------------------

_STARTER_CHORES = [
	{"name": "Make your bed", "description": "Straighten pillows, pull up covers, and make it tidy.", "coin_reward": 5, "point_value": 2},
	{"name": "Wash the dishes", "description": "Rinse, wash, and stack — or load the dishwasher.", "coin_reward": 10, "point_value": 5},
	{"name": "Take out the trash", "description": "Empty trash cans and replace the bags.", "coin_reward": 8, "point_value": 4},
	{"name": "Vacuum the living room", "description": "Vacuum the main living area thoroughly.", "coin_reward": 12, "point_value": 5},
	{"name": "Clean your room", "description": "Pick up clothes, toys, and tidy all surfaces.", "coin_reward": 10, "point_value": 5},
	{"name": "Feed the pets", "description": "Fill food and water bowls for any family pets.", "coin_reward": 5, "point_value": 2},
	{"name": "Wipe down the kitchen counter", "description": "Clean and dry all kitchen countertops.", "coin_reward": 6, "point_value": 3},
	{"name": "Sweep the floor", "description": "Sweep hard-floor areas and collect debris.", "coin_reward": 7, "point_value": 3},
]

_STARTER_KID_STORE = [
	{"name": "30 min extra screen time", "description": "Earn an extra 30 minutes of video game or TV time.", "kid_coin_cost": 20},
	{"name": "Stay up 30 min late", "description": "Stay up 30 minutes past your normal bedtime.", "kid_coin_cost": 25},
	{"name": "Choose what's for dinner", "description": "Pick the family's dinner for one night.", "kid_coin_cost": 50},
	{"name": "Movie night pick", "description": "Choose the movie for family movie night.", "kid_coin_cost": 35},
	{"name": "Skip one chore (once)", "description": "Skip a single chore without penalty — one time use.", "kid_coin_cost": 40},
	{"name": "Small treat from the store", "description": "Parent buys you a small snack or treat of your choice.", "kid_coin_cost": 60},
]

_STARTER_FAMILY_STORE = [
	{"name": "Family movie night", "description": "Pick a movie and enjoy popcorn together as a family.", "family_point_cost": 80},
	{"name": "Pizza night", "description": "Celebrate with everyone's favourite pizza.", "family_point_cost": 120},
	{"name": "Board game marathon", "description": "Break out the board games for a full evening of fun.", "family_point_cost": 60},
	{"name": "Trip to the park or nature trail", "description": "An outdoor adventure day chosen by the family.", "family_point_cost": 150},
	{"name": "Stay-up-late weekend", "description": "Everyone gets to stay up late on a Friday or Saturday night.", "family_point_cost": 100},
	{"name": "Family outing (bowling, mini-golf, etc.)", "description": "A fun outing activity voted on by the family.", "family_point_cost": 200},
]

_STARTER_CHALLENGES = [
	{"title": "Read for 20 minutes", "description": "Read any book for at least 20 minutes and tell someone what it was about.", "difficulty": "bronze", "coin_reward": 8, "point_value": 3, "requires_proof": False, "is_repeatable": True},
	{"title": "No complaining for a whole day", "description": "Go an entire day without complaining about anything — even vegetables.", "difficulty": "silver", "coin_reward": 20, "point_value": 8, "requires_proof": False, "is_repeatable": True},
	{"title": "Write a thank-you note", "description": "Write a heartfelt thank-you note to a friend, teacher, or family member.", "difficulty": "bronze", "coin_reward": 10, "point_value": 4, "requires_proof": True, "is_repeatable": True},
	{"title": "Learn a new skill", "description": "Pick one new skill (knot tying, a card trick, a new recipe) and demo it for the family.", "difficulty": "gold", "coin_reward": 40, "point_value": 15, "requires_proof": True, "is_repeatable": False},
	{"title": "Do something kind for a stranger", "description": "Perform an unprompted act of kindness for someone outside the family.", "difficulty": "silver", "coin_reward": 25, "point_value": 10, "requires_proof": False, "is_repeatable": True},
	{"title": "Memorise a poem or scripture", "description": "Pick a short poem or scripture, memorise it, and recite it from memory.", "difficulty": "silver", "coin_reward": 20, "point_value": 8, "requires_proof": False, "is_repeatable": False},
	{"title": "Exercise for 30 minutes", "description": "Go for a run, do a workout, shoot hoops — any physical activity for 30 minutes.", "difficulty": "bronze", "coin_reward": 10, "point_value": 4, "requires_proof": False, "is_repeatable": True},
	{"title": "Teach a sibling something new", "description": "Teach a younger sibling (or friend) how to do something you're good at.", "difficulty": "gold", "coin_reward": 35, "point_value": 12, "requires_proof": False, "is_repeatable": True},
]


@public_bp.get("/parent/setup-wizard")
@parent_web_login_required
def parent_setup_wizard():
	parent, family = _load_parent_and_family()
	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))
	return render_template("private/parents/setup_wizard.html", parent=parent, family=family)


@public_bp.post("/parent/setup-wizard/submit")
@parent_web_login_required
def parent_setup_wizard_submit():
	parent, family = _load_parent_and_family()
	if not parent or not family:
		session.clear()
		flash("Session expired.", "error")
		return redirect(url_for("public.login"))

	created = []

	# ── Coin rate ──────────────────────────────────────────────────────────
	try:
		rate = int(request.form.get("coins_per_dollar") or 10)
		if 1 <= rate <= 1000:
			family.coins_per_dollar = rate
	except (ValueError, TypeError):
		pass

	# ── Chore ──────────────────────────────────────────────────────────────
	chore_name = (request.form.get("chore_name") or "").strip()
	if chore_name:
		try:
			chore_coins = max(0, int(request.form.get("chore_coin_reward") or 0))
			chore_points = max(0, int(request.form.get("chore_point_value") or 0))
		except (ValueError, TypeError):
			chore_coins = chore_points = 0
		chore = Chore(
			family_id=family.id,
			created_by_parent_id=parent.id,
			name=chore_name,
			description=(request.form.get("chore_description") or "").strip() or None,
			coin_reward=chore_coins,
			point_value=chore_points,
			requires_photo_proof=False,
			max_concurrent_claims=1,
			schedule_kind="unscheduled",
			rotation_cycle_weeks=1,
			anchor_date=None,
		)
		db.session.add(chore)
		created.append(f'chore "{chore_name}"')

	# ── Challenge ──────────────────────────────────────────────────────────
	challenge_title = (request.form.get("challenge_title") or "").strip()
	if challenge_title:
		difficulty = (request.form.get("challenge_difficulty") or "bronze").strip()
		if difficulty not in {"bronze", "silver", "gold"}:
			difficulty = "bronze"
		try:
			ch_coins = max(0, int(request.form.get("challenge_coin_reward") or 0))
			ch_points = max(0, int(request.form.get("challenge_point_value") or 0))
		except (ValueError, TypeError):
			ch_coins = ch_points = 0
		challenge = Challenge(
			family_id=family.id,
			created_by_parent_id=parent.id,
			title=challenge_title,
			description=(request.form.get("challenge_description") or "").strip() or None,
			difficulty=difficulty,
			coin_reward=ch_coins,
			point_value=ch_points,
			requires_proof=request.form.get("challenge_requires_proof") == "1",
			is_repeatable=request.form.get("challenge_is_repeatable") == "1",
		)
		db.session.add(challenge)
		created.append(f'challenge "{challenge_title}"')

	# ── Kid store item ─────────────────────────────────────────────────────
	kid_item_name = (request.form.get("kid_item_name") or "").strip()
	if kid_item_name:
		try:
			kid_cost = max(1, int(request.form.get("kid_item_coin_cost") or 1))
		except (ValueError, TypeError):
			kid_cost = 1
		kid_item = StoreItem(
			family_id=family.id,
			created_by_parent_id=parent.id,
			name=kid_item_name,
			description=(request.form.get("kid_item_description") or "").strip() or None,
			item_scope="kid",
			item_type="basic",
			kid_coin_cost=kid_cost,
			family_point_cost=0,
			stock_qty=-1,
		)
		db.session.add(kid_item)
		created.append(f'kid reward "{kid_item_name}"')

	# ── Family goal ────────────────────────────────────────────────────────
	family_item_name = (request.form.get("family_item_name") or "").strip()
	if family_item_name:
		try:
			family_cost = max(1, int(request.form.get("family_item_point_cost") or 1))
		except (ValueError, TypeError):
			family_cost = 1
		family_item = StoreItem(
			family_id=family.id,
			created_by_parent_id=parent.id,
			name=family_item_name,
			description=(request.form.get("family_item_description") or "").strip() or None,
			item_scope="family",
			item_type="basic",
			kid_coin_cost=0,
			family_point_cost=family_cost,
			stock_qty=-1,
		)
		db.session.add(family_item)
		created.append(f'family goal "{family_item_name}"')

	db.session.commit()

	if created:
		flash(f"Setup complete! Created: {', '.join(created)}.", "success")
	else:
		flash("Setup complete! You can add more from the individual pages.", "success")

	redirect_to = request.form.get("redirect_to") or ""
	# Only allow relative paths to prevent open redirect
	if redirect_to and redirect_to.startswith("/") and not redirect_to.startswith("//"):
		return redirect(redirect_to)
	return redirect(url_for("public.parent_dashboard"))


@public_bp.get("/parent/getting-started")
@parent_web_login_required
def parent_getting_started():
	parent, family = _load_parent_and_family()
	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	existing_chore_names = {c.name for c in Chore.query.filter_by(family_id=family.id).all()}
	existing_store_names = {s.name for s in StoreItem.query.filter_by(family_id=family.id).all()}

	starter_chores = [
		{**c, "already_exists": c["name"] in existing_chore_names}
		for c in _STARTER_CHORES
	]
	starter_kid_store = [
		{**s, "already_exists": s["name"] in existing_store_names}
		for s in _STARTER_KID_STORE
	]
	starter_family_store = [
		{**s, "already_exists": s["name"] in existing_store_names}
		for s in _STARTER_FAMILY_STORE
	]

	return render_template(
		"private/parents/getting_started.html",
		parent=parent,
		family=family,
		starter_chores=starter_chores,
		starter_kid_store=starter_kid_store,
		starter_family_store=starter_family_store,
		starter_challenges=[{**c, "already_exists": c["title"] in {ch.title for ch in Challenge.query.filter_by(family_id=family.id).all()}} for c in _STARTER_CHALLENGES],
	)


@public_bp.post("/parent/getting-started/apply")
@parent_web_login_required
def parent_getting_started_apply():
	parent, family = _load_parent_and_family()
	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	category = request.form.get("category", "all")  # chores | kid_store | family_store | all
	single_name = (request.form.get("single_name") or "").strip() or None  # optional — apply only one item
	added_count = 0

	if category in ("chores", "all"):
		existing_names = {c.name for c in Chore.query.filter_by(family_id=family.id).all()}
		for chore_data in _STARTER_CHORES:
			if single_name and chore_data["name"] != single_name:
				continue
			if chore_data["name"] not in existing_names:
				db.session.add(Chore(
					family_id=family.id,
					created_by_parent_id=parent.id,
					name=chore_data["name"],
					description=chore_data["description"],
					coin_reward=chore_data["coin_reward"],
					point_value=chore_data["point_value"],
					schedule_kind="unscheduled",
					requires_photo_proof=False,
				))
				added_count += 1

	if category in ("kid_store", "all"):
		existing_names = {s.name for s in StoreItem.query.filter_by(family_id=family.id).all()}
		for item_data in _STARTER_KID_STORE:
			if single_name and item_data["name"] != single_name:
				continue
			if item_data["name"] not in existing_names:
				db.session.add(StoreItem(
					family_id=family.id,
					created_by_parent_id=parent.id,
					name=item_data["name"],
					description=item_data["description"],
					item_scope="kid",
					item_type="basic",
					kid_coin_cost=item_data["kid_coin_cost"],
					family_point_cost=0,
					stock_qty=-1,
				))
				added_count += 1

	if category in ("family_store", "all"):
		existing_names = {s.name for s in StoreItem.query.filter_by(family_id=family.id).all()}
		for item_data in _STARTER_FAMILY_STORE:
			if single_name and item_data["name"] != single_name:
				continue
			if item_data["name"] not in existing_names:
				db.session.add(StoreItem(
					family_id=family.id,
					created_by_parent_id=parent.id,
					name=item_data["name"],
					description=item_data["description"],
					item_scope="family",
					item_type="basic",
					kid_coin_cost=0,
					family_point_cost=item_data["family_point_cost"],
					stock_qty=-1,
				))
				added_count += 1

	if category in ("challenges", "all"):
		existing_titles = {c.title for c in Challenge.query.filter_by(family_id=family.id).all()}
		for ch_data in _STARTER_CHALLENGES:
			if single_name and ch_data["title"] != single_name:
				continue
			if ch_data["title"] not in existing_titles:
				db.session.add(Challenge(
					family_id=family.id,
					created_by_parent_id=parent.id,
					title=ch_data["title"],
					description=ch_data["description"],
					difficulty=ch_data["difficulty"],
					coin_reward=ch_data["coin_reward"],
					point_value=ch_data["point_value"],
					requires_proof=ch_data["requires_proof"],
					is_repeatable=ch_data["is_repeatable"],
				))
				added_count += 1

	db.session.commit()

	labels = {
		"chores": "starter chores",
		"kid_store": "kid store items",
		"family_store": "family goals",
		"challenges": "starter challenges",
		"all": "starter data",
	}
	label = labels.get(category, "starter data")
	if added_count:
		flash(f"Added {added_count} {label} to your family!", "success")
	else:
		flash(f"All {label} are already in your account — nothing new to add.", "info")

	return redirect(url_for("public.parent_getting_started"))


# ── Task Board ─────────────────────────────────────────────────────────────────

def _save_task_photo(file) -> str | None:
	"""Save an uploaded task proof photo and return its relative path or None."""
	if not file or not file.filename:
		return None
	upload_folder = os.path.join(current_app.instance_path, "uploads", "task_photos")
	os.makedirs(upload_folder, exist_ok=True)
	ext = os.path.splitext(secure_filename(file.filename))[1].lower()
	filename = f"task_{secrets.token_hex(8)}{ext}"
	file.save(os.path.join(upload_folder, filename))
	return filename


@public_bp.get("/uploads/task_photos/<path:filename>")
def serve_task_photo(filename):
	directory = os.path.join(current_app.instance_path, "uploads", "task_photos")
	return send_from_directory(directory, filename)


# ── Parent: task board ─────────────────────────────────────────────────────────

@public_bp.get("/parent/tasks")
@parent_web_login_required
def parent_tasks():
	parent = Parent.query.get(session["parent_id"])
	family_id = session["family_id"]
	tasks = (
		Task.query
		.filter_by(family_id=family_id, is_active=True)
		.order_by(Task.sort_order.asc(), Task.created_at.asc())
		.all()
	)
	pending_claims = (
		TaskClaim.query
		.join(Task, TaskClaim.task_id == Task.id)
		.filter(Task.family_id == family_id, TaskClaim.status == "submitted")
		.order_by(TaskClaim.submitted_at.desc())
		.all()
	)
	kids = Kid.query.filter_by(family_id=family_id, is_active=True).all()
	return render_template(
		"private/parents/tasks/index.html",
		tasks=tasks,
		pending_claims=pending_claims,
		kids=kids,
		parent=parent,
	)


@public_bp.post("/parent/tasks/create")
@parent_web_login_required
def parent_tasks_create():
	parent = Parent.query.get(session["parent_id"])
	family_id = session["family_id"]

	# Tier limit check
	_fam = Family.query.get(family_id)
	if _fam:
		_current = Task.query.filter_by(family_id=family_id, is_active=True).count()
		if not can_add(_fam, "tasks", _current):
			flash(limit_reached_message("tasks"), "warning")
			return redirect(url_for("public.parent_tasks"))

	title = (request.form.get("title") or "").strip()
	description = (request.form.get("description") or "").strip() or None
	coin_reward = int(request.form.get("coin_reward") or 0)
	point_reward = int(request.form.get("point_reward") or 0)
	due_date_str = (request.form.get("due_date") or "").strip()
	assigned_kid_id = request.form.get("assigned_to_kid_id") or None
	allow_multiple = request.form.get("allow_multiple_claims") == "1"
	requires_photo = request.form.get("requires_photo_proof") == "1"

	if not title:
		flash("Task title is required.", "error")
		return redirect(url_for("public.parent_tasks"))

	due_date = None
	if due_date_str:
		try:
			due_date = date.fromisoformat(due_date_str)
		except ValueError:
			flash("Invalid due date format.", "error")
			return redirect(url_for("public.parent_tasks"))

	if assigned_kid_id:
		kid = Kid.query.filter_by(id=int(assigned_kid_id), family_id=family_id, is_active=True).first()
		if not kid:
			flash("Selected kid not found.", "error")
			return redirect(url_for("public.parent_tasks"))
		assigned_kid_id = kid.id
	else:
		assigned_kid_id = None

	task = Task(
		family_id=family_id,
		created_by_parent_id=parent.id,
		title=title,
		description=description,
		coin_reward=coin_reward,
		point_reward=point_reward,
		due_date=due_date,
		assigned_to_kid_id=assigned_kid_id,
		allow_multiple_claims=allow_multiple,
		requires_photo_proof=requires_photo,
	)
	db.session.add(task)
	db.session.commit()
	flash(f"Task '{title}' created!", "success")
	return redirect(url_for("public.parent_tasks"))


@public_bp.post("/parent/tasks/<int:task_id>/delete")
@parent_web_login_required
def parent_tasks_delete(task_id: int):
	family_id = session["family_id"]
	task = Task.query.filter_by(id=task_id, family_id=family_id).first_or_404()
	task.is_active = False
	db.session.commit()
	flash(f"Task '{task.title}' removed.", "success")
	return redirect(url_for("public.parent_tasks"))


@public_bp.post("/parent/tasks/<int:task_id>/edit")
@parent_web_login_required
def parent_tasks_edit(task_id: int):
	family_id = session["family_id"]
	task = Task.query.filter_by(id=task_id, family_id=family_id).first_or_404()

	title = (request.form.get("title") or "").strip()
	if not title:
		flash("Task title is required.", "error")
		return redirect(url_for("public.parent_tasks"))

	due_date_str = (request.form.get("due_date") or "").strip()
	due_date = None
	if due_date_str:
		try:
			due_date = date.fromisoformat(due_date_str)
		except ValueError:
			flash("Invalid due date.", "error")
			return redirect(url_for("public.parent_tasks"))

	assigned_kid_id = request.form.get("assigned_to_kid_id") or None
	if assigned_kid_id:
		kid = Kid.query.filter_by(id=int(assigned_kid_id), family_id=family_id, is_active=True).first()
		assigned_kid_id = kid.id if kid else None

	task.title = title
	task.description = (request.form.get("description") or "").strip() or None
	task.coin_reward = int(request.form.get("coin_reward") or 0)
	task.point_reward = int(request.form.get("point_reward") or 0)
	task.due_date = due_date
	task.assigned_to_kid_id = assigned_kid_id
	task.allow_multiple_claims = request.form.get("allow_multiple_claims") == "1"
	task.requires_photo_proof = request.form.get("requires_photo_proof") == "1"
	db.session.commit()
	flash(f"Task '{task.title}' updated.", "success")
	return redirect(url_for("public.parent_tasks"))


@public_bp.post("/parent/tasks/claims/<int:claim_id>/approve")
@parent_web_login_required
def parent_tasks_claim_approve(claim_id: int):
	parent = Parent.query.get(session["parent_id"])
	family_id = session["family_id"]
	claim = TaskClaim.query.filter_by(id=claim_id, family_id=family_id).first_or_404()

	if claim.status != "submitted":
		flash("This claim is not pending approval.", "info")
		return redirect(url_for("public.parent_tasks"))

	note = (request.form.get("resolution_note") or "").strip() or None
	task = claim.task
	kid = Kid.query.get(claim.kid_id)

	claim.status = "approved"
	claim.resolved_at = datetime.utcnow()
	claim.resolved_by_parent_id = parent.id
	claim.resolution_note = note
	claim.awarded_coin_amount = task.coin_reward
	claim.awarded_point_amount = task.point_reward

	if task.coin_reward:
		_record_coin_transaction(
			kid=kid,
			family_id=family_id,
			amount=task.coin_reward,
			kind="task_reward",
			reason=f"Task: {task.title}",
			ref_type="task_claim",
			ref_id=claim.id,
			parent_id=parent.id,
		)

	if task.point_reward:
		family = Family.query.get(family_id)
		family.family_points_balance += task.point_reward

	db.session.commit()
	flash(f"Approved! {kid.display_name} earned {task.coin_reward} coins.", "success")
	return redirect(url_for("public.parent_tasks"))


@public_bp.post("/parent/tasks/claims/<int:claim_id>/reject")
@parent_web_login_required
def parent_tasks_claim_reject(claim_id: int):
	parent = Parent.query.get(session["parent_id"])
	family_id = session["family_id"]
	claim = TaskClaim.query.filter_by(id=claim_id, family_id=family_id).first_or_404()

	if claim.status != "submitted":
		flash("This claim is not pending approval.", "info")
		return redirect(url_for("public.parent_tasks"))

	note = (request.form.get("resolution_note") or "").strip() or None
	claim.status = "rejected"
	claim.resolved_at = datetime.utcnow()
	claim.resolved_by_parent_id = parent.id
	claim.resolution_note = note
	db.session.commit()
	flash("Claim rejected.", "info")
	return redirect(url_for("public.parent_tasks"))


# ── Kid: task board ─────────────────────────────────────────────────────────────

@public_bp.get("/kid/tasks")
@kid_web_login_required
def kid_tasks():
	kid = Kid.query.get(session["kid_id"])
	family_id = session["family_id"]

	# Tasks available to this kid: either open board or assigned to them
	all_tasks = Task.query.filter_by(family_id=family_id, is_active=True).all()

	my_claims = TaskClaim.query.filter_by(kid_id=kid.id).filter(
		TaskClaim.status.in_(["claimed", "submitted"])
	).all()
	my_claimed_task_ids = {c.task_id for c in my_claims}

	available_tasks = []
	for task in all_tasks:
		# Must be assigned to this kid or be open board
		if task.assigned_to_kid_id and task.assigned_to_kid_id != kid.id:
			continue
		# Skip tasks the kid has already claimed/submitted
		if task.id in my_claimed_task_ids:
			continue
		# If not allowing multiple claims, skip if already approved by another kid
		if not task.allow_multiple_claims:
			already_approved = any(c.status == "approved" for c in task.claims)
			if already_approved:
				continue
			already_claimed = any(c.status in ("claimed", "submitted") for c in task.claims)
			if already_claimed:
				continue

		available_tasks.append(task)

	family = Family.query.get(family_id)
	return render_template(
		"private/kids/tasks/index.html",
		kid=kid,
		family=family,
		available_tasks=available_tasks,
		my_claims=my_claims,
	)


@public_bp.post("/kid/tasks/<int:task_id>/claim")
@kid_web_login_required
def kid_task_claim(task_id: int):
	kid = Kid.query.get(session["kid_id"])
	family_id = session["family_id"]
	task = Task.query.filter_by(id=task_id, family_id=family_id, is_active=True).first_or_404()

	# Verify kid is allowed
	if task.assigned_to_kid_id and task.assigned_to_kid_id != kid.id:
		flash("This task is not assigned to you.", "error")
		return redirect(url_for("public.kid_tasks"))

	# Check for duplicate active claim
	existing = TaskClaim.query.filter_by(task_id=task.id, kid_id=kid.id).filter(
		TaskClaim.status.in_(["claimed", "submitted"])
	).first()
	if existing:
		flash("You already have an active claim on this task.", "info")
		return redirect(url_for("public.kid_tasks"))

	# If single-claim task, verify no other active claims
	if not task.allow_multiple_claims:
		other_active = TaskClaim.query.filter_by(task_id=task.id).filter(
			TaskClaim.status.in_(["claimed", "submitted", "approved"])
		).first()
		if other_active:
			flash("This task has already been claimed or completed.", "info")
			return redirect(url_for("public.kid_tasks"))

	claim = TaskClaim(
		task_id=task.id,
		family_id=family_id,
		kid_id=kid.id,
		status="claimed",
	)
	db.session.add(claim)
	db.session.commit()
	flash(f"You picked up '{task.title}'! Submit it when done.", "success")
	return redirect(url_for("public.kid_tasks"))


@public_bp.post("/kid/tasks/claims/<int:claim_id>/submit")
@kid_web_login_required
def kid_task_submit(claim_id: int):
	kid = Kid.query.get(session["kid_id"])
	claim = TaskClaim.query.filter_by(id=claim_id, kid_id=kid.id).first_or_404()

	if claim.status != "claimed":
		flash("This task is already submitted or resolved.", "info")
		return redirect(url_for("public.kid_tasks"))

	photo_file = request.files.get("photo")
	photo_path = _save_task_photo(photo_file)

	if claim.task.requires_photo_proof and not photo_path:
		flash("A photo is required as proof for this task.", "error")
		return redirect(url_for("public.kid_tasks"))

	claim.photo_path = photo_path
	claim.status = "submitted"
	claim.submitted_at = datetime.utcnow()
	db.session.commit()
	flash(f"'{claim.task.title}' submitted! Waiting for parent approval. 🎉", "success")
	return redirect(url_for("public.kid_tasks"))
