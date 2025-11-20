"""
Database seeding script for development environment.
Creates sample families, parents, kids, chores, and store items.
"""

from src import create_app, db
from src.models.family import Family
from src.models.parent import Parent
from src.models.kid import Kid
from src.models.chore import Chore
from src.models.store_item import StoreItem
from src.models.chore_assignment import ChoreAssignment
from datetime import datetime, timedelta
import random
import os


def clear_database():
    """Clear all data from the database"""
    print("🗑️  Clearing database...")
    db.drop_all()
    db.create_all()
    print("✅ Database cleared and tables recreated")


def seed_families():
    """Create sample families"""
    print("\n👨‍👩‍👧‍👦 Creating families...")
    
    families_data = [
        {"name": "Thibault", "code": "THIBA1"},
        {"name": "Johnsons", "code": "JOHNS2"},
        {"name": "Williams", "code": "WILLI3"},
    ]
    
    families = []
    for data in families_data:
        family = Family(name=data["name"], family_code=data["code"])
        db.session.add(family)
        families.append(family)
        print(f"  ✓ Created family: {data['name']} (Code: {data['code']})")
    
    db.session.commit()
    return families


def seed_parents(families):
    """Create sample parents for each family"""
    print("\n👨‍💼 Creating parents...")
    
    parents = []
    for i, family in enumerate(families):
        # Create head parent
        if i == 0:
            # First family - Tyler's account
            parent = Parent(
                family_id=family.id,
                email="tyler.thibault@protonmail.com",
                is_head=True
            )
            parent.set_password("lava crispy english")
        else:
            parent = Parent(
                family_id=family.id,
                email=f"parent{i+1}@example.com",
                is_head=True
            )
            parent.set_password("password123")
        
        db.session.add(parent)
        parents.append(parent)
        print(f"  ✓ Created parent: {parent.email} (Head of {family.name})")
    
    db.session.commit()
    return parents


def seed_kids(families):
    """Create sample kids for each family"""
    print("\n👧👦 Creating kids...")
    
    kids_data = [
        ["Theo", "Z"],
        ["Noah", "Sophia"],
        ["Ava", "Mason", "Isabella", "Ethan"],
    ]
    
    all_kids = []
    for i, family in enumerate(families):
        kids_names = kids_data[i]
        for name in kids_names:
            kid = Kid(
                family_id=family.id,
                name=name,
                coin_balance=random.randint(10, 100)
            )
            kid.set_pin("1234")  # Default PIN for all kids in dev
            db.session.add(kid)
            all_kids.append(kid)
            print(f"  ✓ Created kid: {name} (Family: {family.name}, PIN: 1234, Coins: {kid.coin_balance})")
    
    db.session.commit()
    return all_kids


