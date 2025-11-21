from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import random
from datetime import datetime
from src.models.base_model import db
from src.models.parent import Parent
from src.models.kid import Kid
from src.models.chore import Chore
from src.models.chore_assignment import ChoreAssignment
from src.models.family import Family
from src.models.store_item import StoreItem
from src.models.purchase import Purchase
from src.utils.auth_decorators import login_required

parent_bp = Blueprint('parent', __name__)


@parent_bp.route('/dashboard')
@parent_bp.route('/dashboard/<int:num>')
@login_required
def dashboard(num=None):
    parent_id = session.get('parent_id')
    family_id = session.get('family_id')
    
    # Get parent and family info
    parent = Parent.query.get(parent_id)
    family = Family.query.get(family_id)
    
    if not parent or not family:
        flash('Session expired. Please login again.', 'error')
        return redirect(url_for('auth.login'))
    
    # Get all kids in family
    kids = Kid.query.filter_by(family_id=family_id).order_by(Kid.created_at.desc()).all()
    
    # Get all chores in family
    chores = Chore.query.filter_by(family_id=family_id).order_by(Chore.created_at.desc()).all()
    
    # Get pending chore assignments (waiting for parent confirmation)
    pending_assignments = ChoreAssignment.query.join(Kid).filter(
        Kid.family_id == family_id,
        ChoreAssignment.status == 'pending'
    ).order_by(ChoreAssignment.completed_at.desc()).all()
    
    # Get store items
    store_items = StoreItem.query.filter_by(family_id=family_id).order_by(StoreItem.created_at.desc()).all()
    
    # Get pending purchases
    pending_purchases = Purchase.query.join(Kid).filter(
        Kid.family_id == family_id,
        Purchase.status == 'pending'
    ).order_by(Purchase.purchased_at.desc()).all()
    
    if not num:
        return render_template('private/parents/dashboard/index.html',
                         parent=parent,
                         family=family,
                         kids=kids,
                         chores=chores,
                         pending_assignments=pending_assignments,
                         store_items=store_items,
                         pending_purchases=pending_purchases)
    else:
        return render_template(f'private/parents/dashboard/index{num}.html',
                         parent=parent,
                         family=family,
                         kids=kids,
                         chores=chores,
                         pending_assignments=pending_assignments,
                         store_items=store_items,
                         pending_purchases=pending_purchases)


@parent_bp.route('/chores')
@login_required
def chores():
    family_id = session.get('family_id')
    
    # Get all chores in family
    chores = Chore.query.filter_by(family_id=family_id).order_by(Chore.created_at.desc()).all()
    
    return render_template('private/parents/chores/index.html', chores=chores)


@parent_bp.route('/store')
@login_required
def store():
    family_id = session.get('family_id')
    
    # Get all store items
    store_items = StoreItem.query.filter_by(family_id=family_id).order_by(StoreItem.created_at.desc()).all()
    
    return render_template('private/parents/store/index.html', store_items=store_items)


@parent_bp.route('/add-kid', methods=['GET', 'POST'])
@login_required
def add_kid():
    if request.method == 'POST':
        family_id = session.get('family_id')
        kid_name = request.form.get('name', '').strip()
        custom_pin = request.form.get('custom_pin', '').strip()
        use_random_pin = request.form.get('use_random_pin') == 'true'
        
        # Validation
        if not kid_name:
            return jsonify({'success': False, 'message': 'Kid name is required.'}), 400
        
        # Handle PIN: use custom or generate random 4-digit PIN
        if use_random_pin or not custom_pin:
            pin = ''.join([str(random.randint(0, 9)) for _ in range(4)])
        else:
            # Validate custom PIN (must be 4 digits)
            if not custom_pin.isdigit() or len(custom_pin) != 4:
                return jsonify({'success': False, 'message': 'PIN must be exactly 4 digits.'}), 400
            pin = custom_pin
        
        # Create kid
        new_kid = Kid(
            family_id=family_id,
            name=kid_name
        )
        new_kid.set_pin(pin)
        
        try:
            db.session.add(new_kid)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Kid "{kid_name}" added successfully! Their PIN is: {pin}. Please write this down - it will not be shown again.',
                'kid': {
                    'id': new_kid.id,
                    'name': new_kid.name,
                    'coin_balance': new_kid.coin_balance
                },
                'pin': pin
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Failed to add kid. Please try again.'}), 500
    
    return redirect(url_for('parent.dashboard'))


