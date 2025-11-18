from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from src.models.base_model import db
from src.models.parent import Parent
from src.models.kid import Kid
from src.models.chore import Chore

parent_bp = Blueprint('parent', __name__)


@parent_bp.route('/dashboard')
def dashboard():
    # Parent dashboard logic will go here in Phase 2
    return render_template('private/parents/dashboard/index.html')


@parent_bp.route('/add-kid', methods=['POST'])
def add_kid():
    # Add kid logic will go here in Phase 2
    pass


@parent_bp.route('/create-chore', methods=['POST'])
def create_chore():
    # Create chore logic will go here in Phase 2
    pass
