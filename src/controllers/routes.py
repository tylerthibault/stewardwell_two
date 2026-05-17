import os
import secrets
from datetime import date, datetime, timedelta
from functools import wraps

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

import math

from src.models.main import (
	Chore,
	ChoreCategory,
	ChoreScheduleSlot,
	ChoreSubmission,
	CoinTransaction,
	Family,
	GuardianJoinRequest,
	Kid,
	Parent,
	StoreItem,
	StoreRedemption,
	StoreRedemptionVote,
	StoreSessionParticipant,
	StoreSessionTurn,
	StoreTimedSession,
	TrustedDevice,
	db,
	generate_family_code,
)


public_bp = Blueprint("public", __name__)


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


def _is_chore_locked_today(chore: Chore) -> bool:
	return _remaining_claim_slots_for_today(chore) <= 0


def _build_chore_slot_lookup(chore: Chore) -> dict[tuple[int, int], int]:
	return {(slot.cycle_week_index, slot.weekday): slot.kid_id for slot in chore.schedule_slots}


@public_bp.get("/")
def landing():
	return render_template("public/landing/index.html")


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

	session.clear()
	session["role"] = "parent"
	session["parent_id"] = parent.id
	session["family_id"] = parent.family_id
	db.session.commit()

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

	parent_name = f"{first_name} {last_name}".strip()
	parent = Parent(family=family, name=parent_name, email=email)
	parent.set_password(password)

	db.session.add(family)
	db.session.add(parent)
	db.session.commit()

	session.clear()
	session["role"] = "parent"
	session["parent_id"] = parent.id
	session["family_id"] = family.id

	response = redirect(url_for("public.parent_dashboard"))
	flash(f"Account created! Save your family code: {family_code}", "success")
	return response


@public_bp.get("/health")
def health():
	return jsonify({"success": True, "message": "ok"})


@public_bp.get("/parent/dashboard")
@parent_web_login_required
def parent_dashboard():
	parent, family = _load_parent_and_family()

	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	kids = Kid.query.filter_by(family_id=family.id, is_active=True).order_by(Kid.created_at.asc()).all()
	pending_approvals_count = ChoreSubmission.query.filter_by(family_id=family.id, status="submitted").count()

	return render_template(
		"private/parents/dashboard.html",
		parent=parent,
		family=family,
		kids=kids,
		pending_approvals_count=pending_approvals_count,
	)


@public_bp.get("/parent/chores")
@parent_web_login_required
def parent_chores():
	parent, family = _load_parent_and_family()

	if not parent or not family:
		session.clear()
		flash("Session expired. Please log in again.", "error")
		return redirect(url_for("public.login"))

	kids = Kid.query.filter_by(family_id=family.id, is_active=True).order_by(Kid.display_name.asc()).all()
	chores = Chore.query.filter_by(family_id=family.id).order_by(Chore.created_at.desc()).all()
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


@public_bp.post("/parent/chores/create")
@parent_web_login_required
def parent_create_chore():
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

	if not parent or not submission or submission.family_id != session.get("family_id"):
		flash("Submission not found.", "error")
		return redirect(url_for("public.parent_chores"))

	if submission.status != "submitted":
		flash("Only submitted chores can be reviewed.", "error")
		return redirect(url_for("public.parent_chores"))

	if action not in {"approve", "reject"}:
		flash("Invalid decision.", "error")
		return redirect(url_for("public.parent_chores"))

	submission.status = "approved" if action == "approve" else "rejected"
	submission.resolved_at = datetime.utcnow()
	submission.resolved_by_parent_id = parent.id
	submission.resolution_note = resolution_note or None

	if action == "reject":
		submission.awarded_coin_amount = 0
		submission.awarded_point_amount = 0

	if action == "approve":
		_recalculate_chore_split_rewards(
			submission.chore,
			submission.reset_version,
			_submission_day_key(submission),
		)

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
		vote_summary=vote_summary,
		active_tab=active_tab,
		active_sessions=active_sessions,
		recent_sessions=recent_sessions,
	)


@public_bp.post("/parent/store/items/create")
@parent_web_login_required
def parent_store_create_item():
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
	db.session.add(CoinTransaction(
		kid_id=kid.id,
		family_id=kid.family_id,
		amount=coins,
		kind="manual_add",
		reason="Manually added by parent",
		created_by_parent_id=session.get("parent_id"),
	))
	db.session.commit()
	flash(f"Added {coins} coins to {kid.display_name}.", "success")
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


@public_bp.post("/parent/logout")
def parent_logout():
	session.clear()
	response = redirect(url_for("public.login"))
	flash("You are logged out.", "success")
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

	if kid.coin_balance < item.kid_coin_cost:
		flash("You do not have enough coins.", "error")
		return redirect(url_for("public.kid_store", tab="kid"))

	kid.coin_balance -= item.kid_coin_cost
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
	db.session.flush()  # get redemption.id before logging
	db.session.add(CoinTransaction(
		kid_id=kid.id,
		family_id=kid.family_id,
		amount=-item.kid_coin_cost,
		kind="store_purchase",
		reason=f"Store purchase: {item.name}",
		ref_type="store_redemption",
		ref_id=redemption.id,
	))
	db.session.commit()

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
