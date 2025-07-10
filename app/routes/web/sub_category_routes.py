from flask import render_template, redirect, url_for, session, request, jsonify
from constants import SUBCATEGORY_LIST_WEB_URL, Add_SUBCATEGORY_LIST_WEB_URL, GET_SUBCATEGORIES_FILTER_API_URL, EDIT_SUB_CATEGORY_WEB_URL, UPDATE_SUB_CATEGORY_WEB_URL, DELETE_SUB_CATEGORY_WEB_URL, SEARCH_SUB_CATEGORY_WEB_URL
from app.utils.image_upload import get_local_ip, upload_image
from app.utils.validation import validate_required_fields
from . import admin_api
from app.models import Category, SubCategory, SubSubCategory, Products
from bson import ObjectId
from flask import current_app
from app.utils.utils import create_error_response

local_ip = get_local_ip()

def fetch_subcategories_data(category_id='', page=1, per_page=10):
    categories = [{'id': str(cat.id), 'name': cat.name} for cat in Category.objects.all()]

    query = SubCategory.objects()
    if category_id:
        query = query.filter(category=category_id)

    total_count = query.count()
    total_pages = (total_count + per_page - 1) // per_page

    subcategories = query.order_by('-id').skip((page - 1) * per_page).limit(per_page)

    subcategories_data = [
        {
            'id': str(subcategory.id),
            'name': subcategory.name,
            'description': subcategory.description,
            'img_url': url_for('serve_uploaded_files', filename=subcategory.img_url, _external=True) if subcategory.img_url else '',
            'category': {
                'id': str(subcategory.category.id),
                'name': subcategory.category.name
            }
        }
        for subcategory in subcategories
    ]

    return {
        'subcategories': subcategories_data,
        'categories': categories,
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

@admin_api.route(SUBCATEGORY_LIST_WEB_URL, methods=['GET'])
def get_subcategory_list_page():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    category_id = request.args.get('categoryId', '').strip()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('limit', 10))

    data = fetch_subcategories_data(category_id, page, per_page)

    return render_template(
        "admin/categorySubCategory/subcategory/subcategory_list.html",
        subcategories=data['subcategories'],
        categories=data['categories'],
        pagination=data['pagination'],
        limit=per_page,
        subcategories_api_url=GET_SUBCATEGORIES_FILTER_API_URL
    )
    
@admin_api.route(GET_SUBCATEGORIES_FILTER_API_URL, methods=['GET'])
def get_subcategories():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    category_id = request.args.get('categoryId', '').strip()
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('limit', 10))

    data = fetch_subcategories_data(category_id, page, per_page)

    return jsonify({
        'subcategories': data['subcategories'],
        'categories': data['categories'],
        'pagination': data['pagination']
    })

@admin_api.route(Add_SUBCATEGORY_LIST_WEB_URL, methods=['POST','GET'])
def add_subcategory_page():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))
    
    categories = Category.objects.all()
    return render_template('admin/categorySubCategory/subcategory/add_subcategory.html', categories=categories)

@admin_api.route(EDIT_SUB_CATEGORY_WEB_URL, methods=['GET'])
def edit_sub_category_page(sub_category_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))
    
    try:
        sub_category = SubCategory.objects(id=ObjectId(sub_category_id)).first()
        if not sub_category:
            return create_error_response({'error': 'Subcategory not found'}, 404)
            
        categories = Category.objects.all()
        
        port = current_app.config.get('SERVER_PORT', 8080)
        base_url = f"http://{local_ip}:{port}/static/uploads/"

        if sub_category.img_url:
            sub_category.img_url = f"{base_url}/{sub_category.img_url.lstrip('/')}"
        
        return render_template(
            'admin/categorySubCategory/subcategory/edit_sub_category.html', 
            sub_category=sub_category, 
            categories=categories,
            current_category_id=str(sub_category.category.id)
        )
    except Exception as e:
        return create_error_response({'error': str(e)}, 500)


@admin_api.route(UPDATE_SUB_CATEGORY_WEB_URL, methods=['POST'])
def update_sub_category(sub_category_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    try:
        sub_category = SubCategory.objects(id=ObjectId(sub_category_id)).first()
        if not sub_category:
            return create_error_response({'error': 'SubCategory not found'}, 404)

        name = request.form.get('name')
        description = request.form.get('description')
        category_id = request.form.get('category')
        image = request.files.get('image')

        required_fields = ['name', 'description', 'category']
        is_valid, validation_errors = validate_required_fields({
            'name': name,
            'description': description,
            'category': category_id
        }, required_fields)

        if not is_valid:
            return create_error_response(validation_errors, 400)

        category = Category.objects(id=ObjectId(category_id)).first()
        if not category:
            return create_error_response({'error': 'Parent Category not found'}, 404)

        image_filename = sub_category.img_url
        if image and image.filename != '':
            image_filename, image_error = upload_image(image)
            if image_error:
                return create_error_response({'error': image_error}, 400)

        sub_category.update(
            name=name,
            description=description,
            category=category,
            img_url=image_filename
        )

        sub_category.reload()

        return jsonify({
            'status': 'success',
            'message': 'SubCategory updated successfully',
            'sub_category': {
                'id': str(sub_category.id),
                'name': sub_category.name,
                'description': sub_category.description,
                'category_id': str(sub_category.category.id),
                'img_url': sub_category.img_url
            }
        })

    except Exception as e:
        return create_error_response({'error': str(e)}, 500)

@admin_api.route(DELETE_SUB_CATEGORY_WEB_URL, methods=['DELETE'])
def delete_sub_category(sub_category_id):
    if 'user_id' not in session:
         return redirect(url_for('admin_api.login_page'))

    try:
        sub_category = SubCategory.objects(id=ObjectId(sub_category_id)).first()
        if not sub_category:
            return create_error_response({'error': 'SubCategory not found'}, 404)

        products_count = Products.objects(subcategory_id=sub_category).count()
        if products_count > 0:
            return create_error_response({'error': 'Cannot delete sub-subcategory because it is linked to existing products.'}, 400)

        SubSubCategory.objects(sub_category_id=ObjectId(sub_category_id)).delete()
        sub_category.delete()

        return jsonify({
            'status': 'success',
            'message': 'SubCategory and all related SubSubCategories deleted successfully',
            'deleted_sub_category_id': sub_category_id
        })

    except Exception as e:
        return create_error_response({'error': str(e)}, 500)

@admin_api.route(SEARCH_SUB_CATEGORY_WEB_URL, methods=["GET"])
def search_subcategories():
    category_id = request.args.get('category_id')
    query = request.args.get('q', '').strip()

    if not category_id:
        return jsonify({'success': False, 'message': 'Category ID is required'}), 400

    subcategories = SubCategory.objects(
        category=category_id,
        name__icontains=query
    ).limit(10)

    return jsonify({
        'success': True,
        'data': [{'id': str(sub.id), 'name': sub.name} for sub in subcategories]
    })
