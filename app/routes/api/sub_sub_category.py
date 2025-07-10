from flask import Blueprint, request, session, jsonify, redirect, url_for
from app.models import SubSubCategory, SubCategory, Category, Products
from app.utils.image_upload import upload_image, validate_fields
from app.utils.utils import create_error_response
from bson import ObjectId
from constants import SUB_SUB_CATEGORY_ADD_API, GET_SUBSUBCATEGORIES_BY_CATEGORY_ID_API

sub_sub_category_bp = Blueprint('sub_sub_category_bp', __name__)

@sub_sub_category_bp.route(SUB_SUB_CATEGORY_ADD_API, methods=['POST'])
def add_sub_sub_category():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    name = request.form.get('name')
    description = request.form.get('description')
    image = request.files.get('sub-sub-category-image')
    category_id_str = request.form.get('category_id')
    subcategory_id_str = request.form.get('subcategory_id')

    required_fields = ['name', 'description', 'category_id', 'subcategory_id']
    is_valid, errors = validate_fields({
        'name': name,
        'description': description,
        'category_id': category_id_str,
        'subcategory_id': subcategory_id_str
    }, required_fields)

    if not is_valid:
        return create_error_response({"error": errors}, 400)

    if not ObjectId.is_valid(category_id_str):
        return create_error_response({'error': 'Invalid category ID format'}, 400)
    
    if not ObjectId.is_valid(subcategory_id_str):
        return create_error_response({'error': 'Invalid subcategory ID format'}, 400)

    try:
        category = Category.objects.get(id=ObjectId(category_id_str))
        subcategory = SubCategory.objects.get(id=ObjectId(subcategory_id_str))
        
        if str(subcategory.category.id) != category_id_str:
            return create_error_response({'error': 'Subcategory does not belong to the selected category'}, 400)

        image_filename, image_error = upload_image(image)
        if image_error:
            return create_error_response({'error': image_error}, 400)

        new_sub_sub_category = SubSubCategory(
            name=name,
            description=description,
            category_id=category,
            sub_category_id=subcategory,
            img_url=image_filename
        )
        new_sub_sub_category.save()

        return jsonify({
            'status': 'success',
            'message': 'SubSubCategory created successfully',
            'product_type': {
                'id': str(new_sub_sub_category.id),
                'name': new_sub_sub_category.name,
                'description': new_sub_sub_category.description,
                'category': new_sub_sub_category.category_id.name,
                'subcategory': new_sub_sub_category.sub_category_id.name,
                'img_url': url_for('serve_uploaded_files', filename=new_sub_sub_category.img_url, _external=True) if new_sub_sub_category.img_url else ''
            }
        })

    except (Category.DoesNotExist, SubCategory.DoesNotExist) as e:
        return create_error_response({'error': 'Category or SubCategory not found'}, 404)
    except Exception as e:
        return create_error_response({'error': str(e)}, 500)

@sub_sub_category_bp.route(GET_SUBSUBCATEGORIES_BY_CATEGORY_ID_API, methods=['GET'])
def get_sub_sub_category():
    subCategory_id = request.args.get('subCategoryId')
    if not subCategory_id:
        return jsonify({'success': False, 'message': 'categoryId is required'}), 400

    product_types = SubSubCategory.objects(sub_category_id=subCategory_id)
    return jsonify([
        {
            'id': str(pt.id),
            'name': pt.name,
            'img_url': url_for('serve_uploaded_files', filename=pt.img_url, _external=True) if pt.img_url else '',
            'description': pt.description,
            'categoryName': pt.category_id.name,
            'subcategoryName': pt.sub_category_id.name
        } for pt in product_types
    ])