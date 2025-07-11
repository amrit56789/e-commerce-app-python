import os
import random
import string
import decimal
import requests
import json
from datetime import datetime, timedelta
from bson import ObjectId
from flask import jsonify, redirect, request
from app.models import User, Address, ProductCart, Order, OrderItem, PromoCode
from app.utils.utils import create_error_response
from app.utils.validation import validate_required_fields

from constants import RAZOR_PAY_PAYMENT_LINK

def get_user(user_id):
    try:
        return User.objects(id=user_id).first()
    except DoesNotExist:
        return None

def validate_shipping_address(user_id, address_id):
    try:
        address = Address.objects(user_id=user_id, id=ObjectId(address_id)).first()
        if not address:
            return None, {'error': 'Shipping address not found', 'message': 'The specified shipping address doesn\'t exist or doesn\'t belong to you'}
        
        address_fields = ['line1', 'city', 'state', 'postal_code', 'country']
        if not all(getattr(address, field) for field in address_fields):
            return None, {'error': 'Incomplete shipping address', 'message': 'The shipping address is missing required fields'}
        
        return address, None
    except Exception as e:
        return None, {'error': 'Invalid shipping address', 'message': str(e)}

def get_cart_items(user_id, cart_items_ids):
    cart_items_query = ProductCart.objects(user_id=user_id)
    
    if cart_items_ids:
        try:
            cart_items_ids = [ObjectId(id) for id in cart_items_ids]
            return cart_items_query.filter(id__in=cart_items_ids), None
        except Exception:
            return None, {'error': 'Invalid cart item IDs format'}
    else:
        return cart_items_query, None

def validate_promo_code(user_id, promo_code_str, total_amount):
    current_datetime = datetime.utcnow()
    promo_code = PromoCode.objects(
        code=promo_code_str.upper().strip(),
        is_active=True,
        start_date__lte=current_datetime
    ).first()
    
    if not promo_code:
        return None, {'error': 'Invalid or expired promo code'}
    
    if promo_code.expiry_date and promo_code.expiry_date < current_datetime:
        return None, {'error': 'Promo code has expired'}
    
    if promo_code.only_first_order and Order.objects(user_id=user_id).count() > 0:
        return None, {'error': 'This promo code is only valid for first orders'}
    
    if total_amount < decimal.Decimal(str(promo_code.min_order_amount)):
        return None, {'error': f'Minimum order amount of {promo_code.min_order_amount} required'}
    
    if promo_code.max_uses and promo_code.used_count >= promo_code.max_uses:
        return None, {'error': 'Promo code usage limit reached'}
    
    # Ensure discount is positive
    promo_discount = abs(promo_code.calculate_discount(float(total_amount)))
    return promo_code, decimal.Decimal(str(promo_discount))
    
def group_cart_items_by_seller(cart_items):
    seller_items = {}
    for cart_item in cart_items:
        product = cart_item.product_id
        if not product:
            continue
        seller_id = str(product.seller_id.id) if product.seller_id else None
        if seller_id not in seller_items:
            seller_items[seller_id] = {'seller': product.seller_id, 'items': []}
        seller_items[seller_id]['items'].append(cart_item)
    return seller_items

def generate_order_numbers(count):
    order_numbers = set()
    while len(order_numbers) < count:
        order_number = 'ORD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        order_numbers.add(order_number)
    return list(order_numbers)

def create_order_items(cart_items):
    order_items = []
    for cart_item in cart_items:
        product = cart_item.product_id
        price = decimal.Decimal(str(product.price))
        discount_percent = decimal.Decimal(str(product.discount_percent)) if hasattr(product, 'discount_percent') else decimal.Decimal('0')
        final_price = price * (1 - discount_percent / 100)
        
        order_item = OrderItem(
            product_id=product,
            selected_size=cart_item.selected_size,
            selected_color=cart_item.selected_color,
            selected_color_name=cart_item.selected_color_name,
            quantity=cart_item.quantity,
            price=price,
            discount_percent=discount_percent,
            final_price=int(final_price * 100)
        )
        order_items.append(order_item)
    return order_items

