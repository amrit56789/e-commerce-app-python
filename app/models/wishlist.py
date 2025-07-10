from app.extensions import db
from datetime import datetime
from constants import ALLOWED_SIZES
from app.models import Products

class WishlistItem(db.Document):
    user_id = db.StringField(required=True)
    product_id = db.StringField(required=True)
    size = db.StringField(choices=ALLOWED_SIZES)
    color = db.StringField()
    color_hexa_code = db.StringField()
    quantity = db.IntField(default=1)
    added_at = db.DateTimeField(default=datetime.utcnow)

    meta = {
        'indexes': [
            {'fields': ['user_id', 'product_id', 'size', 'color_hexa_code'], 'unique': True},
            'user_id',
            'product_id',
            'added_at',
        ]
    }

    def validate_product(self):
        from .products import Products
        product = Products.objects(id=self.product_id).first()
        if not product:
            raise ValueError(f"Product {self.product_id} not found")
        
        if hasattr(product, 'variants'):
            variant_exists = any(
                v for v in product.variants 
                if v.size == self.size and v.color == self.color
            )
            if not variant_exists:
                raise ValueError(f"Variant with size {self.size} and color {self.color} not found")

    def save(self, *args, **kwargs):
        self.validate_product()
        return super().save(*args, **kwargs)

    def __repr__(self):
        return f"<WishlistItem {self.product_id} for User {self.user_id}>"