def seed_chores(families, parents):
    """Create sample chores with tags"""
    print("\n🧹 Creating chores...")
    
    chores_data = [
        {
            "name": "Clean bedroom",
            "description": "Make bed, put away toys, vacuum floor",
            "tags": "cleaning,daily,indoor",
            "coin_value": 10,
            "point_value": 1,
            "frequency": "daily"
        },
        {
            "name": "Do the dishes",
            "description": "Wash, dry, and put away all dishes",
            "tags": "cleaning,kitchen,daily",
            "coin_value": 15,
            "point_value": 2,
            "frequency": "daily"
        },
        {
            "name": "Take out trash",
            "description": "Empty all trash cans and take to curb",
            "tags": "cleaning,outdoor,weekly",
            "coin_value": 5,
            "point_value": 1,
            "frequency": "weekly"
        },
        {
            "name": "Vacuum living room",
            "description": "Vacuum all carpeted areas in living room",
            "tags": "cleaning,indoor",
            "coin_value": 12,
            "point_value": 1,
            "frequency": "weekly"
        },
        {
            "name": "Feed the pet",
            "description": "Give food and fresh water to pet",
            "tags": "pets,daily",
            "coin_value": 5,
            "point_value": 1,
            "frequency": "daily"
        },
        {
            "name": "Mow the lawn",
            "description": "Mow front and back yard",
            "tags": "outdoor,yard,weekly",
            "coin_value": 25,
            "point_value": 3,
            "frequency": "weekly"
        },
        {
            "name": "Homework help",
            "description": "Complete all homework assignments",
            "tags": "school,daily",
            "coin_value": 10,
            "point_value": 2,
            "frequency": "daily"
        },
        {
            "name": "Water plants",
            "description": "Water all indoor and outdoor plants",
            "tags": "outdoor,garden",
            "coin_value": 8,
            "point_value": 1,
            "frequency": "unlimited"
        },
        {
            "name": "Sort laundry",
            "description": "Sort clothes into whites, colors, and delicates",
            "tags": "cleaning,laundry",
            "coin_value": 10,
            "point_value": 1,
            "frequency": "unlimited"
        },
        {
            "name": "Clean bathroom",
            "description": "Scrub toilet, sink, and shower/tub",
            "tags": "cleaning,bathroom,weekly",
            "coin_value": 20,
            "point_value": 2,
            "frequency": "weekly"
        },
        {
            "name": "Organize toy room",
            "description": "Put all toys in proper bins and shelves",
            "tags": "organizing,indoor",
            "coin_value": 15,
            "point_value": 1,
            "frequency": "one_time"
        },
        {
            "name": "Read for 30 minutes",
            "description": "Read any book for at least 30 minutes",
            "tags": "school,educational,daily",
            "coin_value": 5,
            "point_value": 2,
            "frequency": "daily"
        },
    ]
    
    all_chores = []
    for i, family in enumerate(families):
        # Get parent for this family
        parent = [p for p in parents if p.family_id == family.id][0]
        
        # Create 6-8 random chores per family
        num_chores = random.randint(6, 8)
        selected_chores = random.sample(chores_data, num_chores)
        
        for chore_data in selected_chores:
            chore = Chore(
                family_id=family.id,
                name=chore_data["name"],
                description=chore_data["description"],
                tags=chore_data["tags"],
                coin_value=chore_data["coin_value"],
                point_value=chore_data["point_value"],
                frequency=chore_data["frequency"],
                created_by_parent_id=parent.id,
                is_active=random.choice([True, True, True, False])  # 75% active
            )
            db.session.add(chore)
            all_chores.append(chore)
            status = "✅" if chore.is_active else "❌"
            print(f"  {status} Created chore: {chore.name} (Family: {family.name}, Tags: {chore.tags})")
    
    db.session.commit()
    return all_chores


def seed_store_items(families):
    """Create sample store items"""
    print("\n🛍️  Creating store items...")
    
    store_items_data = [
        {
            "name": "Extra Screen Time (30 min)",
            "description": "Redeem for 30 minutes of extra screen time",
            "tags": "screentime,entertainment",
            "coin_cost": 25
        },
        {
            "name": "Ice Cream Trip",
            "description": "Family trip to ice cream shop",
            "tags": "treats,outing",
            "coin_cost": 50
        },
        {
            "name": "Movie Night Choice",
            "description": "Pick the movie for family movie night",
            "tags": "entertainment,family",
            "coin_cost": 30
        },
        {
            "name": "Skip One Chore",
            "description": "Skip any chore of your choice (one time)",
            "tags": "special,privilege",
            "coin_cost": 40
        },
        {
            "name": "Sleepover with Friend",
            "description": "Have a friend stay overnight",
            "tags": "social,special",
            "coin_cost": 75
        },
        {
            "name": "New Book",
            "description": "Choose any book from the bookstore",
            "tags": "educational,shopping",
            "coin_cost": 35
        },
        {
            "name": "Pizza for Dinner",
            "description": "Family orders pizza for dinner",
            "tags": "treats,food,family",
            "coin_cost": 45
        },
        {
            "name": "Stay Up Late (1 hour)",
            "description": "Stay up one hour past normal bedtime",
            "tags": "privilege,bedtime",
            "coin_cost": 20
        },
        {
            "name": "New Toy (Small)",
            "description": "Choose a small toy (under $10)",
            "tags": "shopping,toys",
            "coin_cost": 100
        },
        {
            "name": "Day Trip Adventure",
            "description": "Family day trip to your choice of location",
            "tags": "outing,special,family",
            "coin_cost": 150
        },
    ]
    
    all_items = []
    for family in families:
        # Create 5-8 random items per family
        num_items = random.randint(5, 8)
        selected_items = random.sample(store_items_data, num_items)
        
        for item_data in selected_items:
            item = StoreItem(
                family_id=family.id,
                name=item_data["name"],
                description=item_data["description"],
                tags=item_data["tags"],
                coin_cost=item_data["coin_cost"],
                is_available=random.choice([True, True, True, False])  # 75% available
            )
            db.session.add(item)
            all_items.append(item)
            status = "✅" if item.is_available else "❌"
            print(f"  {status} Created item: {item.name} (Cost: {item.coin_cost} coins, Tags: {item.tags})")
    
    db.session.commit()
    return all_items