def create_order_object(user, seller_data, order_number, order_items, shipping_address, payment_method, promo_code, promo_discount, order_note=''):
    total_amount = decimal.Decimal('0.00')
    for item in order_items:
        total_amount += decimal.Decimal(str(item.final_price / 100)) * item.quantity
    
    if promo_code:
        total_amount -= promo_discount
    
    return Order(
        user_id=user,
        seller_id=seller_data['seller'] if seller_data['seller'] else None,
        order_number=order_number,
        items=order_items,
        total_amount=total_amount,
        status='pending',
        shipping_address={
            'id': str(shipping_address.id),
            'address_line1': shipping_address.line1,
            'address_line2': shipping_address.line2 if shipping_address.line2 else '',
            'city': shipping_address.city,
            'state': shipping_address.state,
            'postal_code': shipping_address.postal_code,
            'country': shipping_address.country,
            'type': shipping_address.type if shipping_address.type else 'home'
        },
        payment_method=payment_method,
        payment_status='pending',
        order_note=order_note,
        applied_promo_code=promo_code,
        promo_code_discount=promo_discount,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )

def create_razorpay_payment_link(order, user, redirect_url):
    customer_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or "Customer"
    # Use a static URL for testing
    static_redirect_url = "https://your-frontend-domain.com/order-success"  # Change this to your actual frontend URL
    return generate_razorpay_payment_link(
        amount=float(order.total_amount),
        reference_id=order.order_number,
        customer_name=customer_name,
        customer_email=user.email,
        customer_phone=user.phone_number if hasattr(user, 'phone_number') and user.phone_number else '',
        description=f"Order {order.order_number}",
        redirect_url=static_redirect_url  # Use static URL here
    )

def generate_razorpay_payment_link(amount, reference_id, customer_name, customer_email, customer_phone='', description=None, redirect_url=None):
    amount_in_paise = int(amount * 100)
    expire_by = int((datetime.utcnow() + timedelta(days=7)).timestamp())
    
    payload = {
        'amount': amount_in_paise,
        'currency': 'INR',
        'description': description or f"Order {reference_id}",
        'customer': {
            'name': customer_name,
            'email': customer_email,
            'contact': customer_phone or ''
        },
        'reference_id': reference_id,
        'notify': {
            'sms': bool(customer_phone),
            'email': bool(customer_email)
        },
        'reminder_enable': True,
        'expire_by': expire_by,
        'notes': {
            'order_number': reference_id,
            'redirect_url': redirect_url
        },
        'callback_url': f"{os.getenv('API_BASE_URL')}/api/payment-callback",
        'callback_method': 'get'
    }
    print(f"Generated callback URL: {os.getenv('API_BASE_URL')}/api/payment-callback")


    auth = (os.getenv('RAZORPAY_KEY_ID'), os.getenv('RAZORPAY_KEY_SECRET'))
    headers = {'Content-Type': 'application/json'}
    
    response = requests.post(RAZOR_PAY_PAYMENT_LINK, data=json.dumps(payload), auth=auth, headers=headers)
    response.raise_for_status()
    return response.json()

def get_razorpay_payment_link(payment_link_id):
    url = f"https://api.razorpay.com/v1/payment_links/{payment_link_id}"
    auth = (os.getenv('RAZORPAY_KEY_ID'), os.getenv('RAZORPAY_KEY_SECRET'))
    
    response = requests.get(url, auth=auth)
    response.raise_for_status()
    return response.json()

def handle_payment_callback(payment_id, payment_link_id, payment_link_reference_id, order_number):
    payment_link = get_razorpay_payment_link(payment_link_id)
    if payment_link['status'] != 'paid':
        return None, {'error': 'Payment not completed', 'message': 'Payment link status is not paid'}
    
    order = Order.objects(order_number=order_number, payment_link_id=payment_link_id).first()
    if not order:
        return None, {'error': 'Order not found', 'message': 'No matching order found'}
    
    order.payment_id = payment_id
    order.payment_status = 'paid'
    order.status = 'confirmed'
    order.updated_at = datetime.utcnow()
    order.save()
    
    return order, None

def verify_order_payment(user_id, order_number, payment_id):
    order = Order.objects(user_id=user_id, order_number=order_number, payment_id=payment_id).first()
    if not order:
        return None, {'error': 'Order not found'}
    
    payment_link = get_razorpay_payment_link(order.payment_link_id)
    if payment_link['status'] != 'paid':
        return None, {'error': 'Payment not verified', 'message': 'Payment status is not paid'}
    
    if order.payment_status != 'paid':
        order.payment_status = 'paid'
        order.status = 'confirmed'
        order.updated_at = datetime.utcnow()
        order.save()
    
    return order, None