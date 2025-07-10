from flask import Blueprint, request, jsonify, session
from app.models import ProductBrands
from constants import GET_BRANDS_LIST_API, ADD_BRAND_API, UPDATE_BRAND_API
from app.utils.utils import create_error_response
from app.utils.image_upload import upload_image, get_local_ip
from app.utils.validation import validate_required_fields

from datetime import datetime

brand_bp = Blueprint('brand_bp', __name__)
local_ip = get_local_ip()

@brand_bp.route(GET_BRANDS_LIST_API, methods=['GET'])
def fetch_brands():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    get_all = request.args.get('all', 'false').lower() == 'true'

    if get_all:
        try:
            brands = ProductBrands.objects()
            data = [
                {
                    "id": str(brand.id),
                    "name": brand.name,
                    "logo_path": brand.logo_path
                }
                for brand in brands
            ]
            return jsonify({
                "success": True,
                "message": "Brands fetched successfully",
                "data": data
            }), 200
        except Exception as e:
            return jsonify({
                "success": False,
                "message": "Something went wrong while fetching brands",
                "error": str(e)
            }), 500

    search_query = request.args.get('search', '')
    limit = int(request.args.get('limit', 10))
    page = int(request.args.get('page', 1))
    if search_query:
        brands = ProductBrands.objects(name__icontains=search_query)
    else:
        brands = ProductBrands.objects.all()

    brands_paginated = brands.paginate(page=page, per_page=limit)

    brands_data = [
        {
            'id': str(brand.id),
            'name': brand.name,
            'description': brand.description,
            'logo_path': brand.logo_path or ''
        } for brand in brands_paginated.items
    ]

    return jsonify({
        'data': brands_data,
        'pagination': {
            'page': brands_paginated.page,
            'pages': brands_paginated.pages,
            'has_prev': brands_paginated.has_prev,
            'has_next': brands_paginated.has_next,
            'prev_num': brands_paginated.prev_num,
            'next_num': brands_paginated.next_num
        },
        'success': True,
        'search': search_query,
        'limit': limit
    })

@brand_bp.route(ADD_BRAND_API, methods=['POST'])
def add_new_brand():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    name = request.form.get('name')
    description = request.form.get('description')
    logo = request.files.get('logo')

    is_valid, validation_errors = validate_required_fields({'name': name, 'description': description}, ['name', 'description'])
    if not is_valid:
        return create_error_response({"error": validation_errors}, 400)

    if not name:
        return create_error_response({"error": 'Brand name is required'}, 400)

    if not description:
        return create_error_response({"error": 'Description is required'}, 400)

    logo_path, logo_error = upload_image(logo)
    if logo_error:
        return create_error_response({"error": logo_error}, 400)

    existing = ProductBrands.objects(name__iexact=name).first()
    if existing:
        return create_error_response({"error": 'Brand already exists'}, 409)

    brand = ProductBrands(name=name, description=description, logo_path=logo_path)
    brand.save()

    return jsonify({"message": "Brand created successfully", "id": str(brand.id), "logo_path": brand.logo_path, "description": brand.description}), 200


@brand_bp.route(UPDATE_BRAND_API, methods=['POST'])
def update_brand():
    brand_id = request.args.get('brandId')
    if not brand_id:
        return create_error_response({"error": 'Brand ID is required'}, 400)

    name = request.form.get('name')
    description = request.form.get('description')
    logo = request.files.get('logo')

    is_valid, validation_errors = validate_required_fields({'name': name, 'description': description}, ['name', 'description'])
    if not is_valid:
        return create_error_response({"error": validation_errors}, 400)

    brand = ProductBrands.objects(id=brand_id).first()
    if not brand:
        return create_error_response({"error": 'Brand not found'}, 404)

    if logo:
        logo_path, logo_error = upload_image(logo)
        if logo_error:
            return create_error_response({"error": logo_error}, 400)
        brand.logo_path = logo_path

    existing = ProductBrands.objects(name__iexact=name).first()
    if existing and str(existing.id) != brand_id:
        return create_error_response({"error": 'Another brand with the same name already exists'}, 409)

    brand.name = name
    brand.description = description
    brand.updated_at = datetime.utcnow()
    brand.save()

    return jsonify({"message": "Brand updated successfully", "id": str(brand.id), "logo_path": brand.logo_path}), 200
