class ProductAddToCartLog(db.Document):
    product_id = db.ReferenceField('Products', required=True)
    cart_add_count = db.DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'product_add_to_cart_logs',
        'indexes': ['product_id', 'added_at']
    }
