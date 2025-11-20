#!/usr/bin/env python3
"""
Database migration script for CapRover deployment
Automatically runs Flask-Migrate to upgrade database schema
"""

import os
import sys
from flask_migrate import upgrade
from src import create_app

def run_migrations():
    """Run all pending database migrations"""
    
    print("=" * 60)
    print("Starting Database Migration")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            print("\n🔄 Running database migrations...")
            
            # Run all pending migrations
            upgrade()
            
            print("✅ Database migrations completed successfully!")
            print("=" * 60)
            return 0
            
        except Exception as e:
            print(f"\n❌ Migration failed: {e}")
            print("=" * 60)
            import traceback
            traceback.print_exc()
            return 1

if __name__ == '__main__':
    sys.exit(run_migrations())
