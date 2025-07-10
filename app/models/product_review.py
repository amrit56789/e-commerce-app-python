from mongoengine import Document, ReferenceField, StringField, IntField, DateTimeField
from datetime import datetime
from app.models.products import Products
from app.models import User

class ProductReview(Document):
    product_id = ReferenceField(Products, required=True)
    user_id = ReferenceField(User, required=True)
    rating = IntField(required=True, min_value=1, max_value=5)
    review = StringField(required=True, max_length=1000)
    image_url = StringField()
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'product_reviews',
        'indexes': [
            'product_id',
            'user_id'
        ]
    }

    def __repr__(self):
        return f"<Review {self.product_id.name} - {self.rating} stars>"
