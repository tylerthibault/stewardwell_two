from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from src.models.base_model import db


class Kid(db.Model):
    __tablename__ = 'kid'
    
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    pin_code = db.Column(db.String(255), nullable=False)
    coin_balance = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    chore_assignments = db.relationship('ChoreAssignment', backref='kid', lazy=True, cascade='all, delete-orphan')
    
    def set_pin(self, pin):
        self.pin_code = generate_password_hash(pin)
    
    def check_pin(self, pin):
        return check_password_hash(self.pin_code, pin)
    
    def __repr__(self):
        return f'<Kid {self.name}>'
