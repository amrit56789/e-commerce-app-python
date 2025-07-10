from app.extensions import db
from datetime import datetime

class ProductBrands(db.Document):
    name = db.StringField(required=True, unique=True)
    description = db.StringField()
    logo_path = db.StringField()
    created_at = db.DateTimeField(default=datetime.utcnow)
    updated_at = db.DateTimeField(default=datetime.utcnow)

    def __repr__(self):
        return f'<Brand {self.name}>'
