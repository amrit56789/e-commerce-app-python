from flask import render_template, session, redirect, url_for, request, jsonify
from . import admin_api
from app.models import User, PromoCode
from constants import ADD_PROMO_CODE_WEB_URL, PROMO_CODE_LIST_WEB_URL, DELETE_PROMO_CODE, EDIT_PROMO_CODE, UPDATE_PROMO_CODE_WEB_URL
from datetime import datetime
from bson import ObjectId,errors
from app.utils.utils import create_error_response
from app.utils.image_upload import validate_fields
from mongoengine.queryset.visitor import Q

@admin_api.route(ADD_PROMO_CODE_WEB_URL, methods=['GET', 'POST'])
def add_promo_code():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))
    
    if request.method == 'POST':
        return handle_promo_code_submission()
    
    return render_template('admin/promo_codes/add_promo_code.html')

def handle_promo_code_submission():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    try:
        data = request.form
        required_fields = ['code', 'discount_type', 'discount_value', 'start_date']
        
        is_valid, validation_errors = validate_fields(data, required_fields)
        if not is_valid:
            return create_error_response({"error": validation_errors}, 400)

        promo_code_value = data['code'].upper().strip()
        if PromoCode.objects(code=promo_code_value).first():
            return create_error_response({"error": f"Promo code '{promo_code_value}' already exists."}, 400)

        start_date_str = data['start_date']
        expiry_date_str = data.get('expiry_date')
        
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').replace(hour=0, minute=0, second=0)
            expiry_date = datetime.strptime(expiry_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59) if expiry_date_str else None
        except ValueError as e:
            return create_error_response({"error": f'Invalid date format: {str(e)}. Use YYYY-MM-DD format.'}, 400)

        current_date = datetime.utcnow()
        if start_date < current_date.replace(hour=0, minute=0, second=0, microsecond=0):
            return create_error_response({"error": "Start date cannot be in the past"}, 400)
        
        if expiry_date and expiry_date <= start_date:
            return create_error_response({"error": "End date must be after start date"}, 400)

        promo_data = {
            'code': promo_code_value,
            'description': data.get('description'),
            'discount_type': data['discount_type'],
            'discount_value': float(data['discount_value']),
            'min_order_amount': float(data.get('min_order_amount', 0)),
            'max_discount_amount': float(data.get('max_discount_amount', 0)),
            'start_date': start_date,
            'expiry_date': expiry_date,
            'max_uses': int(data['max_uses']) if data.get('max_uses') else None,
            'uses_per_user': int(data.get('uses_per_user', 1)),
            'only_first_order': data.get('only_first_order', 'false').lower() == 'true',
            'is_active': data.get('is_active', 'true').lower() == 'true',
            'created_by': session['user_id']
        }

        if promo_data['discount_type'] == 'percentage' and promo_data['discount_value'] > 100:
            return create_error_response({"error": 'Percentage discount cannot exceed 100%'}, 400)
        
        if promo_data['discount_value'] <= 0:
            return create_error_response({"error": "Discount value must be greater than 0"}, 400)

        promo_code = PromoCode(**promo_data)
        promo_code.save()

        return jsonify({
            'success': True,
            'message': 'Promo code created successfully',
            'promo_code_id': str(promo_code.id),
            'code': promo_code.code,
            'discount_value': float(promo_code.discount_value),
            'discount_type': promo_code.discount_type,
            'start_date': start_date_str,
            'expiry_date': expiry_date_str if expiry_date_str else None
        }), 201

    except ValueError as e:
        return create_error_response({"error" : f'Invalid data: {str(e)}'}, 400)
    except Exception as e:
        return create_error_response({"error" : f'Server error: {str(e)}'}, 500)

