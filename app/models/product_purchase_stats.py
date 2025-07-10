from mongoengine import Document, ObjectIdField, IntField, StringField, DateTimeField

class ProductPurchaseStats(Document):
    product_id = ObjectIdField(required=True)
    product_name = StringField(required=True)
    purchase_count = IntField(default=0)
    last_purchased_at = DateTimeField()
    
    meta = {
        'collection': 'product_purchase_stats',
        'indexes': [
            'product_id',
            {'fields': ['purchase_count'], 'name': 'purchase_count_index'}
        ]
    }