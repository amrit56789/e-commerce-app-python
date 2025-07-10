from flask import Blueprint, request, jsonify, session
from app.models.saveforlater import SaveForLater, SaveForLaterItem
from app.models.products import ProductVariant, Products
from app.models.productCart import ProductCart
from datetime import datetime
from constants import SAVEFORLATER_ADD, SAVEFORLATER_REMOVE, SAVEFORLATER_LIST, SAVEFORLATER_TO_CART, ALLOWED_SIZES

saveforlater_bp = Blueprint('saveforlater_bp', __name__)

def get_user_id():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    return session['user_id']

@saveforlater_bp.route(SAVEFORLATER_ADD, methods=['POST'])
def add_to_saveforlater():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    try:
        data = request.get_json()
    except Exception:
        return jsonify({"error": "Invalid JSON data"}), 400

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid data format, expected JSON object"}), 400

    product_id = data.get('product_id')
    variant_id = data.get('variant_id')
    size = data.get('size')
    quantity = data.get('quantity', 1)

    user_id = get_user_id()
    if isinstance(user_id, tuple):
        return user_id

    if not product_id:
        return jsonify({"error": "product_id is required"}), 400

    if size and size not in ALLOWED_SIZES:
        return jsonify({"error": f"Invalid size. Must be one of {ALLOWED_SIZES}"}), 400

    try:
        quantity = int(quantity)
        if quantity < 1:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"error": "quantity must be a positive integer"}), 400

    product = Products.objects(id=product_id).first()
    if not product:
        return jsonify({"error": "Product not found"}), 404

    price = float(product.final_price)

    variant = None
    if variant_id or size:
        query = ProductVariant.objects(product_id=product)
        if variant_id:
            query = query.filter(id=variant_id)
        if size:
            query = query.filter(size=size)
        variant = query.first()
        if not variant:
            return jsonify({"error": "Variant not found for the specified product and size"}), 404
        price = float(product.final_price)

    saveforlater_item = SaveForLaterItem(
        product_id=product_id,
        variant_id=str(variant.id) if variant else None,
        size=size,
        quantity=quantity,
        price=price,
        original_price=float(product.price),
        discount=float(product.price - product.final_price) if product.discount_price else 0.0
    )

    try:
        saveforlater_item.validate_stock(Products)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    saveforlater = SaveForLater.objects(user_id=user_id).first()
    if not saveforlater:
        saveforlater = SaveForLater(user_id=user_id, items=[], created_at=datetime.utcnow())

    existing_item = None
    for item in saveforlater.items:
        if item.product_id == product_id and item.variant_id == saveforlater_item.variant_id and item.size == size:
            existing_item = item
            break

    if existing_item:
        existing_item.quantity += quantity
        try:
            existing_item.validate_stock(Products)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
    else:
        saveforlater.items.append(saveforlater_item)

    saveforlater.save()

    response_data = {
        "message": "Item added to save for later",
        "saveforlater": {
            "id": str(saveforlater.id),
            "user_id": str(saveforlater.user_id),
            "items": [
                {
                    "product_id": str(item.product_id),
                    "variant_id": str(item.variant_id) if item.variant_id else None,
                    "size": item.size,
                    "quantity": item.quantity,
                    "price": item.price,
                    "original_price": item.original_price,
                    "total_price": item.price * item.quantity,
                    "added_at": item.added_at.isoformat()
                } for item in saveforlater.items
            ],
            "created_at": saveforlater.created_at.isoformat(),
            "updated_at": saveforlater.updated_at.isoformat()
        }
    }

    return jsonify(response_data), 200

@saveforlater_bp.route(SAVEFORLATER_REMOVE, methods=['POST'])
def remove_from_saveforlater():
    user_id = get_user_id()
    if isinstance(user_id, tuple):
        return user_id

    data = request.json
    product_id = data.get('product_id')
    variant_id = data.get('variant_id')
    size = data.get('size')

    if not product_id:
        return jsonify({"error": "product_id is required"}), 400

    saveforlater = SaveForLater.objects(user_id=user_id).first()
    if not saveforlater:
        return jsonify({"error": "Save for later not found"}), 404

    saveforlater.items = [
        item for item in saveforlater.items
        if not (item.product_id == product_id and item.variant_id == variant_id and item.size == size)
    ]
    saveforlater.save()

    return jsonify({
        "message": "Item removed from save for later",
        "saveforlater": {
            "items": [
                {
                    "product_id": item.product_id,
                    "variant_id": item.variant_id,
                    "size": item.size,
                    "quantity": item.quantity,
                    "price": item.price,
                    "total_price": item.price * item.quantity,
                    "added_at": item.added_at.isoformat()
                } for item in saveforlater.items
            ]
        }
    }), 200

@saveforlater_bp.route(SAVEFORLATER_LIST, methods=['GET'])
def get_saveforlater():
    user_id = get_user_id()
    if isinstance(user_id, tuple):
        return user_id

    saveforlater = SaveForLater.objects(user_id=user_id).first()

    if not saveforlater:
        return jsonify({"items": []}), 200

    return jsonify({
        "items": [
            {
                "product_id": item.product_id,
                "variant_id": item.variant_id,
                "size": item.size,
                "quantity": item.quantity,
                "price": item.price,
                "total_price": item.price * item.quantity,
                "added_at": item.added_at.isoformat()
            } for item in saveforlater.items
        ],
    }), 200

@saveforlater_bp.route(SAVEFORLATER_TO_CART, methods=['POST'])
def move_to_cart():
    user_id = get_user_id()
    if isinstance(user_id, tuple):
        return user_id

    data = request.json
    product_id = data.get('product_id')
    variant_id = data.get('variant_id')
    size = data.get('size')

    if not product_id:
        return jsonify({"error": "product_id is required"}), 400

    saveforlater = SaveForLater.objects(user_id=user_id).first()
    if not saveforlater:
        return jsonify({"error": "Save for later not found"}), 404

    target_item = None
    for item in saveforlater.items:
        if item.product_id == product_id and item.variant_id == variant_id and item.size == size:
            target_item = item
            break

    if not target_item:
        return jsonify({"error": "Item not found in save for later"}), 404

    cart = Cart.objects(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id, items=[], created_at=datetime.utcnow())

    cart_item = CartItem(
        product_id=target_item.product_id,
        variant_id=target_item.variant_id,
        size=target_item.size,
        quantity=target_item.quantity,
        price=target_item.price,
        original_price=target_item.original_price,
        discount=target_item.discount
    )

    try:
        cart_item.validate_stock(Products)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    existing_item = None
    for item in cart.items:
        if item.product_id == cart_item.product_id and item.variant_id == cart_item.variant_id and item.size == cart_item.size:
            existing_item = item
            break

    if existing_item:
        existing_item.quantity += cart_item.quantity
        try:
            existing_item.validate_stock(Products)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
    else:
        cart.items.append(cart_item)

    saveforlater.items = [
        item for item in saveforlater.items
        if not (item.product_id == product_id and item.variant_id == variant_id and item.size == size)
    ]

    cart.save()
    saveforlater.save()

    return jsonify({
        "message": "Item moved to cart",
        "cart": {
            "items": [
                {
                    "product_id": item.product_id,
                    "variant_id": item.variant_id,
 "size": item.size,
                    "quantity": item.quantity,
                    "price": item.price,
                    "total_price": item.price * item.quantity
                } for item in cart.items
            ],
            "total_price": cart.total_price
        }
    }), 200