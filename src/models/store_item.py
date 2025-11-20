from datetime import datetime
from .base_model import db


class StoreItem(db.Model):
    __tablename__ = 'store_item'
    
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('family.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    tags = db.Column(db.String(500), nullable=True)
    coin_cost = db.Column(db.Integer, nullable=False, default=0)
    is_available = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    family = db.relationship('Family', backref='store_items')
    purchases = db.relationship('Purchase', backref='item', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<StoreItem {self.name}>'
