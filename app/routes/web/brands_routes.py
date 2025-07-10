from flask import render_template, session, redirect, url_for, request, jsonify
from . import admin_api
from app.models import ProductBrands, Products, ProductVariant, ProductVariantImage
from constants import GET_BRANDS_WEB_URL, ADD_BRAND_WEB_URL, UPDATE_BRAND_WEB_URL, DELETE_BRAND_API
from app.utils.image_upload import get_local_ip
from flask import current_app

local_ip = get_local_ip()

@admin_api.route(GET_BRANDS_WEB_URL)
def get_brand_list_page():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))
    
    search_query = request.args.get('search', '')
    limit = int(request.args.get('limit', 10))
    page = int(request.args.get('page', 1))

    if search_query:
        brands_query = ProductBrands.objects(name__icontains=search_query)
    else:
        brands_query = ProductBrands.objects.all()

    total_count = brands_query.count()
    
    total_pages = max(1, (total_count + limit - 1) // limit)
    
    page = max(1, min(page, total_pages))
    
    brands_paginated = brands_query.paginate(page=page, per_page=limit)

    return render_template('admin/productBrands/brands_list.html', 
                         brands=brands_paginated.items, 
                         pagination=brands_paginated, 
                         search=search_query, 
                         limit=limit,
                         local_ip=local_ip)


@admin_api.route(ADD_BRAND_WEB_URL)
def add_new_brand_page():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))
    return render_template('admin/productBrands/add_brands.html')


@admin_api.route(UPDATE_BRAND_WEB_URL, methods=['GET', 'POST'])
def update_brand_page(brand_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    brand = ProductBrands.objects(id=brand_id).first()
    if not brand:
        return redirect(url_for('admin_api.get_brand_list_page'))

    port = current_app.config.get('SERVER_PORT', 8080)
    base_url = f"http://{local_ip}:{port}/static/uploads/"

    if brand.logo_path:
        brand.logo_path = f"{base_url}/{brand.logo_path.lstrip('/')}"

    return render_template('admin/productBrands/edit_brands.html', brand=brand)

@admin_api.route(DELETE_BRAND_API, methods=['POST'])
def delete_brand(brand_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    page = int(request.form.get('page', 1))
    search_query = request.form.get('search', '')
    limit = int(request.form.get('limit', 10))

    brand = ProductBrands.objects(id=brand_id).first()
    if brand:
        products = Products.objects(brand_id=brand_id)
        
        for product in products:
            for variant in product.variants:
                ProductVariantImage.objects(variant_id=variant.id).delete()
            
            ProductVariant.objects(product_id=product.id).delete()
        
        products.delete()
        
        brand.delete()
        
        remaining_count = ProductBrands.objects(name__icontains=search_query).count()
        total_pages = max(1, (remaining_count + limit - 1) // limit)
        
        if page > total_pages:
            page = total_pages
        
        return jsonify({
            'success': True,
            'page': page,
            'search': search_query,
            'limit': limit
        })
    else:
        return jsonify({'success': False, 'message': 'Brand not found'}), 404