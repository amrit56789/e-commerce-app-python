from flask import render_template, redirect, session, url_for, request, jsonify
from . import admin_api
from app.models import Seller, Identification
from mongoengine.queryset.visitor import Q
from constants import ADD_SELLER_WEB_URL, GET_SELLER_LIST_WEB_URL, GET_SELLERS_API_URL, INDIAN_STATES, EDIT_SELLERS_PAGE_WEB_URL, APPROVAL_STATUSES
from app.models import User
from app.models import Address
from app.utils.image_upload import get_local_ip
from flask import current_app

@admin_api.route(ADD_SELLER_WEB_URL)
def add_new_seller():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))
    return render_template("admin/seller/add_new_seller.html", INDIAN_STATES=INDIAN_STATES)

def get_value(value):
    return value if value else '---'

def fetch_sellers_data(search_query='', approval_status='', page=1, per_page=10, sort_by='', sort_order='asc'):
    query = Seller.objects()

    if approval_status:
        query = query.filter(is_approved=approval_status)

    if search_query:
        user_query = Q(email__icontains=search_query) | Q(phone_number__icontains=search_query)
        matching_users = User.objects(user_query)
        matching_user_ids = [user.id for user in matching_users]

        address_query = Q(city__icontains=search_query) | Q(line1__icontains=search_query)
        matching_addresses = Address.objects(address_query)
        matching_address_ids = [address.id for address in matching_addresses]

        search_regex = Q(businessName__icontains=search_query)
        if matching_user_ids:
            search_regex |= Q(user_id__in=matching_user_ids)
        if matching_address_ids:
            search_regex |= Q(address__in=matching_address_ids)

        query = query.filter(search_regex)

    # Handle sorting
    if sort_by:
        sort_field = sort_by
        sort_prefix = '-' if sort_order == 'desc' else ''
        
        # Handle nested fields
        if sort_by.startswith('user.'):
            field_name = sort_by.split('.')[1]
            # For related fields, we need to use a different approach
            if field_name in ['first_name', 'last_name', 'email', 'phone_number']:
                # This requires aggregation pipeline for proper sorting
                # Here's a simplified approach (might not be efficient for large datasets)
                sellers = list(query)
                
                # Sort in memory
                reverse_sort = sort_order == 'desc'
                
                if field_name == 'first_name':
                    sellers.sort(key=lambda x: x.user_id.first_name if x.user_id else '', reverse=reverse_sort)
                elif field_name == 'last_name':
                    sellers.sort(key=lambda x: x.user_id.last_name if x.user_id else '', reverse=reverse_sort)
                elif field_name == 'email':
                    sellers.sort(key=lambda x: x.user_id.email if x.user_id else '', reverse=reverse_sort)
                elif field_name == 'phone_number':
                    sellers.sort(key=lambda x: x.user_id.phone_number if x.user_id else '', reverse=reverse_sort)
                
                total_count = len(sellers)
                total_pages = (total_count + per_page - 1) // per_page
                start_idx = (page - 1) * per_page
                paginated_sellers = sellers[start_idx:start_idx + per_page]
                
                # Convert to the enriched format
                enriched_sellers = []
                for idx, seller in enumerate(paginated_sellers, start=start_idx + 1):
                    enriched_sellers.append(enrich_seller_data(seller, idx))
                
                return {
                    'data': enriched_sellers,
                    'meta': {
                        'pagination': {
                            'page': page,
                            'per_page': per_page,
                            'total_count': total_count,
                            'total_pages': total_pages,
                            'has_prev': page > 1,
                            'has_next': page < total_pages,
                            'prev_page': page - 1 if page > 1 else None,
                            'next_page': page + 1 if page < total_pages else None
                        },
                        'filters': {
                            'search_query': search_query,
                            'approval_status': approval_status,
                            'sort_by': sort_by,
                            'sort_order': sort_order
                        }
                    }
                }
        else:
            # Handle direct fields
            if sort_by in ['businessName', 'businessType', 'businessEmail', 'is_approved', 'created_at']:
                query = query.order_by(f'{sort_prefix}{sort_by}')

    total_count = query.count()
    total_pages = (total_count + per_page - 1) // per_page

    start_idx = (page - 1) * per_page
    paginated_sellers = query.skip(start_idx).limit(per_page)

    enriched_sellers = []
    for idx, seller in enumerate(paginated_sellers, start=start_idx + 1):
        enriched_sellers.append(enrich_seller_data(seller, idx))

    return {
        'data': enriched_sellers,
        'meta': {
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total_count': total_count,
                'total_pages': total_pages,
                'has_prev': page > 1,
                'has_next': page < total_pages,
                'prev_page': page - 1 if page > 1 else None,
                'next_page': page + 1 if page < total_pages else None
            },
            'filters': {
                'search_query': search_query,
                'approval_status': approval_status,
                'sort_by': sort_by,
                'sort_order': sort_order
            }
        }
    }