@parent_bp.route('/create-chore', methods=['GET', 'POST'])
@login_required
def create_chore():
    if request.method == 'POST':
        family_id = session.get('family_id')
        parent_id = session.get('parent_id')
        
        chore_name = request.form.get('name', '').strip()
        description = request.form.get('description', '').strip()
        tags = request.form.get('tags', '').strip()
        coin_value = request.form.get('coin_value', '0').strip()
        point_value = request.form.get('point_value', '0').strip()
        frequency = request.form.get('frequency', 'unlimited').strip()
        is_active = request.form.get('is_active', 'on') == 'on'
        
        # Validation
        if not chore_name:
            return jsonify({'success': False, 'message': 'Chore name is required.'}), 400
        
        # Validate frequency
        valid_frequencies = ['unlimited', 'daily', 'weekly', 'monthly', 'one_time']
        if frequency not in valid_frequencies:
            return jsonify({'success': False, 'message': 'Invalid frequency selected.'}), 400
        
        try:
            coin_value = int(coin_value)
            point_value = int(point_value)
            
            if coin_value < 0 or point_value < 0:
                return jsonify({'success': False, 'message': 'Coin and point values must be non-negative.'}), 400
        except ValueError:
            return jsonify({'success': False, 'message': 'Coin and point values must be valid numbers.'}), 400
        
        # Create chore
        new_chore = Chore(
            family_id=family_id,
            name=chore_name,
            description=description if description else None,
            tags=tags if tags else None,
            coin_value=coin_value,
            point_value=point_value,
            created_by_parent_id=parent_id,
            frequency=frequency,
            is_active=is_active
        )
        
        try:
            db.session.add(new_chore)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Chore "{chore_name}" created successfully!',
                'chore_id': new_chore.id
            })
        except Exception as e:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Failed to create chore. Please try again.'}), 500
    
    return redirect(url_for('parent.chores'))


