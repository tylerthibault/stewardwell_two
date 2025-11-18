from flask import Blueprint, request, jsonify
from src.models.base_model import db
from src.models.chore_assignment import ChoreAssignment
from src.models.kid import Kid

chore_bp = Blueprint('chore', __name__)


@chore_bp.route('/confirm/<int:assignment_id>', methods=['POST'])
def confirm_assignment(assignment_id):
    # Confirm chore assignment logic will go here in Phase 4
    pass


@chore_bp.route('/reject/<int:assignment_id>', methods=['POST'])
def reject_assignment(assignment_id):
    # Reject chore assignment logic will go here in Phase 4
    pass
