from app.extensions import db
from app.models import Category, SubCategory, SubSubCategory, ProductBrands
from flask import url_for

def seed_categories():
    if Category.objects.count() > 0:
        print("Categories already exist. Skipping category seeding.")
        return

    category_data = {
        "MEN": ["Shirts", "Pants"],
        "WOMEN": ["Dresses", "Handbags"],
        "ELECTRONICS": ["Mobiles", "Laptops"],
        "HOME": ["Furniture", "Kitchen"],
    }

    sub_sub_category_data = {
        "Shirts": ["Casual Shirts", "Formal Shirts"],
        "Pants": ["Jeans", "Chinos"],
        "Dresses": ["Evening Dresses", "Casual Dresses"],
        "Handbags": ["Totes", "Clutches"],
        "Mobiles": ["Android Phones", "iPhones"],
        "Laptops": ["Gaming Laptops", "Ultrabooks"],
        "Furniture": ["Sofas", "Beds"],
        "Kitchen": ["Cookware", "Appliances"],
    }

    categories = {}
    subcategories = {}

    for cat_name, subcat_names in category_data.items():
        category = Category(
            name=cat_name,
            description=f"{cat_name} category description",
            img_url=f"{cat_name.lower()}.jpg"
        ).save()
        categories[cat_name] = category

        for subcat_name in subcat_names:
            subcategory = SubCategory(
                name=subcat_name,
                description=f"{subcat_name} subcategory description",
                category=category,
                img_url=f"{subcat_name.lower().replace(' ', '_')}.jpg"
            ).save()
            subcategories[subcat_name] = subcategory
            print(f"  Subcategory created: {subcat_name}")

            if subcat_name in sub_sub_category_data:
                for prod_type_name in sub_sub_category_data[subcat_name]:
                    SubSubCategory(
                        name=prod_type_name,
                        description=f"{prod_type_name} product type description",
                        category_id=category,
                        sub_category_id=subcategory,
                        img_url=f"{prod_type_name.lower().replace(' ', '_')}.jpg"
                    ).save()
                    print(f" SubSubCategory created: {prod_type_name}")

    print("Category seeding complete!")

def seed_brands():
    brand_data = [
        {"name": "Nike", "description": "Global leader in sportswear.", "logo_path": "nike_logo.png"},
        {"name": "Adidas", "description": "Known for innovation and performance.", "logo_path": "adidas_logo.png"},
        {"name": "Puma", "description": "Performance and lifestyle brand.", "logo_path": "puma_logo.png"},
        {"name": "Reebok", "description": "Fitness and lifestyle brand.", "logo_path": "reebok_logo.png"},
        {"name": "Under Armour", "description": "Brand known for its performance gear.", "logo_path": "under_armour_logo.png"},
        {"name": "New Balance", "description": "Premium sports and lifestyle footwear.", "logo_path": "new_balance_logo.png"},
        {"name": "Asics", "description": "Japanese brand known for athletic shoes.", "logo_path": "asics_logo.png"},
        {"name": "Fila", "description": "Sporty, yet stylish apparel.", "logo_path": "fila_logo.png"},
        {"name": "Converse", "description": "Iconic American footwear brand.", "logo_path": "converse_logo.png"},
        {"name": "Vans", "description": "Skateboarding and streetwear culture.", "logo_path": "vans_logo.png"}
    ]

    if ProductBrands.objects.count() > 0:
        print("Brands already exist. Skipping brand seeding.")
        return

    for data in brand_data:
        brand = ProductBrands(
            name=data["name"],
            description=data["description"],
            logo_path=data["logo_path"]
        )
        brand.save()

    print("Brand seeding complete!")



def seed_data():
    seed_categories()
    seed_brands()
