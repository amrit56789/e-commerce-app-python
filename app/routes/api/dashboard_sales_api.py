from flask import Blueprint, jsonify, session, request
from datetime import datetime, timedelta
import pytz
from app.extensions import db
from mongoengine.queryset.visitor import Q
from bson import ObjectId
from app.models import Order, User, Products, Seller
from constants import SALES_OVERVIEW_API, SALES_OVER_TIME_API, RECENT_SALES_API, TOP_PRODUCT_SALES_API, GET_SALES_SELLER

sales_api = Blueprint('sales_api', __name__)

def get_period_dates(period, now=None):
    if not now:
        now = datetime.now(pytz.UTC)
    start_date = end_date = None
    
    if period == 'this_month':
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = (start_date + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
    elif period == 'last_month':
        end_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - timedelta(seconds=1)
        start_date = end_date.replace(day=1)
    elif period == 'this_quarter':
        quarter = (now.month - 1) // 3 + 1
        start_date = now.replace(month=(quarter-1)*3+1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = (start_date + timedelta(days=92)).replace(day=1) - timedelta(seconds=1)
    elif period == 'this_year':
        start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date.replace(month=12, day=31, hour=23, minute=59, second=59)
    
    return start_date, end_date

@sales_api.route(SALES_OVERVIEW_API, methods=['GET'])
def sales_overview():
    try:
        # Authentication and authorization
        user_id = session.get('user_id')
        if not user_id:
            return redirect(url_for('admin_api.login_page'))
        
        user = User.objects(id=user_id).first()
        if not user:
            return create_error_response({'error': 'User not found'}, 404)
        
        # Get query parameters
        seller_id = request.args.get('seller_id')
        period = request.args.get('period')
        start_date_param = request.args.get('start_date')
        end_date_param = request.args.get('end_date')
        
        now = datetime.now(pytz.UTC)
        
        # Date range handling
        if start_date_param and end_date_param:
            # Custom date range provided
            try:
                start_date = datetime.strptime(start_date_param, '%Y-%m-%d').replace(
                    hour=0, minute=0, second=0, microsecond=0, tzinfo=pytz.UTC
                )
                end_date = datetime.strptime(end_date_param, '%Y-%m-%d').replace(
                    hour=23, minute=59, second=59, microsecond=0, tzinfo=pytz.UTC
                )
                
                # Calculate previous period (same duration before start_date)
                delta = end_date - start_date
                prev_end_date = start_date - timedelta(seconds=1)
                prev_start_date = prev_end_date - delta
            except ValueError as e:
                return create_error_response({'error': f'Invalid date format: {str(e)}. Use YYYY-MM-DD'}, 400)
        elif period:
            # Period-based date range
            start_date, end_date = get_period_dates(period, now)
            
            # Calculate previous period dates
            prev_end_date = start_date - timedelta(seconds=1)
            if period == 'this_month':
                prev_start_date = (start_date - timedelta(days=1)).replace(day=1)
            elif period == 'last_month':
                prev_start_date = (start_date - timedelta(days=1)).replace(day=1)
                prev_end_date = start_date - timedelta(seconds=1)
            elif period == 'this_quarter':
                prev_start_date = (start_date - timedelta(days=92)).replace(day=1)
            elif period == 'this_year':
                prev_start_date = start_date.replace(year=start_date.year-1)
                prev_end_date = end_date.replace(year=end_date.year-1)
            else:
                prev_start_date = start_date - timedelta(days=30)  # default 30-day comparison
        else:
            # Default to current month if no parameters provided
            start_date, end_date = get_period_dates('this_month', now)
            prev_start_date = (start_date - timedelta(days=1)).replace(day=1)
            prev_end_date = start_date - timedelta(seconds=1)
        
        # Build main query
        query = Q(
            created_at__gte=start_date,
            created_at__lte=end_date,
            status__in=['confirmed', 'processing', 'shipped', 'outOfDelivery', 'delivered']
        )
        
        # Build previous period query
        prev_query = Q(
            created_at__gte=prev_start_date,
            created_at__lte=prev_end_date,
            status__in=['confirmed', 'processing', 'shipped', 'outOfDelivery', 'delivered']
        )
        
        # Apply seller filter if needed
        if user.is_admin:
            if seller_id:
                seller = Seller.objects(id=seller_id).first()
                if not seller:
                    return create_error_response({'error': 'Seller not found'}, 404)
                query &= Q(seller_id=seller)
                prev_query &= Q(seller_id=seller)
        else:
            seller = Seller.objects(user_id=user).first()
            if not seller:
                return create_error_response({'error': 'Seller profile not found'}, 404)
            query &= Q(seller_id=seller)
            prev_query &= Q(seller_id=seller)
            
        # Execute queries
        orders = Order.objects(query)
        prev_orders = Order.objects(prev_query)

        # Calculate metrics
        total_sales = sum(order.total_amount for order in orders) or 0
        prev_total_sales = sum(order.total_amount for order in prev_orders) or 0
        sales_change = ((total_sales - prev_total_sales) / prev_total_sales * 100) if prev_total_sales > 0 else 0

        order_count = orders.count()
        prev_order_count = prev_orders.count()
        order_change = ((order_count - prev_order_count) / prev_order_count * 100) if prev_order_count > 0 else 0

        avg_order_value = total_sales / order_count if order_count > 0 else 0
        prev_avg_order_value = prev_total_sales / prev_order_count if prev_order_count > 0 else 0
        avg_order_change = ((avg_order_value - prev_avg_order_value) / prev_avg_order_value * 100) if prev_avg_order_value > 0 else 0

        # Prepare response
        response_data = {
            'status': 'success',
            'data': {
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'previous_start': prev_start_date.isoformat(),
                    'previous_end': prev_end_date.isoformat()
                },
                'total_sales': float(total_sales),
                'total_sales_change': float(sales_change),
                'order_count': order_count,
                'order_count_change': float(order_change),
                'avg_order_value': float(avg_order_value),
                'avg_order_change': float(avg_order_change),
            }
        }
        
        return jsonify(response_data), 200
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
        }), 500

