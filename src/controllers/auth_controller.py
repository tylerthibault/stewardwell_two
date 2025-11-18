from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from src.models.base_model import db
from src.models.parent import Parent
from src.models.family import Family

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Registration logic will go here in Phase 2
        pass
    return render_template('public/auth/register/index.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Login logic will go here in Phase 2
        pass
    return render_template('public/auth/login/index.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main.landing'))
