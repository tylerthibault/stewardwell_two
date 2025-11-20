"""
Apply the database migration to add description column to chores.
Run this script after deploying the new code.
"""
from src import create_app
from src.models.base_model import db

app = create_app()

with app.app_context():
    try:
        # Add description column if it doesn't exist
        from sqlalchemy import inspect, Text
        inspector = inspect(db.engine)
        columns = [col['name'] for col in inspector.get_columns('chore')]
        
        if 'description' not in columns:
            print("Adding 'description' column to chore table...")
            with db.engine.connect() as conn:
                conn.execute(db.text('ALTER TABLE chore ADD COLUMN description TEXT'))
                conn.commit()
            print("✓ Description column added successfully!")
        else:
            print("✓ Description column already exists")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        print("\nYou can also run this SQL manually:")
        print("ALTER TABLE chore ADD COLUMN description TEXT;")
