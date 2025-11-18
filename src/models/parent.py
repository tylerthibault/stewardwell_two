from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from src.models.base_model import db


class Parent(db.Model):
    __tablename__ = 'parent'
    
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_head = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    created_chores = db.relationship('Chore', backref='creator', lazy=True)
    confirmed_assignments = db.relationship('ChoreAssignment', backref='confirmer', lazy=True, foreign_keys='ChoreAssignment.confirmed_by_parent_id')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Parent {self.email}>'
