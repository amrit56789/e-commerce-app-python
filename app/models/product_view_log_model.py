class ProductViewLog(db.Document):
    product_id = db.ReferenceField('Products', required=True)
    viewed_count = db.DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'product_view_logs',
        'indexes': ['product_id', 'viewed_at']
    }