from flask import Blueprint, request, jsonify, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import Address, Seller, User, ProductCart, Products, ProductVariant, ProductVariantImage, Order, OrderItem, ProductPurchaseStats
from datetime import datetime, timedelta
import decimal
from app.utils.utils import create_error_response
from constants import ORDER_PLACE_API, ORDER_LIST_API, GET_ORDER_STATUS_TYPES, ORDER_STATUS, GET_PRODUCT_PURCHASE_STATS, PAYMENT_CALLBACK_API, ORDER_SUCCESS_ROUTE, VERIFY_PAYMENT
from app.utils.jwt_handlers import jwt_error_handler
from mongoengine.queryset.visitor import Q
from app.utils.validation import validate_required_fields
from app.utils.order_helpers import (
    get_user, validate_shipping_address, get_cart_items, 
    validate_promo_code, group_cart_items_by_seller, 
    generate_order_numbers, create_order_items, 
    create_order_object, verify_order_payment, 
    handle_payment_callback, create_razorpay_payment_link
)

order_bp = Blueprint('order', __name__)

@order_bp.route(ORDER_PLACE_API, methods=['POST'])
@jwt_required()
def place_order():
    user_id = get_jwt_identity()
    user = get_user(user_id)
    if not user:
        return create_error_response({'error': 'User not found'}, 404)

    data = request.get_json()
    if not data:
        return create_error_response({'error': 'No data provided'}, 400)

    required_fields = ['cart_items_ids', 'shipping_address_id', 'payment_method']
    is_valid, validation_errors = validate_required_fields(data, required_fields)
    if not is_valid:
        return create_error_response(validation_errors, 400)

    if data['payment_method'] not in ['cod', 'card']:
        return create_error_response({'error': 'Invalid payment method'}, 400)

    shipping_address, error = validate_shipping_address(user_id, data['shipping_address_id'])
    if error:
        return create_error_response(error, error.get('status', 400))

    cart_items, error = get_cart_items(user_id, data.get('cart_items_ids', []))
    if error:
        return create_error_response(error, 400)
    if not cart_items:
        return create_error_response({'error': 'No cart items found'}, 400)

    promo_code = None
    promo_discount = decimal.Decimal('0.00')
    if 'promo_code' in data and data['promo_code']:
        total_amount = sum(
            decimal.Decimal(str(item.product_id.final_price)) * item.quantity
            for item in cart_items if item.product_id
        )
        promo_code, promo_discount = validate_promo_code(user_id, data['promo_code'], total_amount)
        if not promo_code:
            return create_error_response(promo_discount, 400)

    seller_items = group_cart_items_by_seller(cart_items)
    order_numbers = generate_order_numbers(len(seller_items))
    orders = []
    payment_links = []

    try:
        for i, (seller_id, seller_data) in enumerate(seller_items.items()):
            order_items = create_order_items(seller_data['items'])
            
            seller_promo_discount = decimal.Decimal('0.00')
            if promo_code:
                seller_ratio = sum(
                    decimal.Decimal(str(item.final_price / 100)) * item.quantity
                    for item in order_items
                ) / sum(
                    decimal.Decimal(str(item.final_price / 100)) * item.quantity
                    for order in orders for item in order['items']
                ) if orders else decimal.Decimal('1.00')
                seller_promo_discount = promo_discount * seller_ratio

            order = create_order_object(
                user=user,
                seller_data=seller_data,
                order_number=order_numbers[i],
                order_items=order_items,
                shipping_address=shipping_address,
                payment_method=data['payment_method'],
                promo_code=promo_code,
                promo_discount=seller_promo_discount,
                order_note=data.get('order_note', '')
            )
            redirect_url = data.get('redirect_url')
            if data['payment_method'] == 'card':
                payment_link = create_razorpay_payment_link(order, user, redirect_url)
                payment_links.append({
                    'order_number': order_numbers[i],
                    'payment_link_id': payment_link['id'],
                    'payment_link_url': payment_link['short_url'],
                    'amount': order.total_amount
                })
                order.payment_link_id = payment_link['id']

            order.save()
            orders.append({
                'order_id': str(order.id),
                'order_number': order.order_number, 
                'amount': float(order.total_amount),
                'items_count': len(order_items),
                'promo_discount': float(seller_promo_discount)
            })

        if promo_code:
            promo_code.used_count += 1
            promo_code.save()

        response_data = {
            'message': f"{'Payment links and orders' if data['payment_method'] == 'card' else 'Orders'} created successfully",
            'orders': orders,
            'promo_code': promo_code.code if promo_code else None,
            'total_promo_discount': float(promo_discount) if promo_code else 0,
            'payment_links': [{
                'payment_link_id': pl['payment_link_id'],
                'payment_link_url': pl['payment_link_url'],
                'amount': float(pl['amount']),
                'order_number': pl['order_number']
            } for pl in payment_links] if data['payment_method'] == 'card' else []
        }

        return jsonify(response_data), 201

    except Exception as e:
        for order in Order.objects(order_number__in=[o['order_number'] for o in orders]):
            order.delete()
        return create_error_response({
            'error': 'Failed to create order',
            'message': str(e)
        }, 500)

