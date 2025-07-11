from flask import request, session, redirect, url_for, render_template, jsonify
from . import admin_api
from app.models import Order, User, Seller
from bson import ObjectId
from constants import ORDER_LIST_WEB_URL, ORDER_STATUS_UPDATE_WEB_URL, ORDER_STATUS, ORDER_DETAILS_PAGE_WEB_URL
from app.utils.utils import create_error_response
from datetime import datetime

@admin_api.route(ORDER_LIST_WEB_URL, methods=['GET', 'POST'])
def product_order_list_page():    
    user = _authenticate_user()
    if not user:
        return redirect(url_for('admin_api.login_page'))
    
    if request.method == 'GET':
        return _render_order_list(user)
    else:
        return _get_orders_json(user)

def _authenticate_user():
    if 'user_id' not in session:
        return None
    
    user = User.objects(id=session['user_id']).first()
    if not user:
        session.clear()
        return None
    
    return user

def _build_base_query(user):
    if user.is_admin:
        return {}
    
    seller = Seller.objects(user_id=ObjectId(user.id)).first()
    if not seller:
        raise PermissionError("Seller profile not found")
    
    return {'seller_id': seller.id}

def _apply_filters(base_query, filters):
    query = base_query.copy()
    
    if filters.get('search'):
        search = filters['search'].strip()
        query['$or'] = [
            {'order_number': {'$regex': search, '$options': 'i'}},
            {'customer_name': {'$regex': search, '$options': 'i'}},
            {'customer_email': {'$regex': search, '$options': 'i'}},
            {'customer_phone': {'$regex': search, '$options': 'i'}}
        ]
    
    if filters.get('status') and filters['status'] != 'all':
        query['status'] = filters['status']
    
    if filters.get('start_date'):
        query['created_at'] = {'$gte': datetime.fromisoformat(filters['start_date'])}
    if filters.get('end_date'):
        if 'created_at' in query:
            query['created_at']['$lte'] = datetime.fromisoformat(filters['end_date'])
        else:
            query['created_at'] = {'$lte': datetime.fromisoformat(filters['end_date'])}
    
    return query

def _get_pagination_params(request_method):
    params = {
        'max_items_per_page': 100
    }
    
    if request_method == 'GET':
        params.update({
            'page': 1,
            'items_per_page': 10
        })
    else:
        data = request.get_json() or {}
        items_per_page = int(data.get('items_per_page', 10))
        items_per_page = max(1, min(items_per_page, params['max_items_per_page']))
        
        params.update({
            'page': max(1, int(data.get('page', 1))),
            'items_per_page': items_per_page
        })
    
    return params

def _render_order_list(user):
    try:
        query = _build_base_query(user)
        pagination = _get_pagination_params('GET')
        
        total_orders = Order.objects(__raw__=query).count()
        total_pages = (total_orders + pagination['items_per_page'] - 1) // pagination['items_per_page']
        
        orders = Order.objects(__raw__=query).order_by('-created_at').limit(pagination['items_per_page'])

        return render_template(
            "admin/orderPage/orders.html",
            orders=orders,
            current_page=pagination['page'],
            total_pages=total_pages,
            total_orders=total_orders,
            items_per_page=pagination['items_per_page'],
            is_admin=user.is_admin
        )
    except PermissionError as e:
        return render_template("admin/orderPage/orders.html"), 403
    except Exception as e:
        print(f"Error rendering order list: {str(e)}")
        return render_template("admin/orderPage/orders.html"), 500