@parent_bp.route('/toggle-chore/<int:chore_id>', methods=['POST'])
@login_required
def toggle_chore(chore_id):
    family_id = session.get('family_id')
    
    chore = Chore.query.get(chore_id)
    
    if not chore:
        return jsonify({'success': False, 'message': 'Chore not found.'}), 404
    
    # Verify chore belongs to this family
    if chore.family_id != family_id:
        return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
    
    # Toggle active status
    chore.is_active = not chore.is_active
    
    try:
        db.session.commit()
        status = 'active' if chore.is_active else 'inactive'
        return jsonify({
            'success': True,
            'message': f'"{chore.name}" is now {status}.',
            'is_active': chore.is_active
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to update chore. Please try again.'}), 500


@parent_bp.route('/edit-chore/<int:chore_id>', methods=['POST'])
@login_required
def edit_chore(chore_id):
    family_id = session.get('family_id')
    
    chore = Chore.query.get(chore_id)
    
    if not chore:
        return jsonify({'success': False, 'message': 'Chore not found.'}), 404
    
    # Verify chore belongs to this family
    if chore.family_id != family_id:
        return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
    
    chore_name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    tags = request.form.get('tags', '').strip()
    coin_value = request.form.get('coin_value', '0').strip()
    point_value = request.form.get('point_value', '0').strip()
    frequency = request.form.get('frequency', 'unlimited').strip()
    is_active = request.form.get('is_active', 'on') == 'on'
    
    # Validation
    if not chore_name:
        return jsonify({'success': False, 'message': 'Chore name is required.'}), 400
    
    # Validate frequency
    valid_frequencies = ['unlimited', 'daily', 'weekly', 'monthly', 'one_time']
    if frequency not in valid_frequencies:
        return jsonify({'success': False, 'message': 'Invalid frequency selected.'}), 400
    
    try:
        coin_value = int(coin_value)
        point_value = int(point_value)
        
        if coin_value < 0 or point_value < 0:
            return jsonify({'success': False, 'message': 'Coin and point values must be non-negative.'}), 400
    except ValueError:
        return jsonify({'success': False, 'message': 'Coin and point values must be valid numbers.'}), 400
    
    # Update chore
    chore.name = chore_name
    chore.description = description if description else None
    chore.tags = tags if tags else None
    chore.coin_value = coin_value
    chore.point_value = point_value
    chore.frequency = frequency
    chore.is_active = is_active
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Chore "{chore_name}" updated successfully!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to update chore. Please try again.'}), 500


@parent_bp.route('/delete-chore/<int:chore_id>', methods=['POST'])
@login_required
def delete_chore(chore_id):
    family_id = session.get('family_id')
    
    chore = Chore.query.get(chore_id)
    
    if not chore:
        return jsonify({'success': False, 'message': 'Chore not found.'}), 404
    
    # Verify chore belongs to this family
    if chore.family_id != family_id:
        return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
    
    chore_name = chore.name
    
    try:
        db.session.delete(chore)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Chore "{chore_name}" deleted successfully.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to delete chore. Please try again.'}), 500

@parent_bp.route('/confirm-chore/<int:assignment_id>', methods=['POST'])
@login_required
def confirm_chore(assignment_id):
    parent_id = session.get('parent_id')
    family_id = session.get('family_id')
    
    # Get the assignment
    assignment = ChoreAssignment.query.get(assignment_id)
    
    if not assignment:
        return jsonify({'success': False, 'message': 'Chore assignment not found.'}), 404
    
    # Verify assignment belongs to this family
    if assignment.kid.family_id != family_id:
        return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
    
    # Check if already confirmed
    if assignment.status == 'confirmed':
        return jsonify({'success': False, 'message': 'Chore already confirmed.'}), 400
    
    # Get coin adjustment if any
    coin_adjustment = request.form.get('coin_adjustment', None)
    
    if coin_adjustment is not None:
        try:
            coin_adjustment = int(coin_adjustment)
        except ValueError:
            coin_adjustment = assignment.chore.coin_value
    else:
        coin_adjustment = assignment.chore.coin_value
    
    # Update assignment
    assignment.status = 'confirmed'
    assignment.confirmed_by_parent_id = parent_id
    
    # Award coins to kid
    assignment.kid.coin_balance += coin_adjustment
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Chore confirmed! {assignment.kid.name} earned {coin_adjustment} coins.',
            'kid_id': assignment.kid.id,
            'new_balance': assignment.kid.coin_balance
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to confirm chore. Please try again.'}), 500


@parent_bp.route('/reject-chore/<int:assignment_id>', methods=['POST'])
@login_required
def reject_chore(assignment_id):
    family_id = session.get('family_id')
    
    # Get the assignment
    assignment = ChoreAssignment.query.get(assignment_id)
    
    if not assignment:
        return jsonify({'success': False, 'message': 'Chore assignment not found.'}), 404
    
    # Verify assignment belongs to this family
    if assignment.kid.family_id != family_id:
        return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
    
    # Update assignment
    assignment.status = 'rejected'
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Chore rejected.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to reject chore. Please try again.'}), 500


@parent_bp.route('/reset-pin/<int:kid_id>', methods=['POST'])
@login_required
def reset_pin(kid_id):
    family_id = session.get('family_id')
    custom_pin = request.form.get('custom_pin', '').strip()
    use_random_pin = request.form.get('use_random_pin') == 'true'
    
    # Get the kid
    kid = Kid.query.get(kid_id)
    
    if not kid:
        return jsonify({'success': False, 'message': 'Kid not found.'}), 404
    
    # Verify kid belongs to this family
    if kid.family_id != family_id:
        return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
    
    # Handle PIN: use custom or generate random 4-digit PIN
    if use_random_pin or not custom_pin:
        new_pin = ''.join([str(random.randint(0, 9)) for _ in range(4)])
    else:
        # Validate custom PIN (must be 4 digits)
        if not custom_pin.isdigit() or len(custom_pin) != 4:
            return jsonify({'success': False, 'message': 'PIN must be exactly 4 digits.'}), 400
        new_pin = custom_pin
    
    kid.set_pin(new_pin)
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'PIN reset for {kid.name}! New PIN is: {new_pin}. Please write this down - it will not be shown again.',
            'pin': new_pin
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to reset PIN. Please try again.'}), 500


@parent_bp.route('/adjust-coins/<int:kid_id>', methods=['POST'])
@login_required
def adjust_coins(kid_id):
    family_id = session.get('family_id')
    
    # Get the kid
    kid = Kid.query.get(kid_id)
    
    if not kid:
        return jsonify({'success': False, 'message': 'Kid not found.'}), 404
    
    # Verify kid belongs to this family
    if kid.family_id != family_id:
        return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
    
    # Get action (add/subtract) and amount
    action = request.form.get('action', 'add')
    try:
        amount = int(request.form.get('amount', 0))
        if amount <= 0:
            return jsonify({'success': False, 'message': 'Amount must be greater than zero.'}), 400
    except ValueError:
        return jsonify({'success': False, 'message': 'Invalid amount.'}), 400
    
    reason = request.form.get('reason', '').strip()
    
    # Calculate adjustment based on action
    if action == 'subtract':
        adjustment = -amount
    else:
        adjustment = amount
    
    # Update kid's coin balance
    kid.coin_balance += adjustment
    
    # Prevent negative balance
    if kid.coin_balance < 0:
        kid.coin_balance = 0
    
    try:
        db.session.commit()
        
        # Create message
        if adjustment > 0:
            message = f'Added {adjustment} coins to {kid.name}\'s balance!'
        else:
            message = f'Removed {abs(adjustment)} coins from {kid.name}\'s balance!'
        
        if reason:
            message += f' Reason: {reason}'
        
        return jsonify({
            'success': True,
            'message': message,
            'kid_id': kid.id,
            'new_balance': kid.coin_balance
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to adjust coins. Please try again.'}), 500


@parent_bp.route('/add-store-item', methods=['POST'])
@login_required
def add_store_item():
    family_id = session.get('family_id')
    
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    tags = request.form.get('tags', '').strip()
    coin_cost = request.form.get('coin_cost', '0').strip()
    
    # Validation
    if not name:
        return jsonify({'success': False, 'message': 'Item name is required.'}), 400
    
    try:
        coin_cost = int(coin_cost)
        if coin_cost < 0:
            return jsonify({'success': False, 'message': 'Coin cost must be non-negative.'}), 400
    except ValueError:
        return jsonify({'success': False, 'message': 'Coin cost must be a valid number.'}), 400
    
    # Create store item
    new_item = StoreItem(
        family_id=family_id,
        name=name,
        description=description,
        tags=tags if tags else None,
        coin_cost=coin_cost,
        is_available=True
    )
    
    try:
        db.session.add(new_item)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Store item "{name}" added successfully!',
            'item_id': new_item.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to add store item. Please try again.'}), 500


@parent_bp.route('/edit-store-item/<int:item_id>', methods=['POST'])
@login_required
def edit_store_item(item_id):
    family_id = session.get('family_id')
    
    item = StoreItem.query.get(item_id)
    
    if not item:
        return jsonify({'success': False, 'message': 'Store item not found.'}), 404
    
    # Verify item belongs to this family
    if item.family_id != family_id:
        return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
    
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    tags = request.form.get('tags', '').strip()
    coin_cost = request.form.get('coin_cost', '0').strip()
    is_available = request.form.get('is_available') == 'on'
    
    # Validation
    if not name:
        return jsonify({'success': False, 'message': 'Item name is required.'}), 400
    
    try:
        coin_cost = int(coin_cost)
        if coin_cost < 0:
            return jsonify({'success': False, 'message': 'Coin cost must be non-negative.'}), 400
    except ValueError:
        return jsonify({'success': False, 'message': 'Coin cost must be a valid number.'}), 400
    
    # Update store item
    item.name = name
    item.description = description if description else None
    item.tags = tags if tags else None
    item.coin_cost = coin_cost
    item.is_available = is_available
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Store item "{name}" updated successfully!'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to update store item. Please try again.'}), 500


@parent_bp.route('/toggle-store-item/<int:item_id>', methods=['POST'])
@login_required
def toggle_store_item(item_id):
    family_id = session.get('family_id')
    
    item = StoreItem.query.get(item_id)
    
    if not item:
        return jsonify({'success': False, 'message': 'Store item not found.'}), 404
    
    # Verify item belongs to this family
    if item.family_id != family_id:
        return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
    
    # Toggle availability
    item.is_available = not item.is_available
    
    try:
        db.session.commit()
        status = 'available' if item.is_available else 'unavailable'
        return jsonify({
            'success': True,
            'message': f'"{item.name}" is now {status}.',
            'is_available': item.is_available
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to update item. Please try again.'}), 500


@parent_bp.route('/delete-store-item/<int:item_id>', methods=['POST'])
@login_required
def delete_store_item(item_id):
    family_id = session.get('family_id')
    
    item = StoreItem.query.get(item_id)
    
    if not item:
        return jsonify({'success': False, 'message': 'Store item not found.'}), 404
    
    # Verify item belongs to this family
    if item.family_id != family_id:
        return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
    
    item_name = item.name
    
    try:
        db.session.delete(item)
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Store item "{item_name}" deleted successfully.'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to delete item. Please try again.'}), 500


@parent_bp.route('/fulfill-purchase/<int:purchase_id>', methods=['POST'])
@login_required
def fulfill_purchase(purchase_id):
    family_id = session.get('family_id')
    
    # Get the purchase
    purchase = Purchase.query.get(purchase_id)
    
    if not purchase:
        return jsonify({'success': False, 'message': 'Purchase not found.'}), 404
    
    # Verify purchase belongs to this family
    if purchase.kid.family_id != family_id:
        return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
    
    # Verify status is pending
    if purchase.status != 'pending':
        return jsonify({'success': False, 'message': 'This purchase has already been processed.'}), 400
    
    # Mark as fulfilled
    purchase.status = 'fulfilled'
    purchase.fulfilled_at = datetime.utcnow()
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'✓ Purchase fulfilled! {purchase.kid.name} can now enjoy "{purchase.item.name}".'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to fulfill purchase. Please try again.'}), 500


@parent_bp.route('/cancel-purchase/<int:purchase_id>', methods=['POST'])
@login_required
def cancel_purchase(purchase_id):
    family_id = session.get('family_id')
    
    # Get the purchase
    purchase = Purchase.query.get(purchase_id)
    
    if not purchase:
        return jsonify({'success': False, 'message': 'Purchase not found.'}), 404
    
    # Verify purchase belongs to this family
    if purchase.kid.family_id != family_id:
        return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
    
    # Verify status is pending
    if purchase.status != 'pending':
        return jsonify({'success': False, 'message': 'This purchase has already been processed.'}), 400
    
    # Refund coins to kid
    purchase.kid.coin_balance += purchase.coin_cost
    
    # Mark as cancelled
    purchase.status = 'cancelled'
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': f'Purchase cancelled and {purchase.coin_cost} coins refunded to {purchase.kid.name}.',
            'kid_id': purchase.kid.id,
            'new_balance': purchase.kid.coin_balance
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Failed to cancel purchase. Please try again.'}), 500


@parent_bp.route('/family-settings')
@login_required
def family_settings():
    parent_id = session.get('parent_id')
    family_id = session.get('family_id')
    
    parent = Parent.query.get(parent_id)
    family = Family.query.get(family_id)
    
    if not parent or not family:
        flash('Session expired. Please login again.', 'error')
        return redirect(url_for('auth.login'))
    
    # Get all parents in the family
    family_parents = Parent.query.filter_by(family_id=family_id).all()
    
    return render_template('private/parents/family_settings/index.html',
                         parent=parent,
                         family=family,
                         family_parents=family_parents)


@parent_bp.route('/leave-family', methods=['POST'])
@login_required
def leave_family():
    parent_id = session.get('parent_id')
    family_id = session.get('family_id')
    
    parent = Parent.query.get(parent_id)
    family = Family.query.get(family_id)
    
    if not parent or not family:
        flash('Session expired. Please login again.', 'error')
        return redirect(url_for('auth.login'))
    
    # Check if this is the only parent
    family_parents = Parent.query.filter_by(family_id=family_id).all()
    
    if len(family_parents) == 1:
        # Last parent - delete the entire family and all related data
        flash('You are the last parent. Leaving will delete the entire family and all data.', 'warning')
        
        # The cascade delete will handle kids, chores, assignments, store items, purchases
        db.session.delete(family)
        db.session.delete(parent)
        
        try:
            db.session.commit()
            session.clear()
            flash('Family deleted. You can create a new family or join an existing one.', 'info')
            return redirect(url_for('auth.register'))
        except Exception as e:
            db.session.rollback()
            flash('Failed to leave family. Please try again.', 'error')
            return redirect(url_for('parent.family_settings'))
    else:
        # Multiple parents - just remove this parent
        # If this parent is the head, transfer head status to another parent
        if parent.is_head:
            other_parent = next((p for p in family_parents if p.id != parent_id), None)
            if other_parent:
                other_parent.is_head = True
        
        db.session.delete(parent)
        
        try:
            db.session.commit()
            session.clear()
            flash('You have left the family. You can create a new family or join a different one.', 'info')
            return redirect(url_for('auth.register'))
        except Exception as e:
            db.session.rollback()
            flash('Failed to leave family. Please try again.', 'error')
            return redirect(url_for('parent.family_settings'))


@parent_bp.route('/join-new-family', methods=['POST'])
@login_required
def join_new_family():
    parent_id = session.get('parent_id')
    family_code = request.form.get('family_code', '').strip().upper()
    
    if not family_code:
        flash('Family code is required.', 'error')
        return redirect(url_for('parent.family_settings'))
    
    parent = Parent.query.get(parent_id)
    current_family_id = parent.family_id
    
    # Find the new family
    new_family = Family.query.filter_by(family_code=family_code).first()
    
    if not new_family:
        flash('Invalid family code. Please check and try again.', 'error')
        return redirect(url_for('parent.family_settings'))
    
    if new_family.id == current_family_id:
        flash('You are already in this family.', 'error')
        return redirect(url_for('parent.family_settings'))
    
    # Check if this is the only parent in current family
    current_family_parents = Parent.query.filter_by(family_id=current_family_id).all()
    
    if len(current_family_parents) == 1:
        # Last parent - need to delete the old family
        old_family = Family.query.get(current_family_id)
        
        # Transfer parent to new family
        parent.family_id = new_family.id
        parent.is_head = False  # Not head of the new family
        
        # Delete old family (cascade will handle related data)
        db.session.delete(old_family)
    else:
        # Multiple parents in old family
        # If this parent was head, transfer head status
        if parent.is_head:
            other_parent = next((p for p in current_family_parents if p.id != parent_id), None)
            if other_parent:
                other_parent.is_head = True
        
        # Transfer parent to new family
        parent.family_id = new_family.id
        parent.is_head = False  # Not head of the new family
    
    try:
        db.session.commit()
        
        # Update session
        session['family_id'] = new_family.id
        
        flash(f'Successfully joined the {new_family.name} family!', 'success')
        return redirect(url_for('parent.dashboard'))
    except Exception as e:
        db.session.rollback()
        flash('Failed to join new family. Please try again.', 'error')
        return redirect(url_for('parent.family_settings'))


@parent_bp.route('/change-email', methods=['POST'])
@login_required
def change_email():
    parent_id = session.get('parent_id')
    new_email = request.form.get('new_email', '').strip()
    confirm_password = request.form.get('confirm_password', '').strip()
    
    if not new_email or not confirm_password:
        flash('Email and password are required.', 'error')
        return redirect(url_for('parent.family_settings'))
    
    parent = Parent.query.get(parent_id)
    
    if not parent:
        flash('Session expired. Please login again.', 'error')
        return redirect(url_for('auth.login'))
    
    # Verify current password
    if not parent.check_password(confirm_password):
        flash('Incorrect password.', 'error')
        return redirect(url_for('parent.family_settings'))
    
    # Check if new email is already in use
    existing_parent = Parent.query.filter_by(email=new_email).first()
    if existing_parent and existing_parent.id != parent_id:
        flash('Email address already in use.', 'error')
        return redirect(url_for('parent.family_settings'))
    
    # Check if email is the same
    if parent.email == new_email:
        flash('New email is the same as current email.', 'info')
        return redirect(url_for('parent.family_settings'))
    
    # Update email
    parent.email = new_email
    
    try:
        db.session.commit()
        flash('Email address updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to update email. Please try again.', 'error')
    
    return redirect(url_for('parent.family_settings'))


@parent_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    parent_id = session.get('parent_id')
    current_password = request.form.get('current_password', '').strip()
    new_password = request.form.get('new_password', '').strip()
    confirm_new_password = request.form.get('confirm_new_password', '').strip()
    
    if not current_password or not new_password or not confirm_new_password:
        flash('All password fields are required.', 'error')
        return redirect(url_for('parent.family_settings'))
    
    parent = Parent.query.get(parent_id)
    
    if not parent:
        flash('Session expired. Please login again.', 'error')
        return redirect(url_for('auth.login'))
    
    # Verify current password
    if not parent.check_password(current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('parent.family_settings'))
    
    # Check password length
    if len(new_password) < 6:
        flash('New password must be at least 6 characters.', 'error')
        return redirect(url_for('parent.family_settings'))
    
    # Check passwords match
    if new_password != confirm_new_password:
        flash('New passwords do not match.', 'error')
        return redirect(url_for('parent.family_settings'))
    
    # Check if new password is same as current
    if parent.check_password(new_password):
        flash('New password cannot be the same as current password.', 'info')
        return redirect(url_for('parent.family_settings'))
    
    # Update password
    parent.set_password(new_password)
    
    try:
        db.session.commit()
        flash('Password updated successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Failed to update password. Please try again.', 'error')
    
    return redirect(url_for('parent.family_settings'))


@parent_bp.route('/history')
@login_required
def history():
    family_id = session.get('family_id')
    
    # Get all purchases for this family, ordered by most recent first
    purchases = Purchase.query.join(Kid).filter(
        Kid.family_id == family_id
    ).order_by(Purchase.purchased_at.desc()).all()
    
    # Get all completed/confirmed chore assignments for this family
    assignments = ChoreAssignment.query.join(Kid).join(Chore).filter(
        Kid.family_id == family_id,
        ChoreAssignment.status.in_(['confirmed', 'rejected'])
    ).order_by(ChoreAssignment.completed_at.desc()).all()
    
    # Get all kids for filtering
    kids = Kid.query.filter_by(family_id=family_id).order_by(Kid.name).all()
    
    # Get all chores for filtering
    chores = Chore.query.filter_by(family_id=family_id).order_by(Chore.name).all()
    
    return render_template('private/parents/history/index.html',
                         purchases=purchases,
                         assignments=assignments,
                         kids=kids,
                         chores=chores)