@order_bp.route(PAYMENT_CALLBACK_API, methods=['GET'])
def payment_callback():
    payment_id = request.args.get('razorpay_payment_id')
    payment_link_id = request.args.get('razorpay_payment_link_id')
    payment_link_reference_id = request.args.get('razorpay_payment_link_reference_id')
    order_number = request.args.get('order_number')

    if not all([payment_id, payment_link_id, payment_link_reference_id, order_number]):
        return create_error_response({
            'error': 'Invalid callback parameters',
            'message': 'Missing required callback parameters'
        }, 400)

    try:
        url = f"https://api.razorpay.com/v1/payments/{payment_id}"
        auth = (os.getenv('RAZORPAY_KEY_ID'), os.getenv('RAZORPAY_KEY_SECRET'))
        response = requests.get(url, auth=auth)
        response.raise_for_status()
        payment_data = response.json()

        order, error = handle_payment_callback(payment_id, payment_link_id, payment_link_reference_id, order_number)
        if error:
            redirect_url = f"{os.getenv('APP_BASE_URL')}/order-failed?error={error.get('message')}"
            return redirect(redirect_url, code=302)

        redirect_url = payment_data.get('notes', {}).get('redirect_url')
        if not redirect_url:
            redirect_url = f"{os.getenv('APP_BASE_URL')}/order-success?order_number={order_number}"

        return redirect(redirect_url, code=302)

    except Exception as e:
        redirect_url = f"{os.getenv('APP_BASE_URL')}/order-failed?error={str(e)}"
        return redirect(redirect_url, code=302)

@order_bp.route(ORDER_SUCCESS_ROUTE)
def order_success():
    order_number = request.args.get('order_number')
    status = request.args.get('status')
    return f"Order {order_number} status: {status}"

@order_bp.route(VERIFY_PAYMENT, methods=['POST'])
@jwt_required()
def verify_payment():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    required_fields = ['order_number', 'payment_id']
    is_valid, validation_errors = validate_required_fields(data, required_fields)
    if not is_valid:
        return create_error_response(validation_errors, 400)

    order, error = verify_order_payment(user_id, data['order_number'], data['payment_id'])
    if error:
        return create_error_response(error, error.get('status', 400))

    return jsonify({
        'message': 'Payment verified successfully',
        'order_number': order.order_number,
        'status': order.status
    }), 200


