from flask import Flask
from sqlalchemy import inspect, text
from dotenv import load_dotenv
import os

load_dotenv()

from src.models.main import db


def _apply_sqlite_schema_fixes() -> None:
	inspector = inspect(db.engine)
	table_names = set(inspector.get_table_names())
	if "chores" not in table_names:
		return

	columns = {column["name"] for column in inspector.get_columns("chores")}
	if "point_value" not in columns:
		with db.engine.begin() as connection:
			connection.execute(text("ALTER TABLE chores ADD COLUMN point_value INTEGER NOT NULL DEFAULT 0"))
	if "requires_photo_proof" not in columns:
		with db.engine.begin() as connection:
			connection.execute(text("ALTER TABLE chores ADD COLUMN requires_photo_proof BOOLEAN NOT NULL DEFAULT 0"))
	if "daily_reset_version" not in columns:
		with db.engine.begin() as connection:
			connection.execute(text("ALTER TABLE chores ADD COLUMN daily_reset_version INTEGER NOT NULL DEFAULT 0"))
	if "max_concurrent_claims" not in columns:
		with db.engine.begin() as connection:
			connection.execute(text("ALTER TABLE chores ADD COLUMN max_concurrent_claims INTEGER NOT NULL DEFAULT 1"))

	if "families" in table_names:
		family_columns = {column["name"] for column in inspector.get_columns("families")}
		if "family_points_balance" not in family_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE families ADD COLUMN family_points_balance INTEGER NOT NULL DEFAULT 0"))
		if "family_code_plain" not in family_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE families ADD COLUMN family_code_plain VARCHAR(16)"))
		if "coins_per_dollar" not in family_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE families ADD COLUMN coins_per_dollar INTEGER NOT NULL DEFAULT 10"))
		if "last_reset_date" not in family_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE families ADD COLUMN last_reset_date DATE"))
		# SaaS billing columns
		if "plan" not in family_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE families ADD COLUMN plan VARCHAR(20) NOT NULL DEFAULT 'free'"))
		if "trial_ends_at" not in family_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE families ADD COLUMN trial_ends_at DATETIME"))
		if "stripe_customer_id" not in family_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE families ADD COLUMN stripe_customer_id VARCHAR(120)"))
		if "stripe_subscription_id" not in family_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE families ADD COLUMN stripe_subscription_id VARCHAR(120)"))
		if "subscription_status" not in family_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE families ADD COLUMN subscription_status VARCHAR(30)"))

	if "kids" in table_names:
		kid_columns = {column["name"] for column in inspector.get_columns("kids")}
		if "coin_balance" not in kid_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE kids ADD COLUMN coin_balance INTEGER NOT NULL DEFAULT 0"))

	if "parents" in table_names:
		parent_columns = {column["name"] for column in inspector.get_columns("parents")}
		if "email_verified" not in parent_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE parents ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0"))
		if "email_verify_token_hash" not in parent_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE parents ADD COLUMN email_verify_token_hash VARCHAR(64)"))
		if "email_verify_expires_at" not in parent_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE parents ADD COLUMN email_verify_expires_at DATETIME"))
		if "is_superuser" not in parent_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE parents ADD COLUMN is_superuser BOOLEAN NOT NULL DEFAULT 0"))

	if "trusted_devices" in table_names:
		device_columns = {column["name"] for column in inspector.get_columns("trusted_devices")}
		if "user_agent_hash" not in device_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE trusted_devices ADD COLUMN user_agent_hash VARCHAR(64)"))
		if "ip_hash" not in device_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE trusted_devices ADD COLUMN ip_hash VARCHAR(64)"))

	if "sort_order" not in columns:
		with db.engine.begin() as connection:
			connection.execute(text("ALTER TABLE chores ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"))

	if "chore_submissions" in table_names:
		submission_columns = {column["name"] for column in inspector.get_columns("chore_submissions")}
		if "reset_version" not in submission_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE chore_submissions ADD COLUMN reset_version INTEGER NOT NULL DEFAULT 0"))
		if "awarded_coin_amount" not in submission_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE chore_submissions ADD COLUMN awarded_coin_amount INTEGER NOT NULL DEFAULT 0"))
		if "awarded_point_amount" not in submission_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE chore_submissions ADD COLUMN awarded_point_amount INTEGER NOT NULL DEFAULT 0"))

	if "store_items" in table_names:
		si_columns = {column["name"] for column in inspector.get_columns("store_items")}
		_si_patches = [
			("item_type", "VARCHAR(20) NOT NULL DEFAULT 'basic'"),
			("timing_mode", "VARCHAR(20)"),
			("session_duration_minutes", "INTEGER"),
			("session_rate_type", "VARCHAR(20)"),
			("session_flat_cost", "INTEGER NOT NULL DEFAULT 0"),
			("session_coin_per_minute", "INTEGER NOT NULL DEFAULT 0"),
			("session_max_participants", "INTEGER NOT NULL DEFAULT 1"),
			("stock_qty", "INTEGER NOT NULL DEFAULT -1"),
		]
		for col_name, col_sql in _si_patches:
			if col_name not in si_columns:
				with db.engine.begin() as connection:
					connection.execute(text(f"ALTER TABLE store_items ADD COLUMN {col_name} {col_sql}"))

	if "store_timed_sessions" in table_names:
		sts_columns = {column["name"] for column in inspector.get_columns("store_timed_sessions")}
		if "participant_kid_id" not in sts_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE store_timed_sessions ADD COLUMN participant_kid_id INTEGER"))

	if "store_items" in table_names:
		si2_columns = {column["name"] for column in inspector.get_columns("store_items")}
		if "sort_order" not in si2_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE store_items ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"))

	if "challenges" in table_names:
		ch_columns = {column["name"] for column in inspector.get_columns("challenges")}
		if "sort_order" not in ch_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE challenges ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"))

	if "tasks" in table_names:
		task_columns = {column["name"] for column in inspector.get_columns("tasks")}
		if "sort_order" not in task_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE tasks ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0"))


