from datetime import datetime
from src.models.base_model import db


class Chore(db.Model):
    __tablename__ = 'chore'
    
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    coin_value = db.Column(db.Integer, nullable=False, default=0)
    point_value = db.Column(db.Integer, nullable=False, default=0)
    created_by_parent_id = db.Column(db.Integer, db.ForeignKey('parent.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    assignments = db.relationship('ChoreAssignment', backref='chore', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Chore {self.name}>'
