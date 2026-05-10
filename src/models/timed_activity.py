from datetime import datetime
from src.models.base_model import db


class TimedActivity(db.Model):
    __tablename__ = 'timed_activity'

    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    coins_per_minute = db.Column(db.Integer, nullable=False, default=1)
    time_limit_minutes = db.Column(db.Integer, nullable=False, default=10)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    sessions = db.relationship('GameSession', backref='activity', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<TimedActivity {self.name} ({self.coins_per_minute} coins/min)>'
