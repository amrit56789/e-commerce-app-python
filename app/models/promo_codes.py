from app.extensions import db
from datetime import datetime
from mongoengine import EmbeddedDocument, EmbeddedDocumentField
from bson import ObjectId

class PromoCode(db.Document):
    code = db.StringField(required=True, unique=True)
    discount_type = db.StringField(required=True, choices=['percentage', 'fixed_amount'])
    discount_value = db.DecimalField(required=True, precision=2)
    start_date = db.DateTimeField(required=True)
    created_by = db.ReferenceField('User', required=True)
    
    description = db.StringField()
    min_order_amount = db.DecimalField(precision=2, default=0.0)
    max_discount_amount = db.DecimalField(precision=2)
    expiry_date = db.DateTimeField()
    max_uses = db.IntField()
    uses_per_user = db.IntField(default=1)
    only_first_order = db.BooleanField(default=False)
    used_count = db.IntField(default=0)
    is_active = db.BooleanField(default=True)
    
    created_at = db.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'promo_codes',
        'indexes': [
            'code',
            'start_date',
            'expiry_date',
            'is_active',
            'created_by'
        ]
    }

    def is_valid(self, user_id, order_amount):
        now = datetime.utcnow()
        
        if not self.is_active:
            return False, "Promo code is not active"
        if now < self.start_date:
            return False, "Promo code is not yet valid"
        if self.expiry_date and now > self.expiry_date:
            return False, "Promo code has expired"
        if self.max_uses and self.used_count >= self.max_uses:
            return False, "Promo code usage limit reached"
        if order_amount < float(self.min_order_amount):
            return False, f"Minimum order amount of {self.min_order_amount} required"
        
        return True, "Valid promo code"

    def calculate_discount(self, order_amount):
        if self.discount_type == 'percentage':
            discount = (order_amount * float(self.discount_value)) / 100
            if self.max_discount_amount and discount > float(self.max_discount_amount):
                return float(self.max_discount_amount)
            return discount
        else:  # fixed_amount
            discount = float(self.discount_value)
            if self.max_discount_amount and discount > float(self.max_discount_amount):
                return float(self.max_discount_amount)
            return min(discount, order_amount)

    def increment_usage(self):
        self.used_count += 1
        if self.max_uses and self.used_count >= self.max_uses:
            self.is_active = False
        self.save()
