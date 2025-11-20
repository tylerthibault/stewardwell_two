import os
from urllib.parse import quote_plus
from flask import Flask
from flask_migrate import Migrate
from src.models.base_model import db

migrate = Migrate()


def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    
    # Database configuration - use MySQL in production, SQLite locally
    deployment_env = os.environ.get('DEPLOYMENT_ENV', 'development')
    
    if deployment_env == 'production':
        # Production MySQL database on CapRover
        mysql_user = os.environ.get('MYSQL_USER', 'root')
        mysql_password = os.environ.get('MYSQL_PASSWORD', '')
        mysql_host = os.environ.get('MYSQL_HOST', 'srv-captain--stewardwell-db')
        mysql_port = os.environ.get('MYSQL_PORT', '3306')
        mysql_database = os.environ.get('MYSQL_DATABASE', 'stewardwell')
        
        # URL-encode password to handle special characters
        encoded_password = quote_plus(mysql_password)
        
        # First, create the database if it doesn't exist
        try:
            import pymysql
            connection = pymysql.connect(
                host=mysql_host,
                port=int(mysql_port),
                user=mysql_user,
                password=mysql_password
            )
            with connection.cursor() as cursor:
                cursor.execute(f"CREATE DATABASE IF NOT EXISTS {mysql_database}")
            connection.commit()
            connection.close()
            print(f"[DATABASE] Ensured database '{mysql_database}' exists")
        except Exception as e:
            print(f"[DATABASE] Warning: Could not create database: {e}")
        
        app.config['SQLALCHEMY_DATABASE_URI'] = f'mysql+pymysql://{mysql_user}:{encoded_password}@{mysql_host}:{mysql_port}/{mysql_database}'
        
        # MySQL connection pool settings
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 10,
            'pool_recycle': 3600,
            'pool_pre_ping': True,
        }
        
        # Log database connection info (without password)
        print(f"[DATABASE] Using MySQL: {mysql_user}@{mysql_host}:{mysql_port}/{mysql_database}")
    else:
        # Local development SQLite database
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stewardwell.db'
        print(f"[DATABASE] Using SQLite: stewardwell.db")
    
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Import models for migration
    from src.models import family, parent, kid, chore, chore_assignment, store_item, purchase
    
    # Auto-create tables and apply schema updates
    with app.app_context():
        try:
            db.create_all()
            print("[DATABASE] Tables initialized successfully")
            
            # Apply column migrations for existing tables
            from sqlalchemy import inspect, Text
            inspector = inspect(db.engine)
            
            # Check if description column exists in chore table
            chore_columns = [col['name'] for col in inspector.get_columns('chore')]
            if 'description' not in chore_columns:
                print("[DATABASE] Adding 'description' column to chore table...")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE chore ADD COLUMN description TEXT'))
                    conn.commit()
                print("[DATABASE] Description column added to chore table")
            
            # Check if tags column exists in chore table
            if 'tags' not in chore_columns:
                print("[DATABASE] Adding 'tags' column to chore table...")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE chore ADD COLUMN tags VARCHAR(500)'))
                    conn.commit()
                print("[DATABASE] Tags column added to chore table")
            
        except Exception as e:
            print(f"[DATABASE] Warning: Could not auto-create tables: {e}")
    
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
