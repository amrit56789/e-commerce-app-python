from flask import Blueprint, request, jsonify, current_app, url_for
from app.models import Products, ProductVariant , User, WishlistItem, Seller, ProductCart
from datetime import datetime
from constants import WISHLIST_ADD, WISHLIST_REMOVE, WISHLIST_LIST, ALLOWED_SIZES, WISHLIST_REMOVE_ALL, WISHLIST_MOVE_TO_CART
from app.utils.validation import validate_required_fields
from app.utils.utils import create_error_response
from app.utils.jwt_handlers import jwt_error_handler
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.image_upload import get_local_ip

wishlist_bp = Blueprint('wishlist', __name__)
local_ip = get_local_ip()

@wishlist_bp.route(WISHLIST_ADD, methods=['POST'])
@jwt_error_handler
@jwt_required()
def add_to_wishlist():
    user_id = get_jwt_identity()
    user = User.objects(id=user_id).first()

    # Data validation
    try:
        data = request.get_json()
        if not data:
            return create_error_response({"error": "No data provided"}, 400)
    except Exception:
        return create_error_response({"error": "Invalid JSON data"}, 400)

    # Required fields validation
    required_fields = ['product_id', 'selected_size', 'selected_color']
    is_valid, validation_errors = validate_required_fields(data, required_fields)
    if not is_valid:
        return create_error_response({"error": validation_errors}, 400)

    # Input sanitization
    product_id = data['product_id'].strip()
    selected_size = data['selected_size'].strip().upper()
    selected_color = data['selected_color'].strip().lower()
    quantity = max(1, int(data.get('quantity', 1)))  # Ensure minimum quantity of 1

    # Size validation
    if selected_size not in ALLOWED_SIZES:
        return create_error_response(
            {"error": f"Invalid size. Must be one of {ALLOWED_SIZES}"}, 
            400
        )

    # Product existence check
    if not ObjectId.is_valid(product_id):
        return create_error_response({"error": "Invalid product ID format"}, 400)

    product = Products.objects(id=product_id, status='active').first()
    if not product:
        return create_error_response({"error": "Product not found or inactive"}, 404)

    # Variant availability check
    variant = ProductVariant.objects(
        product_id=product_id,
        size=selected_size,
        color_hexa_code=selected_color,
        stock_quantity__gt=0  # Only consider in-stock variants
    ).first()

    if not variant:
        return create_error_response({
            "error": "Variant not available",
            "details": "The selected size/color combination is either invalid or out of stock"
        }, 404)

    # Check if already in cart (optional business logic)
    in_cart = CartItem.objects(
        user_id=user_id,
        product_id=product_id,
        size=selected_size,
        color_hexa_code=selected_color
    ).first()

    # Wishlist limit check (e.g., max 50 items)
    wishlist_count = WishlistItem.objects(user_id=user_id).count()
    if wishlist_count >= 50:
        return create_error_response({
            "error": "Wishlist limit reached",
            "message": "Maximum 50 items allowed in wishlist"
        }, 400)

    # Check for existing wishlist item
    existing_item = WishlistItem.objects(
        user_id=user_id,
        product_id=product_id,
        size=selected_size,
        color_hexa_code=selected_color
    ).first()

    # Update or create wishlist item
    if existing_item:
        existing_item.update(
            quantity=min(existing_item.quantity + quantity, 10),  # Max 10 per item
            last_updated=datetime.utcnow()
        )
        action = "updated"
    else:
        wishlist_item = WishlistItem(
            user_id=user_id,
            product_id=product_id,
            size=selected_size,
            color=variant.color,
            color_hexa_code=variant.color_hexa_code,
            quantity=quantity,
            product_data={
                "name": product.name,
                "price": product.price,
                "image": variant.images[0].image_url if variant.images else None
            }
        )
        wishlist_item.save()
        action = "added"

    # Log wishlist activity
    WishlistActivityLog(
        user_id=user_id,
        product_id=product_id,
        action="add",
        variant_data={
            "size": selected_size,
            "color": selected_color
        }
    ).save()

    # Prepare response with enhanced product data
    wishlist_items = WishlistItem.objects(user_id=user_id).order_by('-added_at')
    
    response_data = {
        "message": f"Item {action} to wishlist successfully",
        "data": [wishlist_item_to_dict(item) for item in wishlist_items],
        "metadata": {
            "wishlist_count": wishlist_count + (0 if existing_item else 1),
            "in_cart": bool(in_cart),
            "product_available": variant.stock_quantity > 0
        }
    }

    return jsonify(response_data), 200