def seed_chore_assignments(chores, kids):
    """Create sample chore assignments with various statuses"""
    print("\n📋 Creating chore assignments...")
    
    statuses = ['pending', 'completed', 'confirmed']
    all_assignments = []
    
    for chore in chores:
        # Get kids from same family
        family_kids = [k for k in kids if k.family_id == chore.family_id]
        
        # Create 1-3 assignments per chore
        num_assignments = random.randint(0, 3)
        for _ in range(num_assignments):
            kid = random.choice(family_kids)
            status = random.choice(statuses)
            
            # Create assignment with timestamp in past week
            days_ago = random.randint(0, 7)
            assigned_date = datetime.utcnow() - timedelta(days=days_ago)
            
            assignment = ChoreAssignment(
                chore_id=chore.id,
                kid_id=kid.id,
                status=status,
                created_at=assigned_date
            )
            
            # Add completion/confirmation timestamps for appropriate statuses
            if status in ['completed', 'confirmed']:
                assignment.completed_at = assigned_date + timedelta(hours=random.randint(1, 12))
            
            if status == 'confirmed':
                assignment.confirmed_at = assignment.completed_at + timedelta(hours=random.randint(1, 24))
                assignment.confirmed_by_parent_id = chore.created_by_parent_id
            
            db.session.add(assignment)
            all_assignments.append(assignment)
            
            emoji = {"pending": "⏳", "completed": "✅", "confirmed": "🎉"}[status]
            print(f"  {emoji} Created assignment: {chore.name} → {kid.name} ({status})")
    
    db.session.commit()
    return all_assignments


def print_summary(families, parents, kids, chores, store_items, assignments):
    """Print summary of seeded data"""
    print("\n" + "="*60)
    print("🎉 DATABASE SEEDING COMPLETE!")
    print("="*60)
    print(f"\n📊 Summary:")
    print(f"  • {len(families)} families created")
    print(f"  • {len(parents)} parents created")
    print(f"  • {len(kids)} kids created")
    print(f"  • {len(chores)} chores created")
    print(f"  • {len(store_items)} store items created")
    print(f"  • {len(assignments)} chore assignments created")
    
    print(f"\n🔐 Login Credentials:")
    for parent in parents:
        family = next(f for f in families if f.id == parent.family_id)
        password = "lava crispy english" if parent.email == "tyler.thibault@protonmail.com" else "password123"
        print(f"  • {parent.email} / {password} ({family.name})")
    
    print(f"\n👶 Kid PINs:")
    print(f"  • All kids use PIN: 1234")
    
    print(f"\n🔢 Family Codes:")
    for family in families:
        print(f"  • {family.name}: {family.family_code}")
    
    print("\n" + "="*60)


def seed_database(clear=True):
    """Main seeding function"""
    app = create_app()
    
    with app.app_context():
        if clear:
            clear_database()
        
        # Seed data in order
        families = seed_families()
        parents = seed_parents(families)
        kids = seed_kids(families)
        chores = seed_chores(families, parents)
        store_items = seed_store_items(families)
        assignments = seed_chore_assignments(chores, kids)
        
        # Print summary
        print_summary(families, parents, kids, chores, store_items, assignments)


if __name__ == '__main__':
    import sys
    
    # Only allow seeding in development environment
    deployment_env = os.environ.get('DEPLOYMENT_ENV', 'development')
    if deployment_env == 'production':
        print("❌ ERROR: Cannot run seed script in production environment!")
        print("   This script is only for development databases.")
        sys.exit(1)
    
    # Check for --no-clear flag
    clear = '--no-clear' not in sys.argv
    
    seed_database(clear=clear)