def create_app() -> Flask:
	app = Flask(__name__)
	app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-key")
	app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL") or "sqlite:///stewardwell.db"
	app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

	from src.controllers.routes import public_bp
	from src.controllers.parent_controller import parent_bp
	from src.controllers.kid_controller import kid_bp
	from src.controllers.admin import admin_bp

	db.init_app(app)
	app.register_blueprint(public_bp)
	app.register_blueprint(parent_bp)
	app.register_blueprint(kid_bp)
	app.register_blueprint(admin_bp)

	with app.app_context():
		db.create_all()
		_apply_sqlite_schema_fixes()
		_seed_dev_admin()

	# ── Background scheduler ─────────────────────────────────────────────────
	if not app.debug or os.environ.get("SCHEDULER_ENABLED"):
		_start_scheduler(app)

	return app


def _seed_dev_admin() -> None:
	"""Create a default superuser for development if one doesn't already exist.
	Credentials: admin@email.com / admin
	Remove or guard with an env check before going to production.
	"""
	if os.environ.get("FLASK_ENV") == "production":
		return
	from src.models.main import Family, Parent, generate_family_code
	if Parent.query.filter_by(email="admin@email.com").first():
		return
	family = Family(name="Admin Family")
	family.set_family_code(generate_family_code())
	admin = Parent(family=family, name="Admin", email="admin@email.com")
	admin.set_password("admin")
	admin.is_superuser = True
	admin.email_verified = True
	db.session.add(family)
	db.session.add(admin)
	db.session.commit()


def _start_scheduler(app: "Flask") -> None:
	"""Start APScheduler for background maintenance tasks."""
	try:
		from apscheduler.schedulers.background import BackgroundScheduler
	except ImportError:
		app.logger.warning("APScheduler not installed; background jobs disabled.")
		return

	scheduler = BackgroundScheduler(daemon=True)

	def run_daily_jobs():
		with app.app_context():
			_job_expire_trials()
			_job_trial_reminders()
			_job_purge_pending_devices()

	scheduler.add_job(run_daily_jobs, "interval", hours=12, id="daily_jobs")
	scheduler.start()


def _job_expire_trials() -> None:
	"""Downgrade families whose trial has ended without a Pro subscription."""
	from datetime import datetime as _dt
	from src.models.main import Family, db
	from src.utils.email import send_email
	import os

	expired = Family.query.filter(
		Family.trial_ends_at <= _dt.utcnow(),
		Family.plan == "free",
		Family.subscription_status == "trialing",
	).all()

	for family in expired:
		family.subscription_status = None
		db.session.commit()
		base_url = os.environ.get("APP_BASE_URL", "https://app.stewardwell.com")
		for parent in family.parents:
			html = (
				f"<p>Hi {parent.name},</p>"
				f"<p>Your Stewardwell Pro trial for <strong>{family.name}</strong> has ended. "
				f"Your account is now on the Free plan.</p>"
				f"<p><a href='{base_url}/billing/upgrade'>Upgrade to Pro</a> to restore unlimited access.</p>"
			)
			send_email(
				to_email=parent.email,
				to_name=parent.name,
				subject="Your Stewardwell Pro trial has ended",
				html_content=html,
			)


def _job_trial_reminders() -> None:
	"""Send a reminder email to families with 3 days left on their trial."""
	from datetime import datetime as _dt, timedelta as _td
	from src.models.main import Family, db
	from src.utils.email import send_email
	import os

	window_start = _dt.utcnow() + _td(days=2, hours=23)
	window_end = _dt.utcnow() + _td(days=3, hours=1)

	expiring = Family.query.filter(
		Family.trial_ends_at >= window_start,
		Family.trial_ends_at <= window_end,
		Family.plan == "free",
		Family.subscription_status == "trialing",
	).all()

	base_url = os.environ.get("APP_BASE_URL", "https://app.stewardwell.com")
	for family in expiring:
		for parent in family.parents:
			html = (
				f"<p>Hi {parent.name},</p>"
				f"<p>Your Stewardwell Pro trial for <strong>{family.name}</strong> ends in <strong>3 days</strong>.</p>"
				f"<p><a href='{base_url}/billing/upgrade'>Subscribe to Pro</a> to keep unlimited access.</p>"
			)
			send_email(
				to_email=parent.email,
				to_name=parent.name,
				subject="Your Stewardwell Pro trial ends in 3 days",
				html_content=html,
			)


def _job_purge_pending_devices() -> None:
	"""Delete long-expired pending device registration records."""
	from datetime import datetime as _dt, timedelta as _td
	from src.models.main import PendingDeviceRegistration, db

	cutoff = _dt.utcnow() - _td(hours=24)
	PendingDeviceRegistration.query.filter(
		PendingDeviceRegistration.expires_at < cutoff
	).delete()
	db.session.commit()
