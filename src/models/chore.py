from datetime import datetime, timedelta
from src.models.base_model import db


class Chore(db.Model):
    __tablename__ = 'chore'
    
    id = db.Column(db.Integer, primary_key=True)
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    coin_value = db.Column(db.Integer, nullable=False, default=0)
    point_value = db.Column(db.Integer, nullable=False, default=0)
    created_by_parent_id = db.Column(db.Integer, db.ForeignKey('parent.id'), nullable=False)
    
    # Frequency and active status
    frequency = db.Column(db.String(20), nullable=False, default='unlimited')  # unlimited, daily, weekly, monthly, one_time
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    
    # Relationships
    assignments = db.relationship('ChoreAssignment', backref='chore', lazy=True, cascade='all, delete-orphan')
    
    def can_be_done_by_kid(self, kid_id):
        """Check if this chore can be done by a kid based on active status and frequency"""
        # Check if chore is active
        if not self.is_active:
            return False
        
        if self.frequency == 'unlimited':
            return True
        
        # Get the time window based on frequency
        now = datetime.utcnow()
        if self.frequency == 'daily':
            window_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif self.frequency == 'weekly':
            # Start of current week (Monday)
            days_since_monday = now.weekday()
            window_start = (now - timedelta(days=days_since_monday)).replace(hour=0, minute=0, second=0, microsecond=0)
        elif self.frequency == 'monthly':
            window_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif self.frequency == 'one_time':
            window_start = datetime.min
        else:
            return True  # Unknown frequency type, allow it
        
        # Count completed/confirmed assignments in this window
        from src.models.chore_assignment import ChoreAssignment
        completed_count = ChoreAssignment.query.filter(
            ChoreAssignment.chore_id == self.id,
            ChoreAssignment.kid_id == kid_id,
            ChoreAssignment.status.in_(['pending', 'confirmed']),
            ChoreAssignment.created_at >= window_start
        ).count()
        
        # For one_time, can only be done once ever
        if self.frequency == 'one_time':
            return completed_count == 0
        
        # For other frequencies, can be done once per period
        return completed_count == 0
    
    def __repr__(self):
        return f'<Chore {self.name}>'
