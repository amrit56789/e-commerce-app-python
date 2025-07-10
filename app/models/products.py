from app.extensions import db
from datetime import datetime
from app.models import Category, SubCategory, SubSubCategory
from app.models.brands import ProductBrands
from constants import ALLOWED_SIZES, ALLOWED_GENDERS
from mongoengine import ReferenceField
from app.models import Seller

class ProductVariant(db.Document):
    product_id = db.ReferenceField('Products', required=False)
    size = db.StringField(required=True, choices=ALLOWED_SIZES)
    color = db.StringField(required=True, max_length=50)
    color_hexa_code = db.StringField(max_length=7)
    stock_quantity = db.IntField(default=0)
    images = db.ListField(db.ReferenceField('ProductVariantImage'))
    created_at = db.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'product_variants',
        'indexes': [
            'product_id',
            'size',
            'color',
            'color_hexa_code'
        ]
    }
    
    def __repr__(self):
        return f"<Variant {self.product_id.name} - {self.color}/{self.size}>"


class ProductVariantImage(db.Document):
    variant_id = db.ReferenceField(ProductVariant, required=False)
    image_url = db.StringField(required=True, max_length=255)
    alt_text = db.StringField(max_length=255)
    
    meta = {
        'collection': 'product_variant_images',
        'indexes': [
            'variant_id',
        ]
    }
    
    def __repr__(self):
        return f"<Image {self.image_url}>"


class Products(db.Document):
    seller_id = db.ReferenceField(Seller, required=True)
    name = db.StringField(required=True, max_length=255)
    details = db.StringField()
    description = db.StringField()
    
    sku_number = db.StringField(required=True, unique=True)
    category_id = db.ReferenceField(Category, required=True)
    subcategory_id = db.ReferenceField(SubCategory, required=True)
    subsubcategory_id = db.ReferenceField(SubSubCategory, required=True)
    brand_id = db.ReferenceField(ProductBrands, required=True)
    
    price = db.DecimalField(required=True, precision=2)
    discount_price = db.DecimalField(precision=2)
    final_price = db.DecimalField(required=True, precision=2)
    stock_quantity = db.IntField()
    material = db.StringField(max_length=100)
    gender = db.StringField(choices=ALLOWED_GENDERS)
    status = db.StringField(choices=['active', 'inactive'], default='active')
    variants = db.ListField(ReferenceField('ProductVariant'))
    
    created_at = db.DateTimeField(default=datetime.utcnow)
    updated_at = db.DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'products',
        'indexes': [
            'seller_id',
            'name',
            'category_id',
            'subcategory_id',
            'brand_id',
            'status'
        ]
    }
    
    def __repr__(self):
        return f"<Product {self.name}>"