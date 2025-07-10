from flask import render_template, redirect, url_for, session, request, jsonify, flash
from constants import CATEGORY_LIST_WEB_URL, ADD_CATEGORY_WEB_URL, GET_CATEGORIES_FILTER_API_URL, DELETE_CATEGORIES_API_WEB_URL, EDIT_CATEGORY_WEB_URL, SEARCH_CATEGORY_WEB_URL
from . import admin_api
from app.models import Category, SubCategory, SubSubCategory, Products
from app.utils.image_upload import get_local_ip, upload_image, validate_fields
from app.utils.utils import create_error_response
from bson import ObjectId
from flask import current_app

local_ip = get_local_ip()

def fetch_categories_data(search='', category_id='', page=1, per_page=10):
    query = Category.objects

    if search:
        query = query.filter(name__icontains=search)
    if category_id:
        query = query.filter(id=category_id)

    total_count = query.count()
    total_pages = (total_count + per_page - 1) // per_page 

    categories = query.order_by('-id').skip((page - 1) * per_page).limit(per_page)

    categories_data = [
        {
            'id': str(category.id),
            'name': category.name,
            'description': category.description,
            'img_url': category.img_url
        }
        for category in categories
    ]

    all_categories = [{'id': str(cat.id), 'name': cat.name} for cat in Category.objects.only('id', 'name')]

    return {
        'categories': categories_data,
        'all_categories': all_categories,
        'pagination': {
            'page': page,
            'pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if page < total_pages else None,
            'total': total_count,
            'per_page': per_page
        }
    }


def fetch_categories_data(search='', category_id='', page=1, per_page=10):
    query = Category.objects

    if search:
        query = query.filter(name__icontains=search)
    if category_id:
        query = query.filter(id=category_id)

    total_count = query.count()
    total_pages = (total_count + per_page - 1) // per_page 

    categories = query.order_by('-id').skip((page - 1) * per_page).limit(per_page)

    categories_data = [
        {
            'id': str(category.id),
            'name': category.name,
            'description': category.description,
            'img_url': url_for('serve_uploaded_files', filename=category.img_url, _external=True) if category.img_url else None
        }
        for category in categories
    ]

    all_categories = [{'id': str(cat.id), 'name': cat.name} for cat in Category.objects.only('id', 'name')]

    return {
        'categories': categories_data,
        'all_categories': all_categories,
        'pagination': {
            'page': page,
            'pages': total_pages,
            'has_prev': page > 1,
            'has_next': page < total_pages,
            'prev_num': page - 1 if page > 1 else None,
            'next_num': page + 1 if page < total_pages else None,
            'total': total_count,
            'per_page': per_page
        }
    }

@admin_api.route(CATEGORY_LIST_WEB_URL, methods=['GET'])
def get_category_list_page():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    search = request.args.get('search', '').strip()
    category_id = request.args.get('categoryId', '').strip()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('limit', 10))

    data = fetch_categories_data(search, category_id, page, per_page)

    # Add full image URL to each category
    categories_with_images = []
    for category in data['categories']:
        # Create a new dictionary or modify the existing one
        category_dict = dict(category)  # Make a copy
        category_dict['img_url_full'] = url_for(
            'serve_uploaded_files', 
            filename=category['img_url'],  # Access as dictionary key
            _external=True
        ) if category.get('img_url') else ''
        categories_with_images.append(category_dict)

    return render_template(
        "admin/categorySubCategory/category/category_list.html",
        categories=categories_with_images,
        all_categories=data['all_categories'],
        pagination=data['pagination'],
        limit=per_page,
        categories_api_url=GET_CATEGORIES_FILTER_API_URL,
        local_ip=local_ip
    )

@admin_api.route(GET_CATEGORIES_FILTER_API_URL, methods=['GET'])
def get_categories():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    search = request.args.get('search', '').strip()
    category_id = request.args.get('categoryId', '').strip()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('limit', 10))

    data = fetch_categories_data(search, category_id, page, per_page)

    return jsonify({
        'categories': data['categories'],
        'all_categories': data['all_categories'],
        'pagination': data['pagination']
    })

    data = fetch_categories_data(search, category_id, page, per_page)

    return jsonify({
        'categories': data['categories'],
        'all_categories': data['all_categories'],
        'pagination': data['pagination']
    })

@admin_api.route(ADD_CATEGORY_WEB_URL)
def add_new_category_page():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))
    return render_template('admin/categorySubCategory/category/add_new_category.html')

@admin_api.route(EDIT_CATEGORY_WEB_URL, methods=['GET'])
def edit_category_page(category_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))
    
    category = Category.objects(id=ObjectId(category_id)).first()
    
    if not category:
        return create_error_response({'error': 'Category not found'}, 404)
    
    port = current_app.config.get('SERVER_PORT', 8080)
    base_url = f"http://{local_ip}:{port}/static/uploads/"

    if category.img_url:
        category.img_url = f"{base_url}/{category.img_url.lstrip('/')}"
    
    return render_template('admin/categorySubCategory/category/edit_category.html', category=category)


@admin_api.route('/update_category/<category_id>', methods=['POST'])
def update_category(category_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    try:
        category = Category.objects(id=ObjectId(category_id)).first()
        if not category:
            return create_error_response({'error': 'Category not found'}, 404)

        name = request.form.get('name')
        description = request.form.get('description')
        image = request.files.get('image')

        required_fields = ['name', 'description']
        is_valid, validation_errors = validate_fields({
            'name': name,
            'description': description
        }, required_fields)

        if not is_valid:
            return create_error_response({"error": validation_errors}, 400)

        image_filename = category.img_url
        if image and image.filename != '':
            image_filename, image_error = upload_image(image)
            if image_error:
                return create_error_response({'error': image_error}, 400)

        category.update(
            name=name,
            description=description,
            img_url=image_filename
        )

        category.reload()

        return jsonify({
            'status': 'success',
            'message': 'Category updated successfully',
            'category': {
                'id': str(category.id),
                'name': category.name,
                'description': category.description,
                'img_url': category.img_url
            }
        })

    except Exception as e:
        return create_error_response({'error': str(e)}, 500)


@admin_api.route(DELETE_CATEGORIES_API_WEB_URL, methods=['POST'])
def delete_category(category_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    try:
        category = Category.objects(id=ObjectId(category_id)).first()
        if not category:
            return create_error_response({'error': 'Category not found'}, 404)

        products_count = Products.objects(category_id=category).count()
        if products_count > 0:
            return create_error_response({'error': 'Cannot delete category because it is linked to existing products.'}, 400)

        SubSubCategory.objects(category_id=category).delete()
        SubCategory.objects(category=category).delete()
        category.delete()

        return jsonify({
            'status': 'success',
            'message': 'Category and related subcategories deleted successfully'
        })

    except Exception as e:
        return create_error_response({'error': str(e)}, 500)


@admin_api.route(SEARCH_CATEGORY_WEB_URL, methods=['GET'])
def search_categories():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify([])

    categories = Category.objects(name__icontains=query).limit(10)
    return jsonify([{'id': str(cat.id), 'name': cat.name} for cat in categories])