@order_bp.route(ORDER_LIST_API, methods=['GET'])
@jwt_error_handler
@jwt_required()
def get_order_lists():
    user_id = get_jwt_identity()
    user = User.objects(id=user_id).first()

    if not user:
        return create_error_response({'status': 'error', 'message': 'User not found', 'data': None}, 404)
    
    search = request.args.get('search', '').strip()
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    status = request.args.get('status')
    
    orders = Order.objects(user_id=user_id)
    
    if search:
        product_ids = [str(p.id) for p in Products.objects(name__icontains=search).only('id')]
        seller_ids = [str(s.id) for s in Seller.objects(businessName__icontains=search).only('id')]
        
        orders = orders.filter(
            Q(order_number__icontains=search) |
            Q(items__product_id__in=product_ids) |
            Q(seller_id__in=seller_ids)
        )
    
    if from_date:
        try:
            from_date_obj = datetime.strptime(from_date, '%Y-%m-%d')
            orders = orders.filter(created_at__gte=from_date_obj)
        except ValueError:
            pass
    
    if to_date:
        try:
            to_date_obj = datetime.strptime(to_date, '%Y-%m-%d') + timedelta(days=1)
            orders = orders.filter(created_at__lte=to_date_obj)
        except ValueError:
            pass
    
    if status:
        orders = orders.filter(status=status)
    
    orders = orders.order_by('-created_at')
    
    order_list = []
    for order in orders:
        seller = Seller.objects(id=order.seller_id.id).first() if order.seller_id else None
        
        promo_code = None
        if order.applied_promo_code:
            promo_code = PromoCode.objects(id=order.applied_promo_code.id).first()
        
        items = []
        for idx, item in enumerate(order.items):
            product = Products.objects(id=item.product_id.id).first() if item.product_id else None
            if not product:
                continue
                
            category = Category.objects(id=product.category_id.id).first() if product.category_id else None
            sub_category = SubCategory.objects(id=product.subcategory_id.id).first() if product.subcategory_id else None
            
            gallery = []
            sizes = []
            if hasattr(product, 'variants'):
                for variant in product.variants:
                    if variant.color_hexa_code == item.selected_color or variant.color == item.selected_color_name:
                        if hasattr(variant, 'images'):
                            for img in variant.images:
                                gallery.append({
                                    'color': variant.color,
                                    'id': str(img.id),
                                    'img_url': url_for('serve_uploaded_files', filename=img.image_url, _external=True) if img.image_url else None 
                                    
                                })
                    
                    if not any(size['value'] == variant.size for size in sizes):
                        sizes.append({
                            'value': variant.size,
                            'size_type': 'standard',
                            'id': str(variant.id)
                        })
            
            product_data = {
                'id': str(product.id),
                'title': product.name,
                'price': float(product.price),
                'final_price': float(product.final_price),
                'thumbnail_url': getattr(product, 'thumbnail_url', None),
                'category': {
                    'name': category.name if category else None,
                    'id': str(category.id) if category else None
                } if category else None,
                'sub_category': {
                    'name': sub_category.name if sub_category else None,
                    'id': str(sub_category.id) if sub_category else None
                } if sub_category else None,
                'seller': {
                    'business_name': seller.businessName if seller else None,
                    'id': str(seller.id) if seller else None
                },
                'gallery': gallery,
                'sizes': sizes
            }
            
            items.append({
                'item_id': f"{order.id}-{idx}",
                'product': product_data,
                'quantity': item.quantity,
                'price': float(item.price),
                'final_price': float(item.final_price),
                'selected_size': item.selected_size,
                'selected_color': item.selected_color,
                'selected_color_name': item.selected_color_name
            })
        
        order_data = {
            'id': str(order.id),
            'order_number': order.order_number,
            'status': order.status,
            'total_amount': float(order.total_amount),
            'created_at': order.created_at.isoformat() + 'Z',
            'items': items,
            'payment_method': order.payment_method,
            'payment_status': order.payment_status,
            'seller': {
                'id': str(seller.id) if seller else None,
                'business_name': seller.businessName if seller else None
            },
            'promo_code': {
                'id': str(promo_code.id) if promo_code else None,
                'code': promo_code.code if promo_code else None,
                'discount_type': promo_code.discount_type if promo_code else None,
                'discount_value': float(promo_code.discount_value) if promo_code else 0,
                'discount_amount': float(order.promo_code_discount) if hasattr(order, 'promo_code_discount') else 0
            } if promo_code else None
        }
        order_list.append(order_data)
    
    return jsonify({
        'status': 'success',
        'message': 'Orders fetched successfully',
        'data': order_list,
        'count': len(order_list)
    })

@order_bp.route(GET_ORDER_STATUS_TYPES, methods=['GET'])
@jwt_error_handler
@jwt_required()
def get_order_statuses():
    return jsonify({
        'status': 'success',
        'message': 'Order statuses fetched successfully',
        'data': ORDER_STATUS
    }), 200


@order_bp.route(GET_PRODUCT_PURCHASE_STATS, methods=['GET'])
def get_top_purchased_products():
    try:
        limit = request.args.get('limit', default=10, type=int)
        if limit <= 0 or limit > 100:
            limit = 10

        top_products = ProductPurchaseStats.objects.order_by('-purchase_count').limit(limit)
        
        result = []
        for product in top_products:
            result.append({
                'product_id': str(product.product_id),
                'product_name': product.product_name,
                'purchase_count': product.purchase_count,
                'last_purchased_at': product.last_purchased_at.isoformat() if product.last_purchased_at else None
            })
        
        return jsonify({
            'success': True,
            'data': {
                'top_products': result,
                'count': len(result)
            }
        })

    except Exception as e:
        return create_error_response({'error': {
            'success': False,
            'error': str(e)
        }},500)