from flask import render_template, redirect, url_for, session, Blueprint, request, jsonify
from constants import API_SUBCATEGORY_LIST, API_ADD_SUBCATEGORY, API_GET_SUBCATEGORIES_BY_CATEGORY_ID
from app.models import SubCategory, Category, SubSubCategory
from app.utils.validation import validate_required_fields
from app.utils.image_upload import upload_image, validate_fields
from app.utils.utils import create_error_response
from bson import ObjectId

subcategory_bp = Blueprint('subcategory_bp', __name__)

@subcategory_bp.route(API_SUBCATEGORY_LIST)
def get_subcategory_list():
    category_id = request.args.get('categoryId', '').strip()
    query = SubCategory.objects

    if category_id:
        query = query(category=category_id)

    subcategories = query.all()

    subcategories_json = []
    for subcat in subcategories:
        sub_sub_category_count = SubSubCategory.objects(sub_category_id=subcat).count()        
        category_data = None
        if subcat.category:
            sub_category_count = SubCategory.objects(category=subcat.category).count()
            sub_sub_category_total = 0
            for sc in SubCategory.objects(category=subcat.category):
                sub_sub_category_total += SubSubCategory.objects(sub_category_id=sc).count()
            
            category_data = {
                "id": str(subcat.category.id),
                "name": subcat.category.name,
                "description": subcat.category.description,
                "img_url": url_for('serve_uploaded_files', filename=subcat.category.img_url, _external=True) if subcat.category.img_url else None,
                "sub_category_count": sub_category_count,
                "sub_sub_category_count": sub_sub_category_total
            }

        subcategories_json.append({
            "id": str(subcat.id),
            "name": subcat.name,
            "description": subcat.description,
            "img_url": url_for('serve_uploaded_files', filename=subcat.img_url, _external=True) if subcat.img_url else None,
            "created_at": subcat.created_at.isoformat(),
            "sub_sub_category_count": sub_sub_category_count,
            "category": category_data
        })

    return jsonify({"data": subcategories_json}), 200


@subcategory_bp.route(API_ADD_SUBCATEGORY, methods=['GET', 'POST'])
def add_new_subcategory():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    categories = Category.objects.all()

    if request.method == 'POST':
        name = request.form.get('name')
        description = request.form.get('description')
        image = request.files.get('image')
        category_id = request.form.get('category')

        required_fields = ['name', 'description', 'category']
        is_valid, validation_errors = validate_fields({
            'name': name,
            'description': description,
            'category': category_id
        }, required_fields)

        if not is_valid:
            return create_error_response({"error": validation_errors}, 400)

        category = Category.objects(id=ObjectId(category_id)).first()
        if not category:
            return create_error_response({'error': 'Invalid category ID'}, 400)

        image_filename, image_error = upload_image(image)
        if image_error:
            return create_error_response({'error': image_error}, 400)

        new_subcategory = SubCategory(
            name=name,
            description=description,
            category=category,
            img_url=image_filename
        )
        new_subcategory.save()

        return jsonify({
            'status': 'success',
            'message': 'SubCategory created successfully',
            'subcategory': {
                'name': new_subcategory.name,
                'description': new_subcategory.description,
                'category': new_subcategory.category.name,
                'img_url': new_subcategory.img_url
            }
        })

@subcategory_bp.route(API_GET_SUBCATEGORIES_BY_CATEGORY_ID, methods=['GET'])
def get_subcategories_by_category(category_id):
    subcategories = SubCategory.objects(category=category_id)
    response_data = []
    
    for subcategory in subcategories:
        category = subcategory.category
        sub_category_count = SubCategory.objects(category=category).count()
        
        sub_sub_category_total = 0
        for sc in SubCategory.objects(category=category):
            sub_sub_category_total += SubSubCategory.objects(sub_category_id=sc).count()
        
        sub_sub_categories = SubSubCategory.objects(sub_category_id=subcategory)
        sub_sub_category_list = [{
            "name": ssc.name,
            "description": ssc.description,
            "category_id": str(ssc.category_id.id) if ssc.category_id else None,
            "sub_category_id": str(ssc.sub_category_id.id) if ssc.sub_category_id else None,
            "id": str(ssc.id),
            "img_url": url_for('serve_uploaded_files', filename=ssc.img_url, _external=True) if ssc.img_url else None
        } for ssc in sub_sub_categories]
        
        subcategory_data = {
            "name": subcategory.name,
            "description": subcategory.description,
            "category_id": str(subcategory.category.id),
            "id": str(subcategory.id),
            "img_url": url_for('serve_uploaded_files', filename=subcategory.img_url, _external=True) if subcategory.img_url else None,
            "sub_sub_category_count": sub_sub_categories.count(),
            "category": {
                "name": category.name,
                "description": category.description,
                "id": str(category.id),
                "img_url": category.img_url,
                "sub_category_count": sub_category_count,
                "sub_sub_category_count": sub_sub_category_total
            },
            "sub_sub_categories": sub_sub_category_list
        }
        
        response_data.append(subcategory_data)
    
    return jsonify({"data": response_data}), 200

@subcategory_bp.route('/delete_subcategory/<string:subcategory_id>', methods=['POST'])
def delete_subcategory(subcategory_id):
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    try:
        subcategory = SubCategory.objects(id=ObjectId(subcategory_id)).first()
        if not subcategory:
            return create_error_response({'error': 'SubCategory not found'}, 404)

        subcategory.delete()

        return jsonify({
            'status': 'success',
            'message': 'SubCategory deleted successfully'
        })
    except Exception as e:
        return create_error_response({'error': str(e)}, 500)
