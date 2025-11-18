from datetime import datetime
from .base_model import db


class Purchase(db.Model):
    __tablename__ = 'purchase'
    
    id = db.Column(db.Integer, primary_key=True)
    kid_id = db.Column(db.Integer, db.ForeignKey('kid.id', ondelete='CASCADE'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('store_item.id', ondelete='CASCADE'), nullable=False)
    coin_cost = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, fulfilled, cancelled
    purchased_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    fulfilled_at = db.Column(db.DateTime)
    
    # Relationships
    kid = db.relationship('Kid', backref='purchases')
    
    def __repr__(self):
        return f'<Purchase {self.kid.name} - {self.item.name}>'
