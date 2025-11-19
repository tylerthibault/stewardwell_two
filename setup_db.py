#!/usr/bin/env python3
"""
Database setup script for CapRover deployment
Run this after deployment to create database and tables
"""

import os
import sys
from src import create_app, db
from sqlalchemy import text

def setup_database():
    """Initialize database and create all tables"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Test database connection
            print("Testing database connection...")
            connection = db.engine.connect()
            print("✓ Database connection successful!")
            
            # For MySQL, try to create database if it doesn't exist
            deployment_env = os.environ.get('DEPLOYMENT_ENV', 'development')
            if deployment_env == 'production':
                try:
                    mysql_database = os.environ.get('MYSQL_DATABASE', 'stewardwell')
                    print(f"\nEnsuring database '{mysql_database}' exists...")
                    connection.execute(text(f"CREATE DATABASE IF NOT EXISTS {mysql_database} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
                    connection.execute(text(f"USE {mysql_database}"))
                    print(f"✓ Database '{mysql_database}' ready!")
                except Exception as e:
                    print(f"Note: Could not create database (may already exist): {e}")
            
            connection.close()
            
            # Create all tables
            print("\nCreating database tables...")
            db.create_all()
            print("✓ All tables created successfully!")
            
            # List all tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"\n✓ Created {len(tables)} tables:")
            for table in tables:
                print(f"  - {table}")
            
            print("\n✓ Database setup complete!")
            return True
            
        except Exception as e:
            print(f"\n✗ Database setup failed: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == '__main__':
    success = setup_database()
    sys.exit(0 if success else 1)
