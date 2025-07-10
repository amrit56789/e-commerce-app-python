from app.extensions import db
from datetime import datetime
from mongoengine import Document, StringField, IntField, ReferenceField, DateTimeField

class ProductCart(db.Document):
    product_id = db.ReferenceField('Products', required=False)
    user_id = db.StringField(required=True)
    selected_size = db.StringField()
    selected_color = db.StringField()
    selected_color_name = db.StringField()
    quantity = db.IntField(default=1)

    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'indexes': [
            'user_id',
            'product_id',
        ],
        'ordering': ['-created_at']
    }

    def __repr__(self):
        return f"<ProductCart user={self.user_id} product={self.product_id}>"