def wishlist_item_to_dict(item):
    return {
        "id": str(item.id),
        "product_id": str(item.product_id.id),
        "product_name": getattr(item.product_data, 'name', ''),
        "product_price": float(getattr(item.product_data, 'price', 0)),
        "product_image": url_for(
            'serve_uploaded_files', 
            filename=getattr(item.product_data, 'image', ''),
            _external=True
        ) if getattr(item.product_data, 'image', None) else None,
        "size": item.size,
        "color": item.color,
        "color_hexa_code": item.color_hexa_code,
        "quantity": item.quantity,
        "added_at": item.added_at.isoformat(),
        "last_updated": item.last_updated.isoformat() if hasattr(item, 'last_updated') else None
    }

@wishlist_bp.route(WISHLIST_REMOVE, methods=['DELETE'])
@jwt_required()
@jwt_error_handler
def remove_from_wishlist():
    user_id = get_jwt_identity()
    
    try:
        data = request.get_json()
    except Exception:
        return create_error_response({"error": "Invalid JSON data"}, 400)

    item_ids = data.get('item_ids')
    
    if not item_ids or not isinstance(item_ids, list):
        return create_error_response({"error": "item_ids must be a list of wishlist item IDs"}, 400)

    delete_result = WishlistItem.objects(
        user_id=user_id,
        id__in=item_ids
    ).delete()

    if delete_result == 0:
        return create_error_response({"error": "No matching items found in your wishlist"}, 400)

    remaining_items = WishlistItem.objects(user_id=user_id)

    response_data = {
        "message": f"Removed {delete_result} items from wishlist",
        "data": [
            {
                "id": str(item.id),
                "product_id": str(item.product_id),
                "size": item.size,
                "color": item.color,
                "color_hexa_code": item.color_hexa_code,
                "quantity": item.quantity,
                "added_at": item.added_at.isoformat()
            } for item in remaining_items
        ]
    }

    return jsonify(response_data), 200


@wishlist_bp.route(WISHLIST_LIST, methods=['GET'])
@jwt_required()
@jwt_error_handler
def get_wishlist():
    user_id = get_jwt_identity()
    
    wishlist_items = WishlistItem.objects(user_id=user_id).order_by('-added_at')
    
    items_with_details = []
    for item in wishlist_items:
        product = Products.objects(id=item.product_id).first()
        if not product:
            continue
            
        variant = ProductVariant.objects(
            product_id=item.product_id,
            size=item.size,
            color_hexa_code=item.color_hexa_code
        ).first()
        
        image_urls = []
        if variant and variant.images:
            for img in variant.images:
                image_urls.append({
                    "image_url": img.image_url,
                    "alt_text": img.alt_text if hasattr(img, 'alt_text') else None
                })
        
        all_variants = ProductVariant.objects(product_id=item.product_id)
        sizes_with_variants = []
        colors_available = set()
        
        size_map = {}
        for v in all_variants:
            if v.size not in size_map:
                size_map[v.size] = {
                    "product_id": str(v.product_id.id),
                    "value": v.size,
                    "size_type": "numeric",
                    "id": str(v.id),
                    "variants": []
                }
            color_variant = {
                "value": v.color_hexa_code,
                "name": v.color,
                "stock_quantity": v.stock_quantity,
                "id": str(v.id)
            }
            size_map[v.size]["variants"].append(color_variant)
            colors_available.add((v.color, v.color_hexa_code))
        
        sizes_with_variants = list(size_map.values())
        
        gallery_images = []
        for v in all_variants:
            if v.images:
                for img in v.images:
                    gallery_images.append({
                        "color": v.color,
                        "id": str(img.id),
                        "img_url": url_for('serve_uploaded_files', filename=img.image_url, _external=True) if img.image_url else '',
                        
                    })
        
        category = {
            "name": product.category_id.name,
            "description": product.category_id.description,
            "id": str(product.category_id.id),
            "img_url": product.category_id.img_url,
            "created_at": product.category_id.created_at.isoformat()
        } if product.category_id else None
        
        sub_category = {
            "name": product.subcategory_id.name,
            "description": product.subcategory_id.description,
            "category": {
                "id": str(product.subcategory_id.category.id),
                "name": product.subcategory_id.category.name
            },
            "id": str(product.subcategory_id.id),
            "img_url": product.subcategory_id.img_url,
            "created_at": product.subcategory_id.created_at.isoformat()
        } if product.subcategory_id else None
        
        sub_sub_category = {
            "name": product.subsubcategory_id.name,
            "description": product.subsubcategory_id.description,
            "category_id": {
                "id": str(product.subsubcategory_id.category_id.id),
                "name": product.subsubcategory_id.category_id.name
            },
            "sub_category_id": {
                "id": str(product.subsubcategory_id.sub_category_id.id),
                "name": product.subsubcategory_id.sub_category_id.name
            },
            "id": str(product.subsubcategory_id.id),
            "img_url": product.subsubcategory_id.img_url,
            "created_at": product.subsubcategory_id.created_at.isoformat()
        } if product.subsubcategory_id else None
        
        items_with_details.append({
            "selected_size": item.size,
            "selected_color": item.color_hexa_code,
            "selected_color_name": item.color,
            "quantity": item.quantity,
            "id": str(item.id),
            "product": {
                "title": product.name,
                "description": product.description,
                "details": product.details,
                "price": float(product.price),
                "delivery_days": product.delivery_days if hasattr(product, 'delivery_days') else None,
                "sku": product.sku_number,
                "stock_quantity": variant.stock_quantity if variant else 0,
                "final_price": float(product.final_price),
                "id": str(product.id),
                "thumbnail_url": product.thumbnail_url if hasattr(product, 'thumbnail_url') else None,
                "total_rating": product.total_rating if hasattr(product, 'total_rating') else None,
                "material": product.material if hasattr(product, 'material') else None,
                "gender": product.gender,
                "category": category,
                "sub_category": sub_category,
                "sub_sub_category": sub_sub_category,
                "gallery": gallery_images,
                "sizes": sizes_with_variants,
                "reviews": []
            }
        })

    return jsonify({
        "data": items_with_details,
        "count": len(items_with_details)
    }), 200

