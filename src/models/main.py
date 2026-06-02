from __future__ import annotations

import hashlib
import math
import secrets
import string
from datetime import date, datetime, timedelta

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash


db = SQLAlchemy()


chore_category_links = db.Table(
	"chore_category_links",
	db.Column("chore_id", db.Integer, db.ForeignKey("chores.id"), primary_key=True),
	db.Column("category_id", db.Integer, db.ForeignKey("chore_categories.id"), primary_key=True),
)


def _normalize_family_code(code: str) -> str:
	return code.strip().upper().replace("-", "")


def _hash_token(token: str) -> str:
	return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_family_code(length: int = 8) -> str:
	alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
	return "".join(secrets.choice(alphabet) for _ in range(length))


class Family(db.Model):
	__tablename__ = "families"

	id = db.Column(db.Integer, primary_key=True)
	name = db.Column(db.String(120), nullable=False)
	family_code_hash = db.Column(db.String(255), nullable=False)
	family_code_hint = db.Column(db.String(16), nullable=False, index=True)
	family_code_plain = db.Column(db.String(16), nullable=True)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	is_active = db.Column(db.Boolean, default=True, nullable=False)
	family_points_balance = db.Column(db.Integer, default=0, nullable=False)
	# How many coins equal $1 (default 10 → 10 coins = $1)
	coins_per_dollar = db.Column(db.Integer, default=10, nullable=False)
	# Tracks the last date daily chore reset ran for this family (lazy reset)
	last_reset_date = db.Column(db.Date, nullable=True)

	# ── SaaS billing ─────────────────────────────────────────────────────────
	# plan: "free" | "pro"
	plan = db.Column(db.String(20), nullable=False, default="free")
	trial_ends_at = db.Column(db.DateTime, nullable=True)
	stripe_customer_id = db.Column(db.String(120), nullable=True)
	stripe_subscription_id = db.Column(db.String(120), nullable=True)
	# subscription_status: "trialing" | "active" | "past_due" | "canceled" | None
	subscription_status = db.Column(db.String(30), nullable=True)

	parents = db.relationship("Parent", back_populates="family", cascade="all, delete-orphan")
	kids = db.relationship("Kid", back_populates="family", cascade="all, delete-orphan")
	devices = db.relationship("TrustedDevice", back_populates="family", cascade="all, delete-orphan")

	@staticmethod
	def hint_for(code: str) -> str:
		normalized = _normalize_family_code(code)
		return normalized[:4]

	def set_family_code(self, raw_code: str) -> None:
		normalized = _normalize_family_code(raw_code)
		self.family_code_hash = generate_password_hash(normalized)
		self.family_code_hint = self.hint_for(normalized)
		self.family_code_plain = normalized

	def verify_family_code(self, candidate: str) -> bool:
		return check_password_hash(self.family_code_hash, _normalize_family_code(candidate))

	@property
	def is_pro(self) -> bool:
		"""True when the family has an active Pro plan OR an active trial."""
		if self.plan == "pro" and self.subscription_status in ("active", "past_due", None):
			return True
		if self.trial_ends_at and datetime.utcnow() < self.trial_ends_at:
			return True
		return False

	@property
	def trial_active(self) -> bool:
		return bool(self.trial_ends_at and datetime.utcnow() < self.trial_ends_at)

	@property
	def trial_days_remaining(self) -> int:
		if not self.trial_active:
			return 0
		delta = self.trial_ends_at - datetime.utcnow()
		return max(0, delta.days)


