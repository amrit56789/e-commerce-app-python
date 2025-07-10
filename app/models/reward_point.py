from datetime import datetime
from app import db

class RewardPoint(db.Document):
    user_id = db.ReferenceField('User', required=True)
    points = db.IntField(required=True)
    reason = db.StringField(required=True)
    created_at = db.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'reward_points',
        'indexes': [
            'user_id',
            'created_at'
        ]
    }