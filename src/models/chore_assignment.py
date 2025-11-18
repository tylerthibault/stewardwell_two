from datetime import datetime
from src.models.base_model import db


class ChoreAssignment(db.Model):
    __tablename__ = 'chore_assignment'
    
    id = db.Column(db.Integer, primary_key=True)
    chore_id = db.Column(db.Integer, db.ForeignKey('chore.id'), nullable=False)
    kid_id = db.Column(db.Integer, db.ForeignKey('kid.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, completed, confirmed, rejected
    completed_at = db.Column(db.DateTime, nullable=True)
    confirmed_by_parent_id = db.Column(db.Integer, db.ForeignKey('parent.id'), nullable=True)
    coin_awarded = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ChoreAssignment {self.id} - {self.status}>'
