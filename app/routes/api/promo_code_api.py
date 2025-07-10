from datetime import datetime
from bson import ObjectId
from flask import request, jsonify, Blueprint
from app.models import Order, Products, PromoCode, ProductCart
from constants import VALIDATE_PROMO_CODE, PROMO_CODE_LIST
from app.utils.utils import create_error_response
from app.utils.jwt_handlers import jwt_error_handler
from flask_jwt_extended import jwt_required, get_jwt_identity

promo_bp = Blueprint('promo_code', __name__)

@promo_bp.route(VALIDATE_PROMO_CODE, methods=['POST'])
@jwt_error_handler
@jwt_required()
def validate_promo_code():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or 'promo_code' not in data or 'cart_items_ids' not in data:
        return create_error_response({"error": 'Both promo_code and cart_items_ids are required'}, 400)
    
    promo_code_str = data['promo_code'].upper().strip()
    cart_items_ids = data['cart_items_ids']
    
    try:
        cart_items = ProductCart.objects(id__in=[ObjectId(item_id) for item_id in cart_items_ids], user_id=user_id)
        
        total_amount = 0
        for item in cart_items:
            product = Products.objects(id=item.product_id.id).first()
            if product:
                # Use final_price instead of price
                total_amount += float(product.final_price) * item.quantity
    
    except Exception as e:
        return create_error_response({"error": 'Invalid cart items'}, 400)
    
    current_datetime = datetime.utcnow()
    promo_code = PromoCode.objects(
        code=promo_code_str,
        is_active=True,
        start_date__lte=current_datetime,
    ).first()
    
    if not promo_code:
        return create_error_response({"error": 'Invalid or expired promo code'}, 404)
    
    if promo_code.expiry_date and promo_code.expiry_date < current_datetime:
        return create_error_response({"error": 'Promo code has expired'}, 400)
    
    if promo_code.only_first_order:
        has_previous_orders = Order.objects(
            user_id=user_id, 
            status__in=['completed', 'delivered']
        ).count() > 0
        if has_previous_orders:
            return create_error_response({"error": 'This promo code is only valid for first orders'}, 400)
    
    if total_amount < float(promo_code.min_order_amount):
        return create_error_response(
           {"error":  f'Minimum order amount of {promo_code.min_order_amount} required. Your current order amount is {total_amount}'}, 
            400
        )
    
    if promo_code.max_uses and promo_code.used_count >= promo_code.max_uses:
        return create_error_response({"error": 'Promo code usage limit reached'}, 400)
    
    discount_amount = promo_code.calculate_discount(total_amount)
    discounted_amount = total_amount - discount_amount
    
    response = {
        'message': 'Promo code is valid and can be applied',
        'promo_code': promo_code.code,
        'discount_amount': float(discount_amount),
        'total_amount': float(total_amount),
        'discounted_amount': float(discounted_amount),
        'discount_details': {
            'type': promo_code.discount_type,
            'value': float(promo_code.discount_value),
            'min_order_amount': float(promo_code.min_order_amount),
            'max_discount': float(promo_code.max_discount_amount) if promo_code.max_discount_amount else None
        }
    }
    
    return jsonify(response), 200


@promo_bp.route(PROMO_CODE_LIST, methods=['GET'])
def list_promo_codes():
    try:
        current_date = datetime.utcnow()
        promo_codes = PromoCode.objects(
            is_active=True,
            start_date__lte=current_date,
            expiry_date__gte=current_date
        ).order_by('-created_at')
        
        promo_codes_data = []
        for promo in promo_codes:
            promo_data = {
                'id': str(promo.id),
                'code': promo.code,
                'is_active': promo.is_active,
                'description': promo.description,
                'discount_type': promo.discount_type,
                'discount_value': float(promo.discount_value),
                'min_order_amount': float(promo.min_order_amount),
                'max_discount_amount': float(promo.max_discount_amount),
                'start_date': promo.start_date.strftime('%Y-%m-%d') if promo.start_date else None,
                'expiry_date': promo.expiry_date.strftime('%Y-%m-%d') if promo.expiry_date else None,
                'max_uses': promo.max_uses,
                'uses_per_user': promo.uses_per_user,
                'only_first_order': promo.only_first_order,
                'created_at': promo.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
            promo_codes_data.append(promo_data)
        
        return jsonify({
            'success': True,
            'data': promo_codes_data,
            'count': len(promo_codes_data)
        }), 200
    
    except Exception as e:
        return create_error_response({"error": f'Server error: {str(e)}'}, 500)