@wishlist_bp.route(WISHLIST_REMOVE_ALL, methods=['DELETE'])
@jwt_required()
@jwt_error_handler
def remove_all_wishlist_items():
    user_id = get_jwt_identity()
    
    delete_result = WishlistItem.objects(user_id=user_id).delete()
    
    if delete_result == 0:
        return jsonify({
            "message": "Your wishlist was already empty",
            "deleted_count": 0
        }), 200
    
    return jsonify({
        "message": "All items removed from wishlist",
        "deleted_count": delete_result
    }), 200

def get_main_product_image(product):
    if hasattr(product, 'images') and product.images:
        return product.images[0].image_url
    return None

@wishlist_bp.route(WISHLIST_MOVE_TO_CART, methods=['POST'])
@jwt_error_handler
@jwt_required()
def move_wishlist_to_cart():
    user_id = get_jwt_identity()
    user = User.objects(id=user_id).first()

    try:
        data = request.get_json()
    except Exception:
        return create_error_response({"error": "Invalid JSON data"}, 400)

    required_fields = ['item_ids']
    is_valid, validation_errors = validate_required_fields(data, required_fields)
    if not is_valid:
        return create_error_response({"error": validation_errors}, 400)

    item_ids = data['item_ids']
    
    if not isinstance(item_ids, list):
        return create_error_response({"error": "item_ids must be an array"}, 400)

    moved_items = []
    not_found_items = []
    already_in_cart_items = []

    for item_id in item_ids:
        # Get wishlist item
        wishlist_item = WishlistItem.objects(
            id=item_id,
            user_id=user_id
        ).first()

        if not wishlist_item:
            not_found_items.append(item_id)
            continue

        # Check if item already exists in cart
        existing_cart_item = ProductCart.objects(
            user_id=user_id,
            product_id=wishlist_item.product_id,
            selected_size=wishlist_item.size,
            selected_color=wishlist_item.color_hexa_code
        ).first()

        if existing_cart_item:
            # Update quantity if already in cart
            existing_cart_item.quantity += wishlist_item.quantity
            existing_cart_item.updated_at = datetime.utcnow()
            existing_cart_item.save()
            already_in_cart_items.append(str(wishlist_item.id))
        else:
            # Create new cart item
            cart_item = ProductCart(
                user_id=user_id,
                product_id=wishlist_item.product_id,
                selected_size=wishlist_item.size,
                selected_color=wishlist_item.color_hexa_code,
                selected_color_name=wishlist_item.color,
                quantity=wishlist_item.quantity
            )
            cart_item.save()

        # Remove from wishlist
        wishlist_item.delete()
        moved_items.append(str(wishlist_item.id))

    response_data = {
        "message": "Items moved to cart",
        "moved_items": moved_items,
        "not_found_items": not_found_items,
        "already_in_cart_items": already_in_cart_items
    }

    return jsonify(response_data), 200