def _get_orders_json(user):
    try:
        data = request.get_json() or {}
        
        filters = {
            'search': data.get('search', '').strip(),
            'status': data.get('status', '').strip(),
            'start_date': data.get('start_date', '').strip(),
            'end_date': data.get('end_date', '').strip()
        }
        
        pagination = _get_pagination_params('POST')
        
        base_query = _build_base_query(user)
        query = _apply_filters(base_query, filters)
        
        total_orders = Order.objects(__raw__=query).count()
        total_pages = max(1, (total_orders + pagination['items_per_page'] - 1) // pagination['items_per_page'])
        page = min(pagination['page'], total_pages)
        
        orders = Order.objects(__raw__=query)\
                     .order_by('-created_at')\
                     .skip((page - 1) * pagination['items_per_page'])\
                     .limit(pagination['items_per_page'])

        orders_data = [_serialize_order(order) for order in orders]

        return jsonify({
            'success': True,
            'orders': orders_data,
            'current_page': page,
            'total_pages': total_pages,
            'total_orders': total_orders,
            'items_per_page': pagination['items_per_page']
        })

    except PermissionError as e:
        return jsonify({'success': False, 'error': str(e)}), 403
    except ValueError as e:
        print(f"Invalid request parameters: {str(e)}")
        return jsonify({'success': False, 'error': 'Invalid request parameters'}), 400
    except Exception as e:
        print(f"Error fetching orders: {str(e)}")
        return jsonify({'success': False, 'error': 'Server error occurred'}), 500

def _serialize_order(order):
    return {
        'id': str(order.id),
        'order_number': order.order_number,
        'created_at': order.created_at.isoformat(),
        'updated_at': order.updated_at.isoformat() if hasattr(order, 'updated_at') else None,
        'total_amount': float(order.total_amount),
        'status': order.status,
        'payment_method': order.payment_method,
        'payment_status': order.payment_status,
        'customer_name': getattr(order, 'customer_name', ''),
        'customer_email': getattr(order, 'customer_email', ''),
        'customer_phone': getattr(order, 'customer_phone', ''),
        'items_count': len(order.items) if hasattr(order, 'items') else 0
    }
    
@admin_api.route(ORDER_STATUS_UPDATE_WEB_URL, methods=['POST'])
def update_order_status(order_id):
    if 'user_id' not in session:
        return create_error_response({'error': 'Unauthorized'}, 401)
    
    user = User.objects(id=session['user_id']).first()
    if not user:
        return create_error_response({'error': 'User not found'}, 401)

    try:
        order = Order.objects(id=order_id).first()
        if not order:
            return create_error_response({'error': 'Order not found'}, 404)
        
        if not user.is_admin:
            seller = Seller.objects(user_id=user.id).first()
            if not seller or str(order.seller_id.id) != str(seller.id):
                return create_error_response({'error': 'Unauthorized to update this order'}, 403)

        status = request.form.get('status')
        valid_statuses = ORDER_STATUS
        
        if status not in valid_statuses:
            return create_error_response({'error': 'Invalid status'}, 400)

        order.status = status
        order.save()
        
        print(f"Order {order_id} status updated to {status} by user {user.id}")
        
        return jsonify({'success': True, 'status': status})

    except Exception as e:
        print(f"Error updating order status: {str(e)}")
        return create_error_response({'error': f'Server error: {str(e)}'}, 500)


@admin_api.route(ORDER_DETAILS_PAGE_WEB_URL, methods=['GET'])
def order_details_page(order_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))
    
    user = User.objects(id=session['user_id']).first()
    if not user:
        return redirect(url_for('admin_api.login_page'))

    try:
        order = Order.objects(id=ObjectId(order_id)).first()
        if not order:
            return render_template("admin/orderPage/orders.html"), 404
        
        if not user.is_admin:
            seller = Seller.objects(user_id=user.id).first()
            if not seller or str(order.seller_id.id) != str(seller.id):
                return render_template("admin/orderPage/orders.html"), 403

        customer = None
        if order.customer_id:
            customer = User.objects(id=order.customer_id).first()

        return render_template(
            "admin/orderPage/order_details.html",
            order=order,
            customer=customer,
            is_admin=user.is_admin
        )

    except Exception as e:
        print(f"Error in order_details_page: {str(e)}")
        return render_template("admin/orderPage/orders.html"), 500