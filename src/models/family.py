from datetime import datetime
from src.models.base_model import db
import secrets


class Family(db.Model):
    __tablename__ = 'family'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    family_code = db.Column(db.String(6), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    parents = db.relationship('Parent', backref='family', lazy=True, cascade='all, delete-orphan')
    kids = db.relationship('Kid', backref='family', lazy=True, cascade='all, delete-orphan')
    chores = db.relationship('Chore', backref='family', lazy=True, cascade='all, delete-orphan')
    
    @staticmethod
    def generate_family_code():
        """Generate a unique 6-character family code"""
        while True:
            code = secrets.token_hex(3).upper()  # 6 characters
            if not Family.query.filter_by(family_code=code).first():
                return code
    
    def __repr__(self):
        return f'<Family {self.name}>'