@admin_api.route(EDIT_PROMO_CODE, methods=['GET'])
def edit_promo_code_page(promo_code_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))
    try:
        promo_obj_id = ObjectId(promo_code_id)
        promo_code = PromoCode.objects.get(id=promo_obj_id)
    except (errors.InvalidId, PromoCode.DoesNotExist):
        return create_error_response({"error": "Promo code not found or invalid"}, 404)

    return render_template('admin/promo_codes/edit_promo_code.html', promo_code=promo_code)

@admin_api.route(UPDATE_PROMO_CODE_WEB_URL, methods=['PUT'])
def update_promo_code(promo_code_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    try:
        promo_code = PromoCode.objects(id=promo_code_id).first()
        if not promo_code:
            return create_error_response({"error": 'Promo code not found'}, 404)

        if str(promo_code.created_by.id) != session['user_id']:
            return create_error_response({"error": 'You can only update promo codes you created'}, 403)

        data = request.get_json() if request.is_json else request.form
        update_data = {}

        if 'code' in data:
            new_code = data['code'].upper().strip()
            if new_code != promo_code.code and PromoCode.objects(code=new_code).first():
                return create_error_response({"error": f"Promo code '{new_code}' already exists"}, 400)
            update_data['code'] = new_code

        if 'description' in data:
            update_data['description'] = data['description']

        if 'discount_type' in data:
            if data['discount_type'] not in ['percentage', 'fixed_amount']:
                return create_error_response({"error": 'Invalid discount type. Must be "percentage" or "fixed_amount"'}, 400)
            update_data['discount_type'] = data['discount_type']

        if 'discount_value' in data:
            try:
                discount_value = float(data['discount_value'])
                if discount_value <= 0:
                    return create_error_response({"error": 'Discount value must be greater than 0'}, 400)
                if 'discount_type' in update_data and update_data['discount_type'] == 'percentage' and discount_value > 100:
                    return create_error_response({"error": 'Percentage discount cannot exceed 100%'}, 400)
                if 'discount_type' not in update_data and promo_code.discount_type == 'percentage' and discount_value > 100:
                    return create_error_response({"error": 'Percentage discount cannot exceed 100%'}, 400)
                update_data['discount_value'] = discount_value
            except ValueError:
                return create_error_response({"error": 'Invalid discount value'}, 400)

        if 'min_order_amount' in data:
            try:
                update_data['min_order_amount'] = max(0, float(data['min_order_amount']))
            except ValueError:
                return create_error_response({"error": 'Invalid minimum order amount'}, 400)

        if 'max_discount_amount' in data:
            try:
                update_data['max_discount_amount'] = max(0, float(data['max_discount_amount']))
            except ValueError:
                return create_error_response({"error": 'Invalid maximum discount amount'}, 400)

        current_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if 'start_date' in data:
            try:
                new_start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').replace(hour=0, minute=0, second=0)
                
                if new_start_date < current_date and promo_code.is_active:
                    return create_error_response({"error": 'Cannot move start date to past for active promo codes'}, 400)
                    
                update_data['start_date'] = new_start_date
            except ValueError:
                return create_error_response({"error": 'Invalid start date format. Use YYYY-MM-DD'}, 400)

        if 'expiry_date' in data:
            if data['expiry_date']:
                try:
                    new_expiry_date = datetime.strptime(data['expiry_date'], '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                    
                    start_date = update_data.get('start_date', promo_code.start_date)
                    if new_expiry_date <= start_date:
                        return create_error_response({"error": 'End date must be after start date'}, 400)
                        
                    update_data['expiry_date'] = new_expiry_date
                except ValueError:
                    return create_error_response({"error": 'Invalid expiry date format. Use YYYY-MM-DD'}, 400)
            else:
                update_data['expiry_date'] = None

        if 'max_uses' in data:
            if data['max_uses']:
                try:
                    update_data['max_uses'] = max(1, int(data['max_uses']))
                except ValueError:
                    return create_error_response({"error": 'Invalid max uses value'}, 400)
            else:
                update_data['max_uses'] = None

        if 'uses_per_user' in data:
            try:
                update_data['uses_per_user'] = max(1, int(data['uses_per_user']))
            except ValueError:
                return create_error_response({"error": 'Invalid uses per user value'}, 400)

        if 'only_first_order' in data:
            update_data['only_first_order'] = str(data['only_first_order']).lower() == 'true'

        if 'is_active' in data:
            new_active_status = str(data['is_active']).lower() == 'true'
            
            start_date = update_data.get('start_date', promo_code.start_date)
            if new_active_status and start_date > current_date:
                return create_error_response({"error": "Cannot activate promo code with future start date"}, 400)
                
            update_data['is_active'] = new_active_status

        promo_code.update(**update_data)
        promo_code.reload()

        response_data = {
            'success': True,
            'message': 'Promo code updated successfully',
            'promo_code': {
                'id': str(promo_code.id),
                'code': promo_code.code,
                'discount_type': promo_code.discount_type,
                'discount_value': float(promo_code.discount_value),
                'start_date': promo_code.start_date.strftime('%Y-%m-%d'),
                'expiry_date': promo_code.expiry_date.strftime('%Y-%m-%d') if promo_code.expiry_date else None,
                'is_active': promo_code.is_active,
            }
        }

        return jsonify(response_data), 200

    except Exception as e:
        return create_error_response({"error": f'Server error: {str(e)}'}, 500)


@admin_api.route('/admin/promo-codes', methods=['GET'])
def promo_code_list():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    # Get query parameters
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    search = request.args.get('promoSearch', '')
    status = request.args.get('status', '')
    discount_type = request.args.get('discount_type', '')

    # Build query
    query = PromoCode.objects

    if search:
        query = query.filter(
            Q(code__icontains=search) |
            Q(description__icontains=search)
        )

    if status == 'active':
        query = query.filter(is_active=True)
    elif status == 'inactive':
        query = query.filter(is_active=False)

    if discount_type:
        query = query.filter(discount_type=discount_type)

    promo_codes = query.order_by('-created_at').paginate(page=page, per_page=limit)

    return render_template(
        'admin/promo_codes/promo_code_list.html',
        promos=promo_codes,
        search=search,
        status=status,
        discount_type=discount_type,
        limit=limit
    )


    

@admin_api.route('/api/admin/promo-codes', methods=['GET'])
def api_promo_code_list():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    # Get query parameters
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    search = request.args.get('promoSearch', '')
    status = request.args.get('status', '')
    discount_type = request.args.get('discount_type', '')

    # Build query
    query = PromoCode.objects

    if search:
        query = query.filter(
            Q(code__icontains=search) |
            Q(description__icontains=search)
        )

    if status == 'active':
        query = query.filter(is_active=True)
    elif status == 'inactive':
        query = query.filter(is_active=False)

    if discount_type:
        query = query.filter(discount_type=discount_type)

    promo_codes = query.order_by('-created_at').paginate(page=page, per_page=limit)

    # Serialize data
    promos_data = []
    for promo in promo_codes.items:
        promos_data.append({
            'id': str(promo.id),
            'code': promo.code,
            'description': promo.description,
            'discount_type': promo.discount_type,
            'discount_value': promo.discount_value,
            'max_discount_amount': promo.max_discount_amount,
            'start_date': promo.start_date.strftime('%Y-%m-%d') if promo.start_date else None,
            'expiry_date': promo.expiry_date.strftime('%Y-%m-%d') if promo.expiry_date else None,
            'max_uses': promo.max_uses,
            'is_active': promo.is_active,
            'created_at': promo.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })

    return jsonify({
        'promos': promos_data,
        'total': promo_codes.total,
        'pages': promo_codes.pages,
        'current_page': promo_codes.page,
        'has_next': promo_codes.has_next,
        'has_prev': promo_codes.has_prev,
        'next_num': promo_codes.next_num,
        'prev_num': promo_codes.prev_num
    })