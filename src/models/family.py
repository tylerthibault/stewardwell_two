from datetime import datetime
from src.models.base_model import db


class Family(db.Model):
    __tablename__ = 'family'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    parents = db.relationship('Parent', backref='family', lazy=True, cascade='all, delete-orphan')
    kids = db.relationship('Kid', backref='family', lazy=True, cascade='all, delete-orphan')
    chores = db.relationship('Chore', backref='family', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Family {self.name}>'
