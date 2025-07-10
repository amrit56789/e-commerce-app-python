from app.extensions import db
from datetime import datetime
from constants import ALLOWED_SIZES

class SaveForLaterItem(db.EmbeddedDocument):
    product_id = db.StringField(required=True)
    variant_id = db.StringField()
    size = db.StringField(choices=ALLOWED_SIZES)
    quantity = db.IntField(required=True, min_value=1)
    price = db.FloatField(required=True)
    original_price = db.FloatField()
    discount = db.FloatField(default=0.0)
    added_at = db.DateTimeField(default=datetime.utcnow)

    def validate_stock(self, product_model):
        product = product_model.objects(id=self.product_id).first()
        if not product:
            raise ValueError(f"Product {self.product_id} not found")
        if self.variant_id:
            variant = None
            for v in product.variants:
                if str(v.id) == self.variant_id:
                    variant = v
                    break
            if not variant:
                raise ValueError(f"Variant {self.variant_id} not found")
            available_stock = variant.stock_quantity
        else:
            available_stock = product.stock_quantity
        if self.quantity > available_stock:
            raise ValueError(f"Insufficient stock for product {self.product_id}")

    def __repr__(self):
        return f"<SaveForLaterItem {self.product_id}>"

class SaveForLater(db.Document):
    user_id = db.StringField(required=True, unique=True)
    items = db.EmbeddedDocumentListField(SaveForLaterItem)
    created_at = db.DateTimeField(default=datetime.utcnow)
    updated_at = db.DateTimeField(default=datetime.utcnow)

    meta = {
        'indexes': [
            {'fields': ['user_id'], 'unique': True},
            'created_at',
        ]
    }

    def validate_saveforlater(self, product_model):
        for item in self.items:
            item.validate_stock(product_model)

    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)

    def __repr__(self):
        return f"<SaveForLater for User {self.user_id}>"