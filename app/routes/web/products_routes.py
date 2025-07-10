import json
import random
import string

from datetime import datetime
from bson import ObjectId
from flask import render_template, redirect, url_for, session, request, jsonify
from constants import ( ADD_PRODUCT_PAGE_WEB_URL, ADD_NEW_PRODUCT_WEB_URL, GET_PRODUCT_LIST_WEB_URL, GET_PRODUCT_DETAILS_WEB_URL, GET_PROUDCT_EDIT_PAGE_BY_ID_WEB_URL, EDIT_PRODUCT_WEB_URL, ALLOWED_SIZES, ALLOWED_GENDERS, REMOVE_PRODUCT_IMAGE_WEB_URL)
from app.models import ( Category, SubCategory, SubSubCategory, Products, ProductVariant, ProductVariantImage, User, Seller, ProductBrands)
from app.utils.image_upload import upload_image, get_local_ip
from app.utils.utils import create_error_response
from app.utils.validation import validate_required_fields
from . import admin_api
from app.utils.image_upload import get_local_ip

local_ip = get_local_ip()

@admin_api.route(ADD_PRODUCT_PAGE_WEB_URL, methods=['GET'])
def get_products_page():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    categories = Category.objects.all()

    return render_template(
        'admin/products/add_new_product.html',
        categories=categories,
    )

