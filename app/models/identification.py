from app import db
from datetime import datetime

class Identification(db.Document):
    user_id = db.ReferenceField('User', required=True)
    address_proof_id_type = db.StringField(required=True)
    address_proof_front = db.StringField()
    address_proof_back = db.StringField()
    pan_number = db.StringField(required=True)
    pan_card_front = db.StringField()
    id_number = db.StringField()
    created_at = db.DateTimeField(default=datetime.utcnow)