def enrich_seller_data(seller, index):
    user = seller.user_id
    address = seller.address
    identification = Identification.objects(user_id=user).first()

    address_data = {
        "line1": get_value(address.line1 if address else None),
        "city": get_value(address.city if address else None),
        "state": get_value(address.state if address else None),
        "postal_code": get_value(address.postal_code if address else None),
        "country": get_value(address.country if address else None)
    }

    return {
        "index": index,
        "seller": {
            "id": str(seller.id),
            "businessName": get_value(seller.businessName),
            "businessType": get_value(seller.businessType),
            "businessEmail": get_value(seller.businessEmail),
            "businessMobile": get_value(seller.businessMobile),
            "gst_number": get_value(seller.gst_number),
            "is_approved": get_value(seller.is_approved),
            "created_at": seller.created_at.isoformat() if seller.created_at else '---'
        },
        "user": {
            "id": str(user.id) if user else '---',
            "email": get_value(user.email if user else None),
            "first_name": get_value(user.first_name if user else None),
            "last_name": get_value(user.last_name if user else None),
            "phone_number": get_value(user.phone_number if user else None)
        },
        "address": address_data,
        "identification": {
            "pan_number": get_value(identification.pan_number if identification else None),
            "address_proof_id_type": get_value(identification.address_proof_id_type if identification else None)
        }
    }

@admin_api.route(GET_SELLER_LIST_WEB_URL)
def get_seller_list():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    search_query = request.args.get('search', '').strip()
    approval_status = request.args.get('approval_status', '').strip()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('limit', 10))
    sort_by = request.args.get('sort_by', '')
    sort_order = request.args.get('sort_order', 'asc')

    data = fetch_sellers_data(
        search_query=search_query,
        approval_status=approval_status,
        page=page,
        per_page=per_page,
        sort_by=sort_by,
        sort_order=sort_order
    )

    return render_template(
        "admin/seller/seller_list.html",
        sellers=data['data'],
        filters=data['meta']['filters'],
        pagination=data['meta']['pagination'],
        limit=per_page,
        sellers_api_url=GET_SELLERS_API_URL
    )

@admin_api.route(GET_SELLERS_API_URL, methods=['GET'])
def get_sellers():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    search_query = request.args.get('search', '').strip()
    approval_status = request.args.get('approval_status', '').strip()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('limit', 10))

    data = fetch_sellers_data(search_query, approval_status, page, per_page)

    return jsonify({
        'data': data['data'],
        'meta': data['meta']
    })

@admin_api.route(EDIT_SELLERS_PAGE_WEB_URL, methods=['GET'])
def edit_seller_page(seller_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    try:
        local_ip = get_local_ip()
        port = current_app.config.get('SERVER_PORT', 8080)
        seller = Seller.objects.get(id=seller_id)
        user = seller.user_id
        
        all_addresses = Address.objects(user_id=user.id)
        
        personal_address = all_addresses.filter(is_primary=True).first()
        
        business_address = (all_addresses.filter(is_business_address=True).first() or 
                          seller.businessAddress)
        
        if not personal_address:
            personal_address = seller.address
        
        identification = Identification.objects(user_id=user.id).first()

        def format_address(address):
            if not address:
                return None
            return {
                "id": str(address.id),
                "line1": address.line1,
                "line2": address.line2,
                "city": address.city,
                "state": address.state,
                "postal_code": address.postal_code,
                "country": address.country,
                "contact_name": address.contact_name,
                "contact_number": address.contact_number,
                "type": address.type,
                "is_primary": address.is_primary,
                "is_business_address": address.is_business_address
            }

        response_data = {
            "seller": {
                "id": str(seller.id),
                "businessName": seller.businessName,
                "businessType": seller.businessType,
                "businessEmail": seller.businessEmail,
                "businessMobile": seller.businessMobile,
                "gst_number": seller.gst_number,
                "is_approved": seller.is_approved,
                "created_at": seller.created_at.isoformat() if seller.created_at else None,
                "approved_by": str(seller.approved_by.id) if seller.approved_by else None,
                "has_business_address": bool(business_address)
            },
            "user": {
                "id": str(user.id),
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone_number": user.phone_number,
                "gender": user.gender,
                "profile_pic": user.profile_pic,
                "is_email_verified": user.is_email_verified
            },
            "address": format_address(personal_address),
            "business_address": format_address(business_address),
            "identification": {
                "id": str(identification.id),
                "address_proof_id_type": identification.address_proof_id_type,
                'address_proof_front': f"http://{local_ip}:{port}/static/uploads/{identification.address_proof_front}" if identification.address_proof_front else '',
                "address_proof_back": identification.address_proof_back,
                "pan_number": identification.pan_number,
                'pan_card_front': f"http://{local_ip}:{port}/static/uploads/{identification.pan_card_front}" if identification.pan_card_front else '',
                "id_number": identification.id_number
            } if identification else None
        }
        
        return render_template("admin/seller/edit_seller.html", 
                            seller_data=response_data, 
                            INDIAN_STATES=INDIAN_STATES, 
                            local_ip=local_ip, 
                            APPROVAL_STATUSES=APPROVAL_STATUSES)
    
    except Seller.DoesNotExist:
        return redirect(url_for('admin_api.get_seller_list'))
    except Exception as e:
        print(f"Error fetching seller data: {str(e)}")
        return redirect(url_for('admin_api.get_seller_list'))