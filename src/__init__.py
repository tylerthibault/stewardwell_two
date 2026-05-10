from flask import Flask
from sqlalchemy import inspect, text

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

	if "kids" in table_names:
		kid_columns = {column["name"] for column in inspector.get_columns("kids")}
		if "coin_balance" not in kid_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE kids ADD COLUMN coin_balance INTEGER NOT NULL DEFAULT 0"))

	if "trusted_devices" in table_names:
		device_columns = {column["name"] for column in inspector.get_columns("trusted_devices")}
		if "user_agent_hash" not in device_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE trusted_devices ADD COLUMN user_agent_hash VARCHAR(64)"))
		if "ip_hash" not in device_columns:
			with db.engine.begin() as connection:
				connection.execute(text("ALTER TABLE trusted_devices ADD COLUMN ip_hash VARCHAR(64)"))

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


def create_app() -> Flask:
	app = Flask(__name__)
	app.config["SECRET_KEY"] = "dev-secret-key"
	app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///stewardwell.db"
	app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

	from src.controllers.routes import public_bp
	from src.controllers.parent_controller import parent_bp
	from src.controllers.kid_controller import kid_bp

	db.init_app(app)
	app.register_blueprint(public_bp)
	app.register_blueprint(parent_bp)
	app.register_blueprint(kid_bp)

	with app.app_context():
		db.create_all()
		_apply_sqlite_schema_fixes()

	return app
