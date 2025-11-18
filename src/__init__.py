import os
from flask import Flask
from flask_migrate import Migrate
from src.models.base_model import db

migrate = Migrate()


def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///stewardwell.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import models for migration
    from src.models import family, parent, kid, chore, chore_assignment, store_item, purchase
    
    # Register blueprints
    from src.controllers.routes import main_bp
    from src.controllers.auth_controller import auth_bp
    from src.controllers.parent_controller import parent_bp
    from src.controllers.kid_controller import kid_bp
    from src.controllers.chore_controller import chore_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(parent_bp, url_prefix='/parent')
    app.register_blueprint(kid_bp, url_prefix='/kid')
    app.register_blueprint(chore_bp, url_prefix='/chore')
    
    return app
