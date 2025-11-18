from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from src.models.base_model import db
from src.models.kid import Kid
from src.models.chore import Chore
from src.models.chore_assignment import ChoreAssignment

kid_bp = Blueprint('kid', __name__)


@kid_bp.route('/dashboard')
def dashboard():
    # Kid dashboard logic will go here in Phase 3
    return render_template('private/kiddos/dashboard.html')


@kid_bp.route('/login', methods=['POST'])
def login():
    # Kid login logic will go here in Phase 3
    pass


@kid_bp.route('/pick-chore/<int:chore_id>', methods=['POST'])
def pick_chore(chore_id):
    # Pick chore logic will go here in Phase 3
    pass


@kid_bp.route('/complete-chore/<int:assignment_id>', methods=['POST'])
def complete_chore(assignment_id):
    # Complete chore logic will go here in Phase 3
    pass
