from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response
from datetime import datetime
from functools import wraps
from src.models.base_model import db
from src.models.kid import Kid
from src.models.family import Family
from src.models.chore import Chore
from src.models.chore_assignment import ChoreAssignment
from src.models.store_item import StoreItem
from src.models.purchase import Purchase

kid_bp = Blueprint('kid', __name__)


def kid_login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'kid_id' not in session:
            flash('Please log in first!', 'error')
            return redirect(url_for('kid.kid_login_page'))
        return f(*args, **kwargs)
    return decorated_function


@kid_bp.route('/login', methods=['GET'])
def kid_login_page():
    # Get remembered kids from cookie
    remembered_kids = []
    remembered_kid_ids = request.cookies.get('remembered_kids', '')
    if remembered_kid_ids:
        kid_ids = [int(kid_id) for kid_id in remembered_kid_ids.split(',') if kid_id]
        remembered_kids = Kid.query.filter(Kid.id.in_(kid_ids)).all()
    
    return render_template('public/kid_login.html', remembered_kids=remembered_kids)


@kid_bp.route('/login', methods=['POST'])
def kid_login():
    family_code = request.form.get('family_code', '').strip().upper()
    pin = request.form.get('pin', '').strip()
    
    if not family_code or not pin:
        flash('Please enter both family code and PIN!', 'error')
        return redirect(url_for('kid.kid_login_page'))
    
    # Validate family code
    family = Family.query.filter_by(family_code=family_code).first()
    if not family:
        flash('Invalid family code!', 'error')
        return redirect(url_for('kid.kid_login_page'))
    
    # Find kid in this family
    kids_in_family = Kid.query.filter_by(family_id=family.id).all()
    authenticated_kid = None
    
    for kid in kids_in_family:
        if kid.check_pin(pin):
            authenticated_kid = kid
            break
    
    if not authenticated_kid:
        flash('Invalid PIN! Please try again.', 'error')
        return redirect(url_for('kid.kid_login_page'))
    
    # Set session
    session['kid_id'] = authenticated_kid.id
    session['kid_name'] = authenticated_kid.name
    session['family_id'] = family.id
    
    # Update remembered kids cookie
    response = make_response(redirect(url_for('kid.dashboard')))
    remembered_kid_ids = request.cookies.get('remembered_kids', '')
    kid_ids_list = [kid_id for kid_id in remembered_kid_ids.split(',') if kid_id]
    
    if str(authenticated_kid.id) not in kid_ids_list:
        kid_ids_list.append(str(authenticated_kid.id))
        response.set_cookie('remembered_kids', ','.join(kid_ids_list), max_age=30*24*60*60)  # 30 days
    
    flash(f'Welcome back, {authenticated_kid.name}! 🎉', 'success')
    return response


@kid_bp.route('/quick-login', methods=['POST'])
def quick_login():
    kid_id = request.form.get('kid_id')
    if not kid_id:
        flash('Invalid request!', 'error')
        return redirect(url_for('kid.kid_login_page'))
    
    kid = Kid.query.get(kid_id)
    if not kid:
        flash('Kid not found!', 'error')
        return redirect(url_for('kid.kid_login_page'))
    
    # Prompt for PIN
    session['quick_login_kid_id'] = kid_id
    return render_template('public/kid_quick_login_pin.html', kid=kid)


@kid_bp.route('/quick-login-verify', methods=['POST'])
def quick_login_verify():
    kid_id = session.get('quick_login_kid_id')
    pin = request.form.get('pin', '').strip()
    
    if not kid_id or not pin:
        flash('Invalid request!', 'error')
        return redirect(url_for('kid.kid_login_page'))
    
    kid = Kid.query.get(kid_id)
    if not kid or not kid.check_pin(pin):
        flash('Invalid PIN!', 'error')
        session.pop('quick_login_kid_id', None)
        return redirect(url_for('kid.kid_login_page'))
    
    # Set session
    session.pop('quick_login_kid_id', None)
    session['kid_id'] = kid.id
    session['kid_name'] = kid.name
    session['family_id'] = kid.family_id
    
    flash(f'Welcome back, {kid.name}! 🎉', 'success')
    return redirect(url_for('kid.dashboard'))


@kid_bp.route('/dashboard')
@kid_login_required
def dashboard():
    kid_id = session.get('kid_id')
    kid = Kid.query.get(kid_id)
    
    if not kid:
        flash('Kid not found!', 'error')
        session.clear()
        return redirect(url_for('kid.kid_login_page'))
    
    # Get all chores for family
    all_chores = Chore.query.filter_by(family_id=kid.family_id).all()
    
    # Filter available chores (check frequency and max_completions)
    available_chores = []
    for chore in all_chores:
        # Check if already has an in-progress assignment
        existing_in_progress = ChoreAssignment.query.filter_by(
            kid_id=kid_id, chore_id=chore.id, status='in-progress').first()
        if existing_in_progress:
            continue
        
        # Check if chore can be done based on frequency and max_completions
        if chore.can_be_done_by_kid(kid_id):
            available_chores.append(chore)
    
    # Get active assignments (in-progress)
    active_assignments = ChoreAssignment.query.filter_by(
        kid_id=kid_id, status='in-progress').all()
    
    # Get pending assignments (waiting for parent confirmation)
    pending_assignments = ChoreAssignment.query.filter_by(
        kid_id=kid_id, status='pending').all()
    
    return render_template('private/kiddos/dashboard.html',
                         kid=kid,
                         available_chores=available_chores,
                         active_assignments=active_assignments,
                         pending_assignments=pending_assignments)


