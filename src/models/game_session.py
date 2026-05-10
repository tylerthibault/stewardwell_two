from datetime import datetime
from src.models.base_model import db


class GameSession(db.Model):
    __tablename__ = 'game_session'

    id = db.Column(db.Integer, primary_key=True)
    kid_id = db.Column(db.Integer, db.ForeignKey('kid.id'), nullable=False)
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'), nullable=False)
    activity_id = db.Column(db.Integer, db.ForeignKey('timed_activity.id'), nullable=False)
    started_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime, nullable=True)
    minutes_played = db.Column(db.Integer, nullable=True)
    coins_spent = db.Column(db.Integer, nullable=True)
    # status: 'active', 'completed', 'ended_by_parent'
    status = db.Column(db.String(20), nullable=False, default='active')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    kid = db.relationship('Kid', backref=db.backref('game_sessions', lazy=True))

    def __repr__(self):
        return f'<GameSession kid={self.kid_id} activity={self.activity_id} status={self.status}>'
