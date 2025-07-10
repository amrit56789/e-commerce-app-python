
from flask import render_template, redirect, url_for, session, request, jsonify
from constants import SUB_SUB_CATEGORY_LIST_WEB_URL,  SUB_SUB_CATEGORY_WEB_URL, EDIT_SUB_SUB_CATEGORY_WEB_URL, UPDATE_SUB_SUB_CATEGORY_WEB_URL, DELETE_SUB_SUB_CATEGORY_WEB_URL
from . import admin_api
from app.models import Category, SubSubCategory, SubCategory, Products
from app.utils.utils import create_error_response
from bson import ObjectId
from flask import current_app
from app.utils.image_upload import get_local_ip, upload_image
from app.utils.validation import validate_required_fields

local_ip = get_local_ip()

@admin_api.route(SUB_SUB_CATEGORY_WEB_URL, methods=['POST', 'GET'])
def add_sub_sub_category_page():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))
    
    categories = Category.objects.all()
    
    return render_template(
        'admin/categorySubCategory/sub_sub_category/add_sub_sub_category.html',
        categories=categories,
    )

@admin_api.route(SUB_SUB_CATEGORY_LIST_WEB_URL, methods=['GET'])
def sub_sub_category_list_page():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))
    
    categories = Category.objects.all()
    return render_template('admin/categorySubCategory/sub_sub_category/sub_sub_category_list.html', categories=categories)

@admin_api.route(EDIT_SUB_SUB_CATEGORY_WEB_URL, methods=['GET'])
def edit_sub_sub_category_page(sub_sub_category_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))
    
    try:
        sub_sub_category = SubSubCategory.objects(id=ObjectId(sub_sub_category_id)).first()
        if not sub_sub_category:
            return create_error_response({'error': 'Subcategory not found'}, 404)
            
        categories = Category.objects.all()
        
        port = current_app.config.get('SERVER_PORT', 8080)
        base_url = f"http://{local_ip}:{port}/static/uploads/"

        if sub_sub_category.img_url:
            sub_sub_category.img_url = f"{base_url}/{sub_sub_category.img_url.lstrip('/')}"
        
        return render_template(
            'admin/categorySubCategory/sub_sub_category/edit_sub_sub_category.html', 
            sub_sub_category=sub_sub_category, 
            categories=categories,
            current_category_id=str(sub_sub_category.category_id.id)
        )
    except Exception as e:
        return create_error_response({'error': str(e)}, 500)

@admin_api.route(UPDATE_SUB_SUB_CATEGORY_WEB_URL, methods=['POST'])
def update_sub_sub_category(sub_sub_category_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    try:
        sub_sub_category = SubSubCategory.objects(id=ObjectId(sub_sub_category_id)).first()
        if not sub_sub_category:
            return create_error_response({'error': 'SubSubCategory not found'}, 404)

        name = request.form.get('name')
        description = request.form.get('description')
        sub_category_id = request.form.get('subcategory_id')
        image = request.files.get('sub-sub-category-image')

        required_fields = ['name', 'description', 'subcategory_id']
        is_valid, validation_errors = validate_required_fields({
            'name': name,
            'description': description,
            'subcategory_id': sub_category_id
        }, required_fields)

        if not is_valid:
            return create_error_response(validation_errors, 400)

        sub_category = SubCategory.objects(id=ObjectId(sub_category_id)).first()
        if not sub_category:
            return create_error_response({'error': 'Parent SubCategory not found'}, 404)

        image_filename = sub_sub_category.img_url 
        
        if image and image.filename != '':
            image_filename, image_error = upload_image(image)
            if image_error:
                return create_error_response({'error': image_error}, 400)

        sub_sub_category.update(
            name=name,
            description=description,
            sub_category_id=sub_category,
            img_url=image_filename
        )

        sub_sub_category.reload()

        return jsonify({
            'status': 'success',
            'message': 'SubSubCategory updated successfully',
            'sub_sub_category': {
                'id': str(sub_sub_category.id),
                'name': sub_sub_category.name,
                'description': sub_sub_category.description,
                'sub_category_id': str(sub_sub_category.sub_category_id.id),
                'img_url': sub_sub_category.img_url
            }
        })

    except Exception as e:
        return create_error_response({'error': str(e)}, 500)


@admin_api.route(DELETE_SUB_SUB_CATEGORY_WEB_URL, methods=['DELETE'])
def delete_sub_sub_category(sub_sub_category_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))
    
    try:
        sub_sub_category = SubSubCategory.objects(id=ObjectId(sub_sub_category_id)).first()
        if not sub_sub_category:
            return create_error_response({'error': 'Sub-sub category not found'}, 404)

        if Products.objects(subsubcategory_id=sub_sub_category).count() > 0:
            return create_error_response({'error': 'Cannot delete sub-sub-subcategory because it is linked to existing products.'}, 400)

        sub_sub_category.delete()
        
        return jsonify({
            'success': True,
            'message': 'Sub-sub category deleted successfully'
        }), 200
        
    except Exception as e:
        return create_error_response({'error': str(e)}, 500)