@admin_api.route(ADD_NEW_PRODUCT_WEB_URL, methods=['POST'])
def add_new_product():
    try:
        if 'user_id' not in session:
            return redirect(url_for('admin_api.login_page'))
        user_id = session.get('user_id')
        try:
            user_object_id = ObjectId(user_id)
        except Exception:
            return create_error_response({'error': 'Invalid user ID'}, 400)

        user = User.objects(id=user_object_id).first()
        if not user:
            return create_error_response({'error': 'User not found'}, 404)

        seller = Seller.objects(user_id=user_object_id).first()
        if not seller:
            return create_error_response({'error': 'Seller profile not found'}, 400)

        required_fields = ['name', 'price', 'category_id', 'subcategory_id', 'subsubcategory_id', 'details', 'description', 'stock_quantity']
        form_data = request.form.to_dict(flat=False)
        data = {k: v[0] if len(v) == 1 else v for k, v in form_data.items()}

        is_valid, validation_errors = validate_required_fields(data, required_fields)
        if not is_valid:
            return create_error_response({'error': validation_errors}, 400)

        category = Category.objects(id=data['category_id']).first()
        subcategory = SubCategory.objects(id=data['subcategory_id']).first()
        subsubcategory = SubSubCategory.objects(id=data['subsubcategory_id']).first()

        if not category or not subcategory or not subsubcategory:
            return create_error_response({
                'category_id': 'Invalid category ID',
                'subcategory_id': 'Invalid subcategory ID',
                'subsubcategory_id': 'Invalid subsubcategory ID'
            }, 400)

        price = float(data['price'])
        discount_price = float(data.get('discount_price', 0))

        final_price = price
        if discount_price > 0:
            final_price = price - (price * discount_price / 100)
            
        material = data.get('material')
        description = data.get('description')
        gender = data.get('gender') if data.get('gender') in ALLOWED_GENDERS else None
        stock_quantity = data.get('stock_quantity')

        # Generate random SKU
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        sku_number = f"SKU-{timestamp}-{random_chars}"

        brand = None
        brand_value = data.get('brand_id')
        other_brand_name = data.get('other_brand')

        if brand_value and brand_value != 'other':
            brand = ProductBrands.objects(id=brand_value).first()
            if not brand:
                return create_error_response({'brand': 'Invalid brand ID'}, 400)
        elif brand_value == 'other' and other_brand_name:
            brand = ProductBrands.objects(name__iexact=other_brand_name.strip()).first()
            if not brand:
                brand = ProductBrands(
                    name=other_brand_name.strip(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                brand.save()

        try:
            variations_list = json.loads(data.get('variations', '[]'))
        except json.JSONDecodeError:
            return create_error_response({'error': 'Invalid variations format'}, 400)

        variants = []
        for var in variations_list:
            try:
                size = var['size']
                color = var['color']
                stock_quantity = int(var.get('stock_quantity', 0))
                color_hexa_code = var.get('color_hexa_code')
                variant = ProductVariant(
                    size=size,
                    color=color,
                    color_hexa_code=color_hexa_code,
                    stock_quantity=stock_quantity,
                    product_id=None
                )
                variants.append(variant)
            except (KeyError, ValueError) as e:
                return create_error_response({'variations': f'Invalid variation data: {str(e)}'}, 400)

        # Dictionary to store images by color (color: [image_urls])
        color_images_map = {}

        # Process all images, grouping by color (ignore size for upload)
        for file_key in request.files:
            if file_key.startswith('images[') and ']' in file_key:
                try:
                    parts = file_key.split('[')
                    color = parts[1].split(']')[0]
                    
                    # Only process if we haven't seen this color before
                    if color not in color_images_map:
                        color_images_map[color] = []
                        # Upload all files for this color
                        for file in request.files.getlist(file_key):
                            image_path, error = upload_image(file)
                            if error:
                                return create_error_response({'error': error}, 400)
                            color_images_map[color].append(image_path)
                except Exception as e:
                    return create_error_response({'error': f'Invalid image key format: {str(e)}'}, 400)

        saved_variants = []
        # Dictionary to track all created images (image_url: image_object)
        variant_images_map = {}

        # First save all variants
        for variant in variants:
            variant.save()
            saved_variants.append(variant)

        # Then create images and associate with variants
        for variant in saved_variants:
            color = variant.color
            if color in color_images_map:
                for image_url in color_images_map[color]:
                    # If image not already created, make new record
                    if image_url not in variant_images_map:
                        image = ProductVariantImage(
                            variant_id=variant.id,
                            image_url=image_url,
                            alt_text=f"{data['name']} - {color} - {variant.size}",
                        )
                        image.save()
                        variant_images_map[image_url] = image
                    # Associate image with variant (whether new or existing)
                    variant.images.append(variant_images_map[image_url])
                variant.save()

        # Create the main product
        product = Products(
            seller_id=seller.id,
            name=data['name'],
            description=data.get('description'),
            details=data.get('details'),
            category_id=category,
            subcategory_id=subcategory,
            subsubcategory_id=subsubcategory,
            brand_id=brand,
            sku_number=sku_number,
            price=price,
            stock_quantity=stock_quantity,
            discount_price=discount_price,
            final_price=final_price,
            material=material,
            gender=gender,
            status='active',
            variants=saved_variants,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        product.save()

        # Update product_id reference in all images
        for image_obj in variant_images_map.values():
            image_obj.product_id = product.id
            image_obj.save()

        # Update product_id reference in all variants
        for variant in saved_variants:
            variant.product_id = product
            variant.save()

        return jsonify({
            "message": "Product created successfully",
            "id": str(product.id),
            "product": {
                "name": product.name,
                "price": float(product.price),
                "discount_price": float(product.discount_price) if product.discount_price else None,
                "final_price": float(product.final_price),
                "sku_number": product.sku_number
            }
        }), 201

    except Exception as error:
        return create_error_response({'error': str(error)}, 500)


def get_filtered_products(seller_id=None):
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('limit', 10, type=int)
    category = request.args.get('category')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)

    query = {}

    if seller_id is not None:
        query['seller_id'] = seller_id

    if category:
        category_obj = Category.objects(name=category).first()
        if category_obj:
            query['category_id'] = category_obj.id
        else:
            return None, Category.objects.all(), f"Category '{category}' not found"

    if min_price is not None:
        query['final_price__gte'] = min_price

    if max_price is not None:
        query['final_price__lte'] = max_price

    try:
        products = Products.objects(**query).order_by('-created_at').paginate(page=page, per_page=per_page)
        return products, Category.objects.all(), None
    except Exception as e:
        return None, Category.objects.all(), str(e)

@admin_api.route(GET_PRODUCT_LIST_WEB_URL, methods=['GET'])
def get_product_lists():
    if 'user_id' not in session:
        return redirect(url_for('admin_api.login_page'))

    current_user = User.objects(id=session['user_id']).first()
    if not current_user:
        return redirect(url_for('admin_api.login_page'))

    if current_user.is_admin:
        products, categories, error = get_filtered_products()
    else:
        seller = Seller.objects(user_id=current_user).first()
        if not seller:
            error_message = 'Seller profile not found. Please contact administrator.'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return create_error_response({'error': error_message}, 400)
            return render_template(
                'admin/products/product_list.html',
                products=None,
                categories=Category.objects.all(),
                local_ip=local_ip,
                error=error_message,
                is_admin=False
            )
        products, categories, error = get_filtered_products(seller_id=seller.id)

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if error:
            return create_error_response({'error': error}, 400)
        if not products or products.total == 0:
            return jsonify({'message': 'No products found'}), 200

        product_data = []
        for product in products.items:
            image_url = None
            if product.variants and product.variants[0].images:
                image_url = f"http://{local_ip}:8080/static/uploads/{product.variants[0].images[0].image_url}"

            product_data.append({
                'name': product.name,
                'price': float(product.price) if product.price else 0,
                'discount_price': float(product.discount_price) if product.discount_price else 0,
                'final_price': float(product.final_price) if product.final_price else 0,
                'sku_number': product.sku_number or '-',
                'image_url': image_url,
                'edit_url': url_for('admin_api.edit_product_page', product_id=str(product.id)),
                'details_url': url_for('admin_api.product_details', product_id=str(product.id))
            })

        return jsonify({
            'products': product_data,
            'page': products.page,
            'pages': products.pages,
            'has_prev': products.has_prev,
            'has_next': products.has_next,
            'prev_num': products.prev_num,
            'next_num': products.next_num
        })

    # Handle AJAX request
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if error:
            return jsonify({'error': error}), 400

        product_data = []
        for product in products.items:
            image_url = None
            if product.variants and product.variants[0].images:
                image_url = f"http://{local_ip}:8080/static/uploads/{product.variants[0].images[0].image_url}"

            product_data.append({
                'name': product.name,
                'price': product.price,
                'discount_price': product.discount_price,
                'final_price': product.final_price,
                'sku_number': product.sku_number or '-',
                'image_url': image_url,
                'edit_url': url_for('admin_api.edit_product_page', product_id=product.id),
                'details_url': url_for('admin_api.product_details', product_id=product.id)
            })

        return jsonify({
            'products': product_data,
            'page': products.page,
            'pages': products.pages,
            'has_prev': products.has_prev,
            'has_next': products.has_next,
            'prev_num': products.prev_num,
            'next_num': products.next_num
        })

    return render_template(
        'admin/products/product_list.html',
        products=products,
        categories=categories,
        local_ip=local_ip,
        error=error,
        is_admin=current_user.is_admin
    )


@admin_api.route(GET_PRODUCT_DETAILS_WEB_URL, methods=['GET'])
def product_details(product_id):
    product = Products.objects(id=product_id).first()
    if not product:
        return "Product not found", 404

    sizes_data = {}
    gallery_data = {}

    for variant in product.variants:
        # Populate sizes_data
        if variant.size not in sizes_data:
            sizes_data[variant.size] = {
                'product_id': str(product.id),
                'value': variant.size,
                'size_type': 'standard',
                'id': str(variant.id) + '_size',
                'variants': []
            }
        sizes_data[variant.size]['variants'].append({
            'value': variant.color_hexa_code if hasattr(variant, 'color_hexa_code') else variant.color,
            'name': variant.color,
            'stock_quantity': variant.stock_quantity,
            'id': str(variant.id)
        })

        # Populate gallery_data (using a set for uniqueness)
        for image in variant.images:
            if variant.color not in gallery_data:
                gallery_data[variant.color] = set()
            gallery_data[variant.color].add((str(image.id), image.image_url))

    # Create the final gallery list
    gallery = []
    for color, image_set in gallery_data.items():
        for img_id, img_url in image_set:
            gallery.append({
                'color': color,
                'id': img_id,
                'img_url': img_url
            })

    thumbnail_url = None
    if product.variants and product.variants[0].images:
        thumbnail_url = product.variants[0].images[0].image_url

    product_dict = {
        'seller_id': str(product.seller_id.id) if product.seller_id else None,
        'title': product.name,
        'description': product.description,
        'details': product.details,
        'price': float(product.price) if product.price else None,
        'discount_percent': product.discount_price,
        'sku': product.sku_number,
        'stock_quantity': sum(v.stock_quantity for v in product.variants) if product.variants else 0,
        'final_price': product.final_price,
        'id': str(product.id),
        'thumbnail_url': thumbnail_url,
        'sizes': list(sizes_data.values()),
        'gallery': gallery,
        'category': {
            'name': product.category_id.name if product.category_id else None,
            'description': getattr(product.category_id, 'description', None),
            'id': str(product.category_id.id) if product.category_id else None,
            'img_url': getattr(product.category_id, 'img_url', None)
        },
        'sub_category': {
            'name': product.subcategory_id.name if product.subcategory_id else None,
            'description': getattr(product.subcategory_id, 'description', None),
            'category_id': str(product.subcategory_id.category.id) if product.subcategory_id and product.subcategory_id.category else None,
            'id': str(product.subcategory_id.id) if product.subcategory_id else None,
            'img_url': getattr(product.subcategory_id, 'img_url', None)
        },
        'sub_sub_category': {
            'name': product.subsubcategory_id.name if product.subsubcategory_id else None,
            'description': getattr(product.subsubcategory_id, 'description', None),
            'category_id': str(product.subsubcategory_id.category_id.id) if product.subsubcategory_id and product.subsubcategory_id.category_id else None,
            'sub_category_id': str(product.subsubcategory_id.sub_category_id.id) if product.subsubcategory_id and product.subsubcategory_id.sub_category_id else None,
            'id': str(product.subsubcategory_id.id) if product.subsubcategory_id else None,
            'img_url': getattr(product.subsubcategory_id, 'img_url', None)
        },
        'brand': {
            'name': product.brand_id.name if product.brand_id else None,
            'description': getattr(product.brand_id, 'description', None),
            'id': str(product.brand_id.id) if product.brand_id else None,
            'img_url': getattr(product.brand_id, 'img_url', None)
        }
    }

    return render_template('admin/products/product_details.html', product=product_dict, local_ip=local_ip)


@admin_api.route(GET_PROUDCT_EDIT_PAGE_BY_ID_WEB_URL, methods=['GET'])
def edit_product_page(product_id):
    product = Products.objects(id=product_id).first()
    if not product:
        return "Product not found", 404

    colors_data = {}
    
    for variant in product.variants:
        color_name = variant.color
        color_value = variant.color_hexa_code if hasattr(variant, 'color_hexa_code') else variant.color
        
        if color_name not in colors_data:
            colors_data[color_name] = {
                'name': color_name,
                'value': color_value,
                'sizes': [],
                'images': []  # Changed from set to list to store dictionaries
            }
        
        colors_data[color_name]['sizes'].append({
            'size': variant.size,
            'size_type': 'standard',
            'stock_quantity': variant.stock_quantity,
            'variant_id': str(variant.id)
        })
        
        for image in variant.images:
            if image.image_url:
                image_url = url_for('serve_uploaded_files', filename=image.image_url, _external=True)
                # Add both image URL and ID
                image_data = {
                    'url': image_url,
                    'id': str(image.id)  # Assuming the image object has an 'id' field
                }
                # Check if this image is already added (by ID)
                if not any(img['id'] == image_data['id'] for img in colors_data[color_name]['images']):
                    colors_data[color_name]['images'].append(image_data)

    product_dict = {
        'seller_id': str(product.seller_id.id) if product.seller_id else None,
        'title': product.name,
        'description': product.description,
        'details': product.details,
        'price': float(product.price) if product.price else None,
        'discount_percent': product.discount_price,
        'sku': product.sku_number,
        'stock_quantity': sum(v.stock_quantity for v in product.variants) if product.variants else 0,
        'final_price': product.final_price,
        'id': str(product.id),
        'colors': list(colors_data.values()),
        'category': {
            'name': product.category_id.name if product.category_id else None,
            'id': str(product.category_id.id) if product.category_id else None,
        },
        'sub_category': {
            'name': product.subcategory_id.name if product.subcategory_id else None,
            'id': str(product.subcategory_id.id) if product.subcategory_id else None,
        },
        'sub_sub_category': {
            'name': product.subsubcategory_id.name if product.subsubcategory_id else None,
            'id': str(product.subsubcategory_id.id) if product.subsubcategory_id else None,
        },
        'brand': {
            'name': product.brand_id.name if product.brand_id else None,
            'id': str(product.brand_id.id) if product.brand_id else None,
        }
    }

    return render_template('admin/products/product_edit.html', product=product_dict, local_ip=local_ip)


@admin_api.route(EDIT_PRODUCT_WEB_URL, methods=['PUT'])
def update_product():
    try:
        user_id = session.get('user_id')
        if not user_id:
            return create_error_response({'error': 'User not logged in'}, 401)
        
        # Validate IDs
        try:
            user_object_id = ObjectId(user_id)
            product_id = ObjectId(request.form.get('product_id'))
        except Exception:
            return create_error_response({'error': 'Invalid ID format'}, 400)

        # Find the product
        product = Products.objects(id=product_id).first()
        if not product:
            return create_error_response({'error': 'Product not found or unauthorized'}, 404)

        # Prepare update fields
        data = request.form.to_dict()
        update_fields = {
            'name': data.get('name'),
            'description': data.get('description'),
            'details': data.get('details'),
            'price': float(data.get('price', 0)),
            'discount_price': float(data.get('discount_price', 0)),
            'stock_quantity': int(data.get('stock_quantity', 0)),
            'category_id': ObjectId(data.get('category_id')),
            'subcategory_id': ObjectId(data.get('subcategory_id')),
            'subsubcategory_id': ObjectId(data.get('subsubcategory_id')),
            'updated_at': datetime.utcnow()
        }

        # Handle brand
        brand_value = data.get('brand_id')
        other_brand_name = data.get('other_brand')
        
        if brand_value and brand_value != 'other':
            brand = ProductBrands.objects(id=brand_value).first()
            if not brand:
                return create_error_response({'error': 'Invalid brand ID'}, 400)
            update_fields['brand_id'] = brand
        elif brand_value == 'other' and other_brand_name:
            brand = ProductBrands.objects(name__iexact=other_brand_name.strip()).first()
            if not brand:
                brand = ProductBrands(
                    name=other_brand_name.strip(),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                brand.save()
            update_fields['brand_id'] = brand

        # Parse variations
        try:
            variations_list = json.loads(data.get('variations', '[]'))
        except json.JSONDecodeError:
            return create_error_response({'error': 'Invalid variations format'}, 400)

        # Dictionary to store images by color (color: [image_urls])
        color_images_map = {}
        # Dictionary to track all created images (image_url: image_object)
        variant_images_map = {}

        # Process all images, grouping by color (ignore size for upload)
        for file_key in request.files:
            if file_key.startswith('images[') and ']' in file_key:
                try:
                    parts = file_key.split('[')
                    color = parts[1].split(']')[0].strip()
                    
                    # Only process if we haven't seen this color before
                    if color not in color_images_map:
                        color_images_map[color] = []
                        # Upload all files for this color
                        for file in request.files.getlist(file_key):
                            image_path, error = upload_image(file)
                            if error:
                                return create_error_response({'error': error}, 400)
                            color_images_map[color].append(image_path)
                except Exception as e:
                    return create_error_response({'error': f'Invalid image key format: {str(e)}'}, 400)

        # Process variants
        existing_variants = {f"{v.color}_{v.size}": v for v in product.variants}
        new_variant_keys = {f"{v['color']}_{v['size']}" for v in variations_list}
        
        for var in variations_list:
            try:
                color = var['color']
                size = var['size']
                variant_key = f"{color}_{size}"
                
                if variant_key in existing_variants:
                    # Update existing variant
                    variant = existing_variants[variant_key]
                    variant.stock_quantity = int(var.get('stock_quantity', 0))
                    variant.color_hexa_code = var.get('color_hexa_code')
                    variant.updated_at = datetime.utcnow()
                    
                    # Handle images for existing variant - MODIFIED TO PRESERVE EXISTING IMAGES
                    if color in color_images_map:
                        # Get existing image URLs to avoid duplicates
                        existing_image_urls = {img.image_url for img in variant.images}
                        
                        # Add new images (shared across all variants with same color)
                        for image_url in color_images_map[color]:
                            # Skip if image already exists for this variant
                            if image_url in existing_image_urls:
                                continue
                                
                            # If image not already created in this session, make new record
                            if image_url not in variant_images_map:
                                image = ProductVariantImage(
                                    variant_id=variant.id,
                                    image_url=image_url,
                                    alt_text=f"{update_fields['name']} - {color} - {size}",
                                )
                                image.save()
                                variant_images_map[image_url] = image
                            
                            # Associate image with variant
                            variant.images.append(variant_images_map[image_url])
                    
                    variant.save()
                else:
                    # Create new variant
                    variant = ProductVariant(
                        size=size,
                        color=color,
                        color_hexa_code=var.get('color_hexa_code'),
                        stock_quantity=int(var.get('stock_quantity', 0)),
                        product_id=product.id
                    )
                    variant.save()
                    
                    if color in color_images_map:
                        variant.images = []
                        for image_url in color_images_map[color]:
                            # Reuse existing image record if available
                            if image_url in variant_images_map:
                                variant.images.append(variant_images_map[image_url])
                            else:
                                image = ProductVariantImage(
                                    variant_id=variant.id,
                                    image_url=image_url,
                                    alt_text=f"{update_fields['name']} - {color} - {size}",
                                )
                                image.save()
                                variant_images_map[image_url] = image
                                variant.images.append(image)
                    
                    variant.save()
                    product.variants.append(variant)
                    
            except (KeyError, ValueError) as e:
                return create_error_response({'error': f'Invalid variation data: {str(e)}'}, 400)

        for variant_key, variant in existing_variants.items():
            if variant_key not in new_variant_keys:
                ProductVariantImage.objects(variant_id=variant.id).delete()
                product.variants.remove(variant)
                variant.delete()

        product.update(**update_fields)
        
        if update_fields['discount_price'] > 0:
            product.final_price = update_fields['price'] - (update_fields['price'] * update_fields['discount_price'] / 100)
        else:
            product.final_price = update_fields['price']
        
        product.save()

        return jsonify({
            "message": "Product updated successfully",
            "id": str(product.id),
            "product": {
                "name": product.name,
                "price": float(product.price),
                "discount_price": float(product.discount_price) if product.discount_price else None,
                "final_price": float(product.final_price)
            }
        }), 200

    except Exception as error:
        return create_error_response({'error': str(error)}, 500)

@admin_api.route(REMOVE_PRODUCT_IMAGE_WEB_URL, methods=['DELETE'])
def remove_product_image():
    try:
        user_id = session.get('user_id')
        if 'user_id' not in session:
            return redirect(url_for('admin_api.login_page'))
        
        product_id = request.form.get('product_id')
        image_id = request.form.get('image_id')
        
        if not product_id or not image_id:
            return create_error_response({'error': 'Missing image_id or product_id'}, 400)

        try:
            product_id_obj = ObjectId(product_id)
            image_id_obj = ObjectId(image_id)
        except Exception as e:
            return create_error_response({'error': 'Invalid ID format'}, 400)

        product = Products.objects(id=product_id_obj).first()
        if not product:
            return create_error_response({'error': 'Product not found'}, 404)

        image_removed = False
        image_url = None

        # Convert image_id to string for comparison
        target_image_id_str = str(image_id_obj)

        # Iterate through all variants
        for variant in product.variants:
            # Check each image in the variant
            for img in variant.images:
                if str(img.id) == target_image_id_str:
                    image_url = img.image_url
                    variant.images.remove(img)
                    variant.save()
                    image_removed = True
                    break  # Exit inner loop once found

            if image_removed:
                break  # Exit outer loop if image was found and removed

        if not image_removed:
            # Provide more detailed error information
            variant_images = []
            for v in product.variants:
                variant_images.extend(str(img.id) for img in v.images)
            
            return create_error_response({
                'error': 'Image not found in product variants',
                'details': {
                    'requested_image_id': target_image_id_str,
                    'existing_image_ids': variant_images,
                    'variant_count': len(product.variants)
                }
            }, 404)

        # Check if image is still referenced by any variant
        image_still_used = any(
            str(img.id) == target_image_id_str
            for variant in product.variants
            for img in variant.images
        )

        # Delete image record if no longer used (but keep the file in storage)
        if not image_still_used:
            ProductVariantImage.objects(id=image_id_obj).delete()
            # Removed the delete_image_from_storage call

        return jsonify({
            "success": True,
            "message": "Image removed successfully",
            "image_id": target_image_id_str,
            "note": "Image file was kept in storage"
        }), 200

    except Exception as error:
        print(f"Error in remove_product_image: {str(error)}")
        return create_error_response({'error': 'Internal server error'}, 500)