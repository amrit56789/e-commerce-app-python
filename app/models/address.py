from app import db
from mongoengine import Document, ReferenceField, StringField, BooleanField, DateTimeField
from datetime import datetime
from constants import ADDRESS_TYPES

class Address(db.Document):
    user_id = db.ReferenceField('User', required=True)
    
    line1 = db.StringField(required=True)
    line2 = db.StringField()
    city = db.StringField(required=True)
    state = db.StringField(required=True)
    postal_code = db.StringField(required=True)
    country = db.StringField(required=True)
    contact_name = db.StringField()
    contact_number = db.IntField()
    type = db.StringField(choices=ADDRESS_TYPES, required=True)
    is_primary = db.BooleanField(default=False)
    is_business_address = db.BooleanField(default=False)
    created_at = db.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'indexes': [
            'user_id',
            'type',
            'is_primary'
        ]
    }

    def clean(self):
        if self.is_primary:
            existing_primary = Address.objects(
                user_id=self.user_id,
                type=self.type,
                is_primary=True
            ).first()
            
            if existing_primary and existing_primary.id != self.id:
                existing_primary.update(set__is_primary=False)