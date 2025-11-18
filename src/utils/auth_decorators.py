from functools import wraps
from flask import session, redirect, url_for, flash


def login_required(f):
    """Decorator to require parent login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'parent_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def kid_login_required(f):
    """Decorator to require kid login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'kid_id' not in session:
            flash('Please login to access this page.', 'warning')
            return redirect(url_for('kid.login'))
        return f(*args, **kwargs)
    return decorated_function