@kid_bp.route('/pick-chore/<int:chore_id>', methods=['POST'])
@kid_login_required
def pick_chore(chore_id):
    kid_id = session.get('kid_id')
    chore = Chore.query.get(chore_id)
    
    if not chore:
        flash('Chore not found!', 'error')
        return redirect(url_for('kid.dashboard'))
    
    # Check if chore belongs to kid's family
    kid = Kid.query.get(kid_id)
    if chore.family_id != kid.family_id:
        flash('Invalid chore!', 'error')
        return redirect(url_for('kid.dashboard'))
    
    # Check if already has an in-progress assignment
    existing = ChoreAssignment.query.filter_by(
        kid_id=kid_id, chore_id=chore_id, status='in-progress').first()
    if existing:
        flash('You already have this chore!', 'error')
        return redirect(url_for('kid.dashboard'))
    
    # Check if chore can be done based on frequency and max_completions
    if not chore.can_be_done_by_kid(kid_id):
        flash('This chore cannot be done right now. Check the frequency limits!', 'error')
        return redirect(url_for('kid.dashboard'))
    
    # Create assignment
    assignment = ChoreAssignment(
        chore_id=chore_id,
        kid_id=kid_id,
        status='in-progress'
    )
    db.session.add(assignment)
    db.session.commit()
    
    flash(f'Great! You picked "{chore.name}"! Time to get to work! 💪', 'success')
    return redirect(url_for('kid.dashboard'))


@kid_bp.route('/complete-chore/<int:assignment_id>', methods=['POST'])
@kid_login_required
def complete_chore(assignment_id):
    kid_id = session.get('kid_id')
    assignment = ChoreAssignment.query.get(assignment_id)
    
    if not assignment:
        flash('Assignment not found!', 'error')
        return redirect(url_for('kid.dashboard'))
    
    # Verify assignment belongs to this kid
    if assignment.kid_id != kid_id:
        flash('Invalid assignment!', 'error')
        return redirect(url_for('kid.dashboard'))
    
    # Verify status is in-progress
    if assignment.status != 'in-progress':
        flash('This chore is already completed!', 'error')
        return redirect(url_for('kid.dashboard'))
    
    # Update to pending
    assignment.status = 'pending'
    assignment.completed_at = datetime.utcnow()
    db.session.commit()
    
    flash('Awesome job! 🎉 Your chore is waiting for parent approval!', 'success')
    return redirect(url_for('kid.dashboard'))


@kid_bp.route('/logout')
def logout():
    kid_name = session.get('kid_name', 'Kid')
    session.clear()
    flash(f'Bye {kid_name}! See you soon! 👋', 'success')
    return redirect(url_for('main.landing'))


@kid_bp.route('/store')
@kid_login_required
def store():
    kid_id = session.get('kid_id')
    kid = Kid.query.get(kid_id)
    
    if not kid:
        flash('Session expired. Please log in again!', 'error')
        return redirect(url_for('kid.kid_login_page'))
    
    # Get available store items for this family
    store_items = StoreItem.query.filter_by(
        family_id=kid.family_id,
        is_available=True
    ).order_by(StoreItem.coin_cost.asc()).all()
    
    return render_template('private/kiddos/store/index.html',
                         kid=kid,
                         store_items=store_items)


@kid_bp.route('/purchase/<int:item_id>', methods=['POST'])
@kid_login_required
def purchase_item(item_id):
    kid_id = session.get('kid_id')
    kid = Kid.query.get(kid_id)
    
    if not kid:
        flash('Session expired. Please log in again!', 'error')
        return redirect(url_for('kid.kid_login_page'))
    
    # Get the store item
    item = StoreItem.query.get(item_id)
    
    if not item:
        flash('Item not found!', 'error')
        return redirect(url_for('kid.store'))
    
    # Verify item belongs to same family and is available
    if item.family_id != kid.family_id:
        flash('Invalid item!', 'error')
        return redirect(url_for('kid.store'))
    
    if not item.is_available:
        flash('This item is no longer available!', 'error')
        return redirect(url_for('kid.store'))
    
    # Check if kid has enough coins
    if kid.coin_balance < item.coin_cost:
        flash('You don\'t have enough coins for this item! 😢', 'error')
        return redirect(url_for('kid.store'))
    
    # Deduct coins
    kid.coin_balance -= item.coin_cost
    
    # Create purchase record
    purchase = Purchase(
        kid_id=kid_id,
        item_id=item_id,
        coin_cost=item.coin_cost,
        status='pending'
    )
    
    try:
        db.session.add(purchase)
        db.session.commit()
        flash(f'🎉 You purchased "{item.name}"! Your parent will fulfill it soon. ({item.coin_cost} coins spent)', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Purchase failed. Please try again!', 'error')
    
    return redirect(url_for('kid.store'))