class Parent(db.Model):
	__tablename__ = "parents"

	id = db.Column(db.Integer, primary_key=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	email = db.Column(db.String(255), nullable=False, unique=True, index=True)
	password_hash = db.Column(db.String(255), nullable=False)
	name = db.Column(db.String(120), nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	last_login_at = db.Column(db.DateTime)
	# ── Email verification ────────────────────────────────────────────────────
	email_verified = db.Column(db.Boolean, nullable=False, default=False)
	email_verify_token_hash = db.Column(db.String(64), nullable=True)
	email_verify_expires_at = db.Column(db.DateTime, nullable=True)
	# ── Admin flag ────────────────────────────────────────────────────────────
	is_superuser = db.Column(db.Boolean, nullable=False, default=False)

	family = db.relationship("Family", back_populates="parents")
	registered_devices = db.relationship("TrustedDevice", back_populates="registered_by_parent")

	def generate_verify_token(self) -> str:
		"""Generate a new email-verification token, store its hash, return plain token."""
		plain = secrets.token_urlsafe(32)
		self.email_verify_token_hash = _hash_token(plain)
		self.email_verify_expires_at = datetime.utcnow() + timedelta(hours=24)
		return plain

	def verify_email_token(self, plain: str) -> bool:
		"""Return True if the plain token matches and has not expired."""
		if not self.email_verify_token_hash or not self.email_verify_expires_at:
			return False
		if datetime.utcnow() > self.email_verify_expires_at:
			return False
		return _hash_token(plain) == self.email_verify_token_hash

	def set_password(self, raw_password: str) -> None:
		self.password_hash = generate_password_hash(raw_password)

	def verify_password(self, candidate: str) -> bool:
		return check_password_hash(self.password_hash, candidate)


class Kid(db.Model):
	__tablename__ = "kids"

	id = db.Column(db.Integer, primary_key=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	display_name = db.Column(db.String(120), nullable=False)
	pin_hash = db.Column(db.String(255), nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	is_active = db.Column(db.Boolean, default=True, nullable=False)
	coin_balance = db.Column(db.Integer, default=0, nullable=False)

	family = db.relationship("Family", back_populates="kids")

	def set_pin(self, raw_pin: str) -> None:
		self.pin_hash = generate_password_hash(raw_pin)

	def verify_pin(self, candidate: str) -> bool:
		return check_password_hash(self.pin_hash, candidate)


class TrustedDevice(db.Model):
	__tablename__ = "trusted_devices"

	id = db.Column(db.Integer, primary_key=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	device_label = db.Column(db.String(120), nullable=False)
	token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
	user_agent_hash = db.Column(db.String(64), index=True)
	ip_hash = db.Column(db.String(64), index=True)
	registered_by_parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	last_seen_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	expires_at = db.Column(db.DateTime, nullable=False)
	revoked_at = db.Column(db.DateTime)

	family = db.relationship("Family", back_populates="devices")
	registered_by_parent = db.relationship("Parent", back_populates="registered_devices")

	@staticmethod
	def mint_token(length: int = 48) -> str:
		alphabet = string.ascii_letters + string.digits
		return "".join(secrets.choice(alphabet) for _ in range(length))

	@classmethod
	def create_for_family(
		cls,
		family_id: int,
		parent_id: int,
		device_label: str,
		ttl_days: int = 90,
		user_agent: str | None = None,
		ip_address: str | None = None,
	) -> tuple["TrustedDevice", str]:
		plain_token = cls.mint_token()
		device = cls(
			family_id=family_id,
			registered_by_parent_id=parent_id,
			device_label=device_label,
			token_hash=_hash_token(plain_token),
			user_agent_hash=_hash_token(user_agent.strip()) if user_agent else None,
			ip_hash=_hash_token(ip_address.strip()) if ip_address else None,
			expires_at=datetime.utcnow() + timedelta(days=ttl_days),
		)
		return device, plain_token

	@classmethod
	def find_valid_by_token(cls, plain_token: str) -> "TrustedDevice | None":
		token_hash = _hash_token(plain_token)
		now = datetime.utcnow()
		return cls.query.filter(
			cls.token_hash == token_hash,
			cls.revoked_at.is_(None),
			cls.expires_at > now,
		).first()

	@classmethod
	def find_valid_by_fingerprint(cls, user_agent: str, ip_address: str) -> "TrustedDevice | None":
		if not user_agent or not ip_address:
			return None

		now = datetime.utcnow()
		return cls.query.filter(
			cls.user_agent_hash == _hash_token(user_agent.strip()),
			cls.ip_hash == _hash_token(ip_address.strip()),
			cls.revoked_at.is_(None),
			cls.expires_at > now,
		).order_by(cls.last_seen_at.desc()).first()


class PendingDeviceRegistration(db.Model):
	"""Short-lived record created when a kid's device shows a QR code.
	A parent scans it, logs in, and approves — then the kid's browser picks
	up the resulting TrustedDevice token via polling."""

	__tablename__ = "pending_device_registrations"

	id = db.Column(db.Integer, primary_key=True)
	# Token shown in the QR code URL (stored as a SHA-256 hash)
	init_token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	expires_at = db.Column(db.DateTime, nullable=False)

	# Populated once a parent confirms
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=True)
	device_label = db.Column(db.String(120), nullable=True)
	confirmed_at = db.Column(db.DateTime, nullable=True)
	# Plain TrustedDevice token stored briefly so the kid's browser can consume it
	confirmed_device_token = db.Column(db.String(128), nullable=True)
	# Set once the kid's browser has actually consumed (set its cookie)
	completed_at = db.Column(db.DateTime, nullable=True)

	TTL_SECONDS = 5 * 60  # QR codes expire after 5 minutes

	@classmethod
	def create(cls) -> tuple["PendingDeviceRegistration", str]:
		plain_token = TrustedDevice.mint_token(48)
		rec = cls(
			init_token_hash=_hash_token(plain_token),
			expires_at=datetime.utcnow() + timedelta(seconds=cls.TTL_SECONDS),
		)
		return rec, plain_token

	@classmethod
	def find_valid(cls, plain_token: str) -> "PendingDeviceRegistration | None":
		token_hash = _hash_token(plain_token)
		now = datetime.utcnow()
		return cls.query.filter(
			cls.init_token_hash == token_hash,
			cls.expires_at > now,
			cls.completed_at.is_(None),
		).first()


class Chore(db.Model):
	__tablename__ = "chores"

	id = db.Column(db.Integer, primary_key=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	created_by_parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=False)
	name = db.Column(db.String(120), nullable=False)
	description = db.Column(db.Text)
	coin_reward = db.Column(db.Integer, default=0, nullable=False)
	point_value = db.Column(db.Integer, default=0, nullable=False)
	requires_photo_proof = db.Column(db.Boolean, default=False, nullable=False)
	daily_reset_version = db.Column(db.Integer, default=0, nullable=False)
	max_concurrent_claims = db.Column(db.Integer, default=1, nullable=False)
	schedule_kind = db.Column(db.String(20), default="unscheduled", nullable=False)
	rotation_cycle_weeks = db.Column(db.Integer, default=1, nullable=False)
	anchor_date = db.Column(db.Date, default=date.today, nullable=False)
	is_active = db.Column(db.Boolean, default=True, nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	sort_order = db.Column(db.Integer, default=0, nullable=False)

	family = db.relationship("Family", backref=db.backref("chores", lazy=True, cascade="all, delete-orphan"))
	created_by_parent = db.relationship("Parent", backref=db.backref("chores", lazy=True))
	schedule_slots = db.relationship(
		"ChoreScheduleSlot",
		back_populates="chore",
		cascade="all, delete-orphan",
		order_by="(ChoreScheduleSlot.cycle_week_index, ChoreScheduleSlot.weekday)",
	)
	categories = db.relationship(
		"ChoreCategory",
		secondary=chore_category_links,
		back_populates="chores",
		lazy="joined",
	)
	submissions = db.relationship(
		"ChoreSubmission",
		back_populates="chore",
		cascade="all, delete-orphan",
		order_by="ChoreSubmission.claimed_at.desc()",
	)

	def cycle_week_for_date(self, target_date: date) -> int:
		cycle_length = max(self.rotation_cycle_weeks or 1, 1)
		anchor = self.anchor_date or target_date
		delta_days = (target_date - anchor).days
		weeks_since_anchor = 0 if delta_days < 0 else delta_days // 7
		return weeks_since_anchor % cycle_length

	def assignments_for_date(self, target_date: date) -> list["ChoreScheduleSlot"]:
		if self.schedule_kind == "unscheduled":
			return []

		weekday = target_date.weekday()
		cycle_week_index = self.cycle_week_for_date(target_date)
		return [
			slot
			for slot in self.schedule_slots
			if slot.weekday == weekday and slot.cycle_week_index == cycle_week_index
		]


class ChoreScheduleSlot(db.Model):
	__tablename__ = "chore_schedule_slots"

	id = db.Column(db.Integer, primary_key=True)
	chore_id = db.Column(db.Integer, db.ForeignKey("chores.id"), nullable=False, index=True)
	kid_id = db.Column(db.Integer, db.ForeignKey("kids.id"), nullable=False, index=True)
	weekday = db.Column(db.Integer, nullable=False)
	cycle_week_index = db.Column(db.Integer, default=0, nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

	chore = db.relationship("Chore", back_populates="schedule_slots")
	kid = db.relationship("Kid", backref=db.backref("scheduled_chore_slots", lazy=True))

	@property
	def weekday_name(self) -> str:
		return ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"][self.weekday]


class ChoreCategory(db.Model):
	__tablename__ = "chore_categories"

	id = db.Column(db.Integer, primary_key=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	name = db.Column(db.String(60), nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

	family = db.relationship("Family", backref=db.backref("chore_categories", lazy=True, cascade="all, delete-orphan"))
	chores = db.relationship(
		"Chore",
		secondary=chore_category_links,
		back_populates="categories",
	)

	__table_args__ = (
		db.UniqueConstraint("family_id", "name", name="uq_chore_category_family_name"),
	)


class ChoreSubmission(db.Model):
	__tablename__ = "chore_submissions"

	id = db.Column(db.Integer, primary_key=True)
	chore_id = db.Column(db.Integer, db.ForeignKey("chores.id"), nullable=False, index=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	kid_id = db.Column(db.Integer, db.ForeignKey("kids.id"), nullable=False, index=True)
	# claimed | submitted | approved | rejected
	status = db.Column(db.String(20), nullable=False, default="claimed", index=True)
	reset_version = db.Column(db.Integer, default=0, nullable=False, index=True)
	awarded_coin_amount = db.Column(db.Integer, default=0, nullable=False)
	awarded_point_amount = db.Column(db.Integer, default=0, nullable=False)
	before_photo_path = db.Column(db.String(255))
	after_photo_path = db.Column(db.String(255))
	claimed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	submitted_at = db.Column(db.DateTime)
	resolved_at = db.Column(db.DateTime)
	resolved_by_parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=True, index=True)
	resolution_note = db.Column(db.String(255))

	chore = db.relationship("Chore", back_populates="submissions")
	family = db.relationship("Family", backref=db.backref("chore_submissions", lazy=True, cascade="all, delete-orphan"))
	kid = db.relationship("Kid", backref=db.backref("chore_submissions", lazy=True, cascade="all, delete-orphan"))
	resolved_by_parent = db.relationship("Parent", foreign_keys=[resolved_by_parent_id])


class GuardianJoinRequest(db.Model):
	"""A request from a guardian to join an existing family."""

	__tablename__ = "guardian_join_requests"

	id = db.Column(db.Integer, primary_key=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	requester_parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=False, index=True)
	# pending | accepted | rejected
	status = db.Column(db.String(20), nullable=False, default="pending", index=True)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	resolved_at = db.Column(db.DateTime)
	resolved_by_parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=True)

	family = db.relationship("Family", backref=db.backref("guardian_join_requests", lazy=True))
	requester = db.relationship("Parent", foreign_keys=[requester_parent_id], backref=db.backref("sent_join_requests", lazy=True))
	resolved_by = db.relationship("Parent", foreign_keys=[resolved_by_parent_id])


class StoreItem(db.Model):
	__tablename__ = "store_items"

	id = db.Column(db.Integer, primary_key=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	created_by_parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=False, index=True)
	name = db.Column(db.String(120), nullable=False)
	description = db.Column(db.Text)
	# kid | family
	item_scope = db.Column(db.String(20), nullable=False, index=True)
	# basic | timed_session
	item_type = db.Column(db.String(20), default="basic", nullable=False)
	kid_coin_cost = db.Column(db.Integer, default=0, nullable=False)
	family_point_cost = db.Column(db.Integer, default=0, nullable=False)
	# timed_session fields
	timing_mode = db.Column(db.String(20))  # countdown | stopwatch
	session_duration_minutes = db.Column(db.Integer)  # for countdown
	session_rate_type = db.Column(db.String(20))  # flat | per_minute
	session_flat_cost = db.Column(db.Integer, default=0)
	session_coin_per_minute = db.Column(db.Integer, default=0)
	session_max_participants = db.Column(db.Integer, default=1)
	# -1 = unlimited; 0 = out of stock
	stock_qty = db.Column(db.Integer, default=-1, nullable=False)
	is_active = db.Column(db.Boolean, default=True, nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	sort_order = db.Column(db.Integer, default=0, nullable=False)

	family = db.relationship("Family", backref=db.backref("store_items", lazy=True, cascade="all, delete-orphan"))
	created_by_parent = db.relationship("Parent", backref=db.backref("store_items", lazy=True))
	sessions = db.relationship("StoreTimedSession", back_populates="store_item", cascade="all, delete-orphan")


class StoreRedemption(db.Model):
	__tablename__ = "store_redemptions"

	id = db.Column(db.Integer, primary_key=True)
	store_item_id = db.Column(db.Integer, db.ForeignKey("store_items.id"), nullable=False, index=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	requested_by_kid_id = db.Column(db.Integer, db.ForeignKey("kids.id"), nullable=False, index=True)
	# pending | approved | rejected | fulfilled
	status = db.Column(db.String(20), nullable=False, default="pending", index=True)
	requested_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	resolved_at = db.Column(db.DateTime)
	resolved_by_parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=True)
	notes = db.Column(db.String(255))

	store_item = db.relationship("StoreItem", backref=db.backref("redemptions", lazy=True, cascade="all, delete-orphan"))
	family = db.relationship("Family", backref=db.backref("store_redemptions", lazy=True, cascade="all, delete-orphan"))
	requested_by_kid = db.relationship("Kid", backref=db.backref("store_redemptions", lazy=True))
	resolved_by_parent = db.relationship("Parent", foreign_keys=[resolved_by_parent_id])


class StoreRedemptionVote(db.Model):
	__tablename__ = "store_redemption_votes"

	id = db.Column(db.Integer, primary_key=True)
	redemption_id = db.Column(db.Integer, db.ForeignKey("store_redemptions.id"), nullable=False, index=True)
	kid_id = db.Column(db.Integer, db.ForeignKey("kids.id"), nullable=False, index=True)
	# yes | no
	vote = db.Column(db.String(10), nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

	redemption = db.relationship("StoreRedemption", backref=db.backref("votes", lazy=True, cascade="all, delete-orphan"))
	kid = db.relationship("Kid", backref=db.backref("store_redemption_votes", lazy=True))

	__table_args__ = (
		db.UniqueConstraint("redemption_id", "kid_id", name="uq_store_redemption_vote_kid"),
	)


class StoreTimedSession(db.Model):
	"""Records a timed session started by a kid when using a timed_session store item."""

	__tablename__ = "store_timed_sessions"

	id = db.Column(db.Integer, primary_key=True)
	store_item_id = db.Column(db.Integer, db.ForeignKey("store_items.id"), nullable=False, index=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	started_by_kid_id = db.Column(db.Integer, db.ForeignKey("kids.id"), nullable=False, index=True)
	participant_kid_id = db.Column(db.Integer, db.ForeignKey("kids.id"), nullable=True, index=True)
	# active | completed | cancelled
	status = db.Column(db.String(20), nullable=False, default="active", index=True)
	# snapshot of timing_mode at session start
	timing_mode = db.Column(db.String(20), nullable=False)  # countdown | stopwatch
	# null for stopwatch, set for countdown
	planned_duration_minutes = db.Column(db.Integer)
	started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
	ended_at = db.Column(db.DateTime)
	total_coins_charged = db.Column(db.Integer, nullable=False, default=0)

	store_item = db.relationship("StoreItem", back_populates="sessions")
	family = db.relationship("Family", backref=db.backref("store_timed_sessions", lazy=True, cascade="all, delete-orphan"))
	started_by_kid = db.relationship("Kid", foreign_keys=[started_by_kid_id], backref=db.backref("store_timed_sessions_started", lazy=True))
	participant_kid = db.relationship("Kid", foreign_keys=[participant_kid_id], backref=db.backref("store_timed_sessions_joined", lazy=True))
	participants = db.relationship(
		"StoreSessionParticipant",
		back_populates="timed_session",
		cascade="all, delete-orphan",
		order_by="StoreSessionParticipant.joined_at.asc()",
	)
	turns = db.relationship(
		"StoreSessionTurn",
		back_populates="timed_session",
		cascade="all, delete-orphan",
		order_by="StoreSessionTurn.started_at.asc()",
	)

	@property
	def elapsed_seconds(self) -> int:
		"""Seconds elapsed since start (capped at planned duration for countdown)."""
		end = self.ended_at or datetime.utcnow()
		elapsed = max(0, int((end - self.started_at).total_seconds()))
		if self.timing_mode == "countdown" and self.planned_duration_minutes:
			return min(elapsed, self.planned_duration_minutes * 60)
		return elapsed

	@property
	def remaining_seconds(self) -> int | None:
		"""Seconds remaining for countdown sessions; None for stopwatch."""
		if self.timing_mode != "countdown" or not self.planned_duration_minutes:
			return None
		return max(0, self.planned_duration_minutes * 60 - self.elapsed_seconds)

	def calculate_coins_due(self, item: "StoreItem") -> int:
		"""Calculate coins owed based on rate type and elapsed time."""
		if item.session_rate_type == "flat":
			return item.session_flat_cost or 0
		# per_minute
		elapsed_minutes = math.ceil(self.elapsed_seconds / 60) if self.elapsed_seconds > 0 else 0
		return elapsed_minutes * (item.session_coin_per_minute or 0)

	@property
	def current_turn(self) -> "StoreSessionTurn | None":
		for turn in reversed(self.turns or []):
			if turn.ended_at is None:
				return turn
		return None


class StoreSessionParticipant(db.Model):
	"""A joined kid or guest in a shared timed store session."""

	__tablename__ = "store_session_participants"

	id = db.Column(db.Integer, primary_key=True)
	timed_session_id = db.Column(db.Integer, db.ForeignKey("store_timed_sessions.id"), nullable=False, index=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	kid_id = db.Column(db.Integer, db.ForeignKey("kids.id"), nullable=True, index=True)
	# kid | guest
	participant_type = db.Column(db.String(20), nullable=False, default="kid", index=True)
	guest_name = db.Column(db.String(120))
	joined_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

	timed_session = db.relationship("StoreTimedSession", back_populates="participants")
	family = db.relationship("Family", backref=db.backref("store_session_participants", lazy=True, cascade="all, delete-orphan"))
	kid = db.relationship("Kid", backref=db.backref("store_session_participants", lazy=True))
	turns = db.relationship(
		"StoreSessionTurn",
		back_populates="participant",
		cascade="all, delete-orphan",
		order_by="StoreSessionTurn.started_at.asc()",
	)

	__table_args__ = (
		db.UniqueConstraint("timed_session_id", "kid_id", name="uq_store_session_participant_kid"),
	)

	@property
	def display_name(self) -> str:
		if self.participant_type == "guest":
			return self.guest_name or "Guest"
		return self.kid.display_name if self.kid else "Kid"

	@property
	def charges_coins(self) -> bool:
		return self.participant_type == "kid" and self.kid_id is not None


class StoreSessionTurn(db.Model):
	"""A single turn slice within a shared timed store session."""

	__tablename__ = "store_session_turns"

	id = db.Column(db.Integer, primary_key=True)
	timed_session_id = db.Column(db.Integer, db.ForeignKey("store_timed_sessions.id"), nullable=False, index=True)
	participant_id = db.Column(db.Integer, db.ForeignKey("store_session_participants.id"), nullable=False, index=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	started_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	ended_at = db.Column(db.DateTime)
	elapsed_seconds = db.Column(db.Integer, nullable=False, default=0)
	coins_charged = db.Column(db.Integer, nullable=False, default=0)

	timed_session = db.relationship("StoreTimedSession", back_populates="turns")
	participant = db.relationship("StoreSessionParticipant", back_populates="turns")
	family = db.relationship("Family", backref=db.backref("store_session_turns", lazy=True, cascade="all, delete-orphan"))

	@property
	def live_elapsed_seconds(self) -> int:
		end = self.ended_at or datetime.utcnow()
		return max(0, int((end - self.started_at).total_seconds()))


class PasswordResetToken(db.Model):
	"""Single-use, time-limited token for parent password resets."""

	__tablename__ = "password_reset_tokens"

	id = db.Column(db.Integer, primary_key=True)
	parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=False, index=True)
	token_hash = db.Column(db.String(64), nullable=False, unique=True, index=True)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	expires_at = db.Column(db.DateTime, nullable=False)
	used_at = db.Column(db.DateTime)

	parent = db.relationship("Parent", backref=db.backref("password_reset_tokens", lazy=True, cascade="all, delete-orphan"))

	@classmethod
	def create_for_parent(cls, parent_id: int, ttl_minutes: int = 60) -> tuple["PasswordResetToken", str]:
		plain_token = secrets.token_urlsafe(48)
		token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
		record = cls(
			parent_id=parent_id,
			token_hash=token_hash,
			expires_at=datetime.utcnow() + timedelta(minutes=ttl_minutes),
		)
		return record, plain_token

	@classmethod
	def find_valid(cls, plain_token: str) -> "PasswordResetToken | None":
		token_hash = hashlib.sha256(plain_token.encode()).hexdigest()
		now = datetime.utcnow()
		return cls.query.filter(
			cls.token_hash == token_hash,
			cls.used_at.is_(None),
			cls.expires_at > now,
		).first()


class CoinTransaction(db.Model):
	"""Ledger entry for every coin credit or debit."""

	__tablename__ = "coin_transactions"

	id = db.Column(db.Integer, primary_key=True)
	kid_id = db.Column(db.Integer, db.ForeignKey("kids.id"), nullable=False, index=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	# positive = credit, negative = debit
	amount = db.Column(db.Integer, nullable=False)
	# fine | chore_reward | store_purchase | timed_session | manual_add
	kind = db.Column(db.String(30), nullable=False)
	# Human-readable label; required for fines
	reason = db.Column(db.Text)
	ref_type = db.Column(db.String(50))   # e.g. "chore_submission", "store_redemption"
	ref_id = db.Column(db.Integer)        # soft reference to the related record id
	created_by_parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"))
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	approved_at = db.Column(db.DateTime, nullable=True)
	seen_by_kid = db.Column(db.Boolean, nullable=False, default=False)

	kid = db.relationship("Kid", backref=db.backref("coin_transactions", lazy=True, order_by="CoinTransaction.created_at.desc()"))
	family = db.relationship("Family", backref=db.backref("coin_transactions", lazy=True))
	created_by_parent = db.relationship("Parent", backref=db.backref("coin_transactions_issued", lazy=True))


class StoreSessionPreference(db.Model):
	"""Saves the last timer setup a kid used for a timed item."""

	__tablename__ = "store_session_preferences"

	id = db.Column(db.Integer, primary_key=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	kid_id = db.Column(db.Integer, db.ForeignKey("kids.id"), nullable=False, index=True)
	store_item_id = db.Column(db.Integer, db.ForeignKey("store_items.id"), nullable=False, index=True)
	timing_mode = db.Column(db.String(20), nullable=False, default="countdown")
	countdown_minutes = db.Column(db.Integer, nullable=False, default=30)
	updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

	family = db.relationship("Family", backref=db.backref("store_session_preferences", lazy=True, cascade="all, delete-orphan"))
	kid = db.relationship("Kid", backref=db.backref("store_session_preferences", lazy=True))
	store_item = db.relationship("StoreItem", backref=db.backref("store_session_preferences", lazy=True, cascade="all, delete-orphan"))

	__table_args__ = (
		db.UniqueConstraint("kid_id", "store_item_id", name="uq_store_session_pref_kid_item"),
	)


class Challenge(db.Model):
	"""A non-chore goal (memory verse, character trait, act of service, etc.) that kids can earn coins/points for."""

	__tablename__ = "challenges"

	id = db.Column(db.Integer, primary_key=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	created_by_parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=False)
	title = db.Column(db.String(120), nullable=False)
	description = db.Column(db.Text)
	# bronze | silver | gold
	difficulty = db.Column(db.String(20), nullable=False, default="bronze")
	coin_reward = db.Column(db.Integer, default=0, nullable=False)
	point_value = db.Column(db.Integer, default=0, nullable=False)
	requires_proof = db.Column(db.Boolean, default=False, nullable=False)
	is_repeatable = db.Column(db.Boolean, default=False, nullable=False)
	is_active = db.Column(db.Boolean, default=True, nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	sort_order = db.Column(db.Integer, default=0, nullable=False)

	family = db.relationship("Family", backref=db.backref("challenges", lazy=True, cascade="all, delete-orphan"))
	created_by_parent = db.relationship("Parent", backref=db.backref("challenges_created", lazy=True))
	submissions = db.relationship(
		"ChallengeSubmission",
		back_populates="challenge",
		cascade="all, delete-orphan",
		order_by="ChallengeSubmission.claimed_at.desc()",
	)


class ChallengeSubmission(db.Model):
	"""A kid's attempt at a Challenge."""

	__tablename__ = "challenge_submissions"

	id = db.Column(db.Integer, primary_key=True)
	challenge_id = db.Column(db.Integer, db.ForeignKey("challenges.id"), nullable=False, index=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	kid_id = db.Column(db.Integer, db.ForeignKey("kids.id"), nullable=False, index=True)
	# claimed | submitted | approved | rejected
	status = db.Column(db.String(20), nullable=False, default="claimed", index=True)
	proof_note = db.Column(db.Text)
	proof_photo_path = db.Column(db.String(255))
	awarded_coin_amount = db.Column(db.Integer, default=0, nullable=False)
	awarded_point_amount = db.Column(db.Integer, default=0, nullable=False)
	claimed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	submitted_at = db.Column(db.DateTime)
	resolved_at = db.Column(db.DateTime)
	resolved_by_parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=True, index=True)
	resolution_note = db.Column(db.String(255))

	challenge = db.relationship("Challenge", back_populates="submissions")
	family = db.relationship("Family", backref=db.backref("challenge_submissions", lazy=True, cascade="all, delete-orphan"))
	kid = db.relationship("Kid", backref=db.backref("challenge_submissions", lazy=True, cascade="all, delete-orphan"))
	resolved_by_parent = db.relationship("Parent", foreign_keys=[resolved_by_parent_id])


class Task(db.Model):
	"""A one-off task on the family task board. Can be assigned to a specific kid
	or left open for any kid to claim."""

	__tablename__ = "tasks"

	id = db.Column(db.Integer, primary_key=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	created_by_parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=False)
	title = db.Column(db.String(120), nullable=False)
	description = db.Column(db.Text)
	coin_reward = db.Column(db.Integer, default=0, nullable=False)
	point_reward = db.Column(db.Integer, default=0, nullable=False)
	due_date = db.Column(db.Date, nullable=True)
	# null = open board (any kid can claim). set = assigned to that specific kid.
	assigned_to_kid_id = db.Column(db.Integer, db.ForeignKey("kids.id"), nullable=True, index=True)
	# if True, multiple kids can each independently claim & complete this task
	allow_multiple_claims = db.Column(db.Boolean, default=False, nullable=False)
	requires_photo_proof = db.Column(db.Boolean, default=True, nullable=False)
	is_active = db.Column(db.Boolean, default=True, nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	sort_order = db.Column(db.Integer, default=0, nullable=False)

	family = db.relationship("Family", backref=db.backref("tasks", lazy=True, cascade="all, delete-orphan"))
	created_by_parent = db.relationship("Parent", backref=db.backref("tasks_created", lazy=True))
	assigned_to_kid = db.relationship("Kid", foreign_keys=[assigned_to_kid_id], backref=db.backref("assigned_tasks", lazy=True))
	claims = db.relationship(
		"TaskClaim",
		back_populates="task",
		cascade="all, delete-orphan",
		order_by="TaskClaim.claimed_at.desc()",
	)

	@property
	def is_open_board(self) -> bool:
		return self.assigned_to_kid_id is None


class TaskClaim(db.Model):
	"""A kid's claim/submission on a Task."""

	__tablename__ = "task_claims"

	id = db.Column(db.Integer, primary_key=True)
	task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False, index=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	kid_id = db.Column(db.Integer, db.ForeignKey("kids.id"), nullable=False, index=True)
	# claimed | submitted | approved | rejected
	status = db.Column(db.String(20), nullable=False, default="claimed", index=True)
	photo_path = db.Column(db.String(255))
	awarded_coin_amount = db.Column(db.Integer, default=0, nullable=False)
	awarded_point_amount = db.Column(db.Integer, default=0, nullable=False)
	claimed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
	submitted_at = db.Column(db.DateTime)
	resolved_at = db.Column(db.DateTime)
	resolved_by_parent_id = db.Column(db.Integer, db.ForeignKey("parents.id"), nullable=True, index=True)
	resolution_note = db.Column(db.String(255))

	task = db.relationship("Task", back_populates="claims")
	family = db.relationship("Family", backref=db.backref("task_claims", lazy=True, cascade="all, delete-orphan"))
	kid = db.relationship("Kid", backref=db.backref("task_claims", lazy=True, cascade="all, delete-orphan"))
	resolved_by_parent = db.relationship("Parent", foreign_keys=[resolved_by_parent_id])


# ---------------------------------------------------------------------------
# Promo Codes
# ---------------------------------------------------------------------------

class PromoCode(db.Model):
	"""Admin-managed promotional codes.

	behavior:
	  "discount"    — a Stripe Promotion Code applied at Checkout (requires stripe_promotion_code_id)
	  "grant_trial" — extends the family's Pro trial by `benefit_days` days (no Stripe needed)

	billing_cycle:
	  "any" | "monthly" | "annual"  (informational / Stripe coupon constraint)
	"""

	__tablename__ = "promo_codes"

	id = db.Column(db.Integer, primary_key=True)
	code = db.Column(db.String(64), nullable=False, unique=True, index=True)
	description = db.Column(db.String(255), nullable=True)
	# "discount" | "grant_trial"
	behavior = db.Column(db.String(30), nullable=False, default="discount")
	# "pro" (only tier for now)
	target_tier = db.Column(db.String(20), nullable=False, default="pro")
	# "any" | "monthly" | "annual"
	billing_cycle = db.Column(db.String(20), nullable=False, default="any")
	expires_at = db.Column(db.DateTime, nullable=True)
	# days to extend trial (grant_trial only)
	benefit_days = db.Column(db.Integer, nullable=True)
	max_uses = db.Column(db.Integer, nullable=True)
	use_count = db.Column(db.Integer, nullable=False, default=0)
	# Stripe promo code ID (discount behavior)
	stripe_promotion_code_id = db.Column(db.String(120), nullable=True)
	is_active = db.Column(db.Boolean, nullable=False, default=True)
	created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

	# Track which families have used this code
	redemptions = db.relationship("PromoRedemption", back_populates="promo_code", cascade="all, delete-orphan")

	@property
	def is_expired(self) -> bool:
		return bool(self.expires_at and datetime.utcnow() > self.expires_at)

	@property
	def is_maxed(self) -> bool:
		return bool(self.max_uses and self.use_count >= self.max_uses)

	@property
	def is_usable(self) -> bool:
		return self.is_active and not self.is_expired and not self.is_maxed

	def record_use(self, family_id: int) -> None:
		self.use_count += 1
		db.session.add(PromoRedemption(promo_code_id=self.id, family_id=family_id))


class PromoRedemption(db.Model):
	"""Tracks which families have redeemed a promo code."""

	__tablename__ = "promo_redemptions"

	id = db.Column(db.Integer, primary_key=True)
	promo_code_id = db.Column(db.Integer, db.ForeignKey("promo_codes.id"), nullable=False, index=True)
	family_id = db.Column(db.Integer, db.ForeignKey("families.id"), nullable=False, index=True)
	redeemed_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

	promo_code = db.relationship("PromoCode", back_populates="redemptions")
	family = db.relationship("Family", backref=db.backref("promo_redemptions", lazy=True))


# ---------------------------------------------------------------------------
# Feature Flags
# ---------------------------------------------------------------------------

class FeatureFlag(db.Model):
	"""Persists per-feature tier overrides set via the admin UI.

	Tier values: 'free' | 'pro' | 'disabled'
	The code-level FEATURES dict in limits.py is used as the default;
	rows here override those defaults at runtime.
	"""

	__tablename__ = "feature_flags"

	key = db.Column(db.String(64), primary_key=True)
	tier = db.Column(db.String(20), nullable=False)  # 'free' | 'pro' | 'disabled'
	updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


# ---------------------------------------------------------------------------
# App Settings (admin-managed env-var overrides)
# ---------------------------------------------------------------------------

class AppSetting(db.Model):
	"""Key/value store for runtime configuration set via the admin UI.

	At startup these values are loaded into os.environ, so they override
	anything set in the deployment environment (Coolify env vars etc.).
	Secret values (API keys, webhook secrets) are stored in plaintext here;
	protect this DB accordingly.
	"""

	__tablename__ = "app_settings"

	key = db.Column(db.String(128), primary_key=True)
	value = db.Column(db.Text, nullable=True)
	updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

	def __repr__(self) -> str:
		return f"<AppSetting {self.key}>"


# ---------------------------------------------------------------------------
# Donations
# ---------------------------------------------------------------------------

class Donation(db.Model):
	"""Logs one-time donations received via Stripe Payment Link."""

	__tablename__ = "donations"

	id = db.Column(db.Integer, primary_key=True)
	stripe_payment_intent_id = db.Column(db.String(120), nullable=False, unique=True, index=True)
	amount_cents = db.Column(db.Integer, nullable=False)  # amount in smallest currency unit
	currency = db.Column(db.String(10), nullable=False, default="usd")
	donor_email = db.Column(db.String(255), nullable=True)  # from billing_details
	donor_name = db.Column(db.String(255), nullable=True)
	received_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

	@property
	def amount_display(self) -> str:
		"""Human-readable amount, e.g. '$5.00'."""
		return f"${self.amount_cents / 100:,.2f}"
