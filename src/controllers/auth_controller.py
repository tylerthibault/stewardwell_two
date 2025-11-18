from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from src.models.base_model import db
from src.models.parent import Parent
from src.models.family import Family

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        family_name = request.form.get('family_name', '').strip()
        
        # Validation
        if not email or not password or not family_name:
            flash('All fields are required.', 'error')
            return render_template('public/auth/register/index.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('public/auth/register/index.html')
        
        # Check if email already exists
        existing_parent = Parent.query.filter_by(email=email).first()
        if existing_parent:
            flash('Email already registered. Please login.', 'error')
            return redirect(url_for('auth.login'))
        
        # Create family
        new_family = Family(
            name=family_name,
            family_code=Family.generate_family_code()
        )
        db.session.add(new_family)
        db.session.flush()  # Get family ID before committing
        
        # Create parent (as head of family)
        new_parent = Parent(
            family_id=new_family.id,
            email=email,
            is_head=True
        )
        new_parent.set_password(password)
        db.session.add(new_parent)
        
        try:
            db.session.commit()
            
            # Auto-login after registration
            session['parent_id'] = new_parent.id
            session['family_id'] = new_family.id
            
            flash(f'Welcome to Stewardwell, {family_name} family!', 'success')
            return redirect(url_for('parent.dashboard'))
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
            return render_template('public/auth/register/index.html')
    
    return render_template('public/auth/register/index.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        # Validation
        if not email or not password:
            flash('Email and password are required.', 'error')
            return render_template('public/auth/login/index.html')
        
        # Find parent by email
        parent = Parent.query.filter_by(email=email).first()
        
        if not parent or not parent.check_password(password):
            flash('Invalid email or password.', 'error')
            return render_template('public/auth/login/index.html')
        
        # Set session
        session['parent_id'] = parent.id
        session['family_id'] = parent.family_id
        
        flash('Login successful!', 'success')
        return redirect(url_for('parent.dashboard'))
    
    return render_template('public/auth/login/index.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('main.landing'))