@sales_api.route(SALES_OVER_TIME_API, methods=['GET'])
def sales_over_time():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return create_error_response({'error': 'User not logged in'}, 401)
        
        user = User.objects(id=user_id).first()
        if not user:
            return create_error_response({'error': 'User not found'}, 404)
        
        seller_id = request.args.get('seller_id')
        period = request.args.get('period', 'monthly')
        filter_period = request.args.get('filter_period', 'this_month')
        
        now = datetime.now(pytz.UTC)
        start_date, end_date = get_period_dates(filter_period, now)
        labels = []
        sales_data = []

        if period == 'monthly':
            months = (end_date - start_date).days // 30 + 1
            for i in range(months):
                month_start = (start_date + timedelta(days=30 * i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)
                if month_end <= end_date:
                    labels.append(month_start.strftime('%b %Y'))
                    sales_data.append(get_sales_for_period(user, seller_id, month_start, month_end))
        elif period == 'weekly':
            weeks = (end_date - start_date).days // 7 + 1
            for i in range(weeks):
                week_start = (start_date + timedelta(weeks=i)).replace(hour=0, minute=0, second=0, microsecond=0)
                week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
                if week_end <= end_date:
                    labels.append(f"Week {week_start.isocalendar()[1]}")
                    sales_data.append(get_sales_for_period(user, seller_id, week_start, week_end))
        else:  # daily
            days = (end_date - start_date).days + 1
            for i in range(days):
                day_start = (start_date + timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
                day_end = day_start + timedelta(hours=23, minutes=59, seconds=59)
                if day_end <= end_date:
                    labels.append(day_start.strftime('%d %b'))
                    sales_data.append(get_sales_for_period(user, seller_id, day_start, day_end))

        return jsonify({
            'status': 'success',
            'data': {
                'labels': labels[::-1],
                'sales': sales_data[::-1],
                'period': period
            }
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

def get_sales_for_period(user, seller_id, start_date, end_date):
    query = Q(
        created_at__gte=start_date,
        created_at__lte=end_date,
        status__in=['confirmed', 'processing', 'shipped', 'outOfDelivery', 'delivered']
    )
    
    if user.is_admin:
        if seller_id:
            seller = Seller.objects(id=seller_id).first()
            if seller:
                query &= Q(seller_id=seller)
    else:
        seller = Seller.objects(user_id=user).first()
        if seller:
            query &= Q(seller_id=seller)
            
    orders = Order.objects(query)
    return float(sum(order.total_amount for order in orders) or 0)

@sales_api.route(GET_SALES_SELLER, methods=['GET'])
def get_sellers():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return create_error_response({'error': 'User not logged in'}, 401)
        
        user = User.objects(id=user_id).first()
        if not user:
            return create_error_response({'error': 'User not found'}, 404)
            
        if not user.is_admin:
            return create_error_response({'error': 'Unauthorized access'}, 403)
            
        sellers = Seller.objects(is_approved='approved').only(
            'id', 'businessName', 'user_id'
        )
        
        seller_list = [{
            'id': str(seller.id),
            'name': seller.businessName,
            'user_id': str(seller.user_id.id)
        } for seller in sellers]
        
        return jsonify({
            'status': 'success',
            'data': seller_list
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@sales_api.route(TOP_PRODUCT_SALES_API, methods=['GET'])
def top_products():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return create_error_response({'error': 'User not logged in'}, 401)
        
        user = User.objects(id=user_id).first()
        if not user:
            return create_error_response({'error': 'User not found'}, 404)
        
        seller_id = request.args.get('seller_id')
        period = request.args.get('period', 'this_month')
        
        start_date, end_date = get_period_dates(period)
        
        query = Q(
            created_at__gte=start_date,
            created_at__lte=end_date,
            status__in=['confirmed', 'processing', 'shipped', 'outOfDelivery', 'delivered']
        )
        
        if user.is_admin:
            if seller_id:
                seller = Seller.objects(id=seller_id).first()
                if not seller:
                    return create_error_response({'error': 'Seller not found'}, 404)
                query &= Q(seller_id=seller)
        else:
            seller = Seller.objects(user_id=user).first()
            if not seller:
                return create_error_response({'error': 'Seller profile not found'}, 404)
            query &= Q(seller_id=seller)
            
        orders = Order.objects(query)
        product_sales = {}
        total_sales = 0
        
        for order in orders:
            for item in order.items:
                if hasattr(item, 'product_id') and item.product_id:
                    product = Products.objects(id=item.product_id.id).first()
                    if product:
                        product_id = str(product.id)
                        product_sales[product_id] = product_sales.get(product_id, {'name': product.name, 'amount': 0})
                        product_sales[product_id]['amount'] += float(item.quantity * item.price)
                        total_sales += float(item.quantity * item.price)
        
        top_products = [
            {
                'name': data['name'],
                'amount': data['amount'],
                'percentage': (data['amount'] / total_sales * 100) if total_sales > 0 else 0
            }
            for product_id, data in sorted(product_sales.items(), key=lambda x: x[1]['amount'], reverse=True)[:4]
        ]
        
        return jsonify({
            'status': 'success',
            'data': top_products
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@sales_api.route(RECENT_SALES_API, methods=['GET'])
def recent_sales():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return create_error_response({'error': 'User not logged in'}, 401)
        
        user = User.objects(id=user_id).first()
        if not user:
            return create_error_response({'error': 'User not found'}, 404)
        
        seller_id = request.args.get('seller_id')
        limit = int(request.args.get('limit', 5))
        page = int(request.args.get('page', 1))
        period = request.args.get('period', 'this_month')
        
        start_date, end_date = get_period_dates(period)
        
        query = Q(
            created_at__gte=start_date,
            created_at__lte=end_date,
            status__in=['confirmed', 'processing', 'shipped', 'outOfDelivery', 'delivered']
        )
        
        if user.is_admin:
            if seller_id:
                seller = Seller.objects(id=seller_id).first()
                if not seller:
                    return create_error_response({'error': 'Seller not found'}, 404)
                query &= Q(seller_id=seller)
        else:
            seller = Seller.objects(user_id=user).first()
            if not seller:
                return create_error_response({'error': 'Seller profile not found'}, 404)
            query &= Q(seller_id=seller)
            
        total_orders = Order.objects(query).count()
        orders = Order.objects(query).order_by('-created_at').skip((page - 1) * limit).limit(limit)

        recent_orders = []
        for order in orders:
            user = User.objects(id=order.user_id.id).first()
            
            customer_name = 'Unknown'
            if user:
                customer_name = f"{user.first_name or ''} {user.last_name or ''}".strip()
                if not customer_name:
                    customer_name = user.email.split('@')[0]
            
            product_names = []
            for item in order.items:
                if hasattr(item, 'product_id') and item.product_id:
                    product = Products.objects(id=item.product_id.id).first()
                    if product:
                        product_names.append(product.name)
            
            recent_orders.append({
                'order_id': order.order_number,
                'customer': customer_name,
                'product': ', '.join(product_names) if product_names else 'Unknown',
                'amount': float(order.total_amount),
                'date': order.created_at.strftime('%Y-%m-%d'),
                'status': order.status
            })

        return jsonify({
            'status': 'success',
            'data': {
                'orders': recent_orders,
                'total': total_orders,
                'page': page,
                'per_page': limit
            }
        }), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500