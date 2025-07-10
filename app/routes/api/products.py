from flask import Blueprint, request, jsonify, session, url_for
from datetime import datetime
from constants import PRODUCT_LISTS_API, PRODUCT_LISTS_BY_ID_API
from app.models import Products, Category, SubCategory, SubSubCategory, Seller, User
from app.models.products import ProductVariant, ProductVariantImage
from app.utils.image_upload import upload_image
from app.utils.validation import validate_required_fields
from app.utils.utils import create_error_response
from flask import current_app
from mongoengine.queryset.visitor import Q
from app.extensions import db

products_bp = Blueprint('products_bp', __name__)

@products_bp.route(PRODUCT_LISTS_API, methods=['GET'])
def get_all_products():
    try:
        all_data = request.args.get('all_data', 'false').lower() == 'true'
        page = int(request.args.get('page', 1)) if not all_data else 1
        per_page = int(request.args.get('per_page', 10)) if not all_data else 0
        status = request.args.get('status')
        sort_by = request.args.get('sort_by', 'created_at')
        sort_order = request.args.get('sort_order', 'desc')
        
        search_term = request.args.get('searchTerm')
        min_price = request.args.get('minPrice')
        max_price = request.args.get('maxPrice')
        brand_ids = request.args.get('brandIds')
        category_ids = request.args.get('categoryIds')
        subcategory_ids = request.args.get('subCategoryIds')
        subsubcategory_ids = request.args.get('subSubCategoryIds')
        sizes = request.args.get('sizes')
        colors = request.args.get('colors')
        
        query = Products.objects()

        # Step 1: Filter by size and color (if provided)
        variant_ids = []
        if sizes or colors:
            variant_query = ProductVariant.objects()
            if sizes:
                size_list = [s.strip() for s in sizes.split(',') if s.strip()]
                variant_query = variant_query.filter(size__in=size_list)
            if colors:
                color_list = [c.strip() for c in colors.split(',') if c.strip()]
                variant_query = variant_query.filter(color__in=color_list)
            # Get the IDs of matching variants
            variant_ids = [variant.id for variant in variant_query]
            if variant_ids:
                query = query.filter(variants__in=variant_ids)
            else:
                # If no variants match, return empty result
                query = query.filter(id=None)  # No products will match

        # Step 2: Apply other filters
        if status:
            query = query.filter(status=status)
            
        if search_term:
            query = query.filter(Q(name__icontains=search_term) | Q(description__icontains=search_term))
            
        if min_price:
            query = query.filter(final_price__gte=float(min_price))
            
        if max_price:
            query = query.filter(final_price__lte=float(max_price))
            
        if brand_ids:
            brand_id_list = [bid.strip() for bid in brand_ids.split(',') if bid.strip()]
            if brand_id_list:
                query = query.filter(brand_id__in=brand_id_list)
            
        if category_ids:
            category_id_list = [cid.strip() for cid in category_ids.split(',') if cid.strip()]
            if category_id_list:
                query = query.filter(category_id__in=category_id_list)
            
        if subcategory_ids:
            subcategory_id_list = [scid.strip() for scid in subcategory_ids.split(',') if scid.strip()]
            if subcategory_id_list:
                query = query.filter(subcategory_id__in=subcategory_id_list)
            
        if subsubcategory_ids:
            subsubcategory_id_list = [sscid.strip() for sscid in subsubcategory_ids.split(',') if sscid.strip()]
            if subsubcategory_id_list:
                query = query.filter(subsubcategory_id__in=subsubcategory_id_list)

        # Step 3: Apply sorting
        if sort_order == 'desc':
            query = query.order_by(f'-{sort_by}')
        else:
            query = query.order_by(f'+{sort_by}')

        # Step 4: Fetch products
        if all_data:
            products = query.all()
            products_data = []
        else:
            paginated_products = query.paginate(page=page, per_page=per_page)
            products = paginated_products.items
            products_data = []

        # Step 5: Construct response
        for product in products:
            sizes_data = {}
            gallery_data = {}

            for variant in product.variants:
                if variant.size not in sizes_data:
                    sizes_data[variant.size] = {
                        'product_id': str(product.id),
                        'value': variant.size,
                        'size_type': 'standard',
                        'id': str(variant.id) + '_size',
                        'variants': []
                    }
                sizes_data[variant.size]['variants'].append({
                    'value': variant.color_hexa_code if variant.color_hexa_code else variant.color,
                    'name': variant.color,
                    'stock_quantity': variant.stock_quantity,
                    'id': str(variant.id)
                })

                for image in variant.images:
                    if variant.color not in gallery_data:
                        gallery_data[variant.color] = []
                    gallery_data[variant.color].append({
                        'color': variant.color,
                        'id': str(image.id),
                        'img_url': url_for('serve_uploaded_files', filename=image.image_url, _external=True)
                    })
            thumbnail_url = None
            if product.variants and product.variants[0].images:
                image_url = product.variants[0].images[0].image_url
                thumbnail_url = url_for('serve_uploaded_files', filename=image_url, _external=True)

            seller_data = None
            if product.seller_id:
                try:
                    seller = Seller.objects(id=product.seller_id.id).first()
                    if seller:
                        seller_data = {
                            'id': str(seller.id),
                            'businessName': seller.businessName
                        }
                    else:
                        seller_data = {'id': str(product.seller_id.id), 'businessName': 'Unknown Seller'}
                except Exception as e:
                    print(f"Error fetching seller for product {product.id}: {str(e)}")
                    seller_data = {'id': str(product.seller_id.id), 'businessName': 'Unknown Seller'}

            product_dict = {
                'seller': seller_data,
                'title': product.name,
                'description': product.description,
                'details': product.details,
                'price': float(product.price) if product.price else None,
                'discount_percent': float(product.discount_price) if product.discount_price else None,
                'sku': product.sku_number,
                'stock_quantity': sum(v.stock_quantity for v in product.variants) if product.variants else 0,
                'final_price': float(product.final_price) if product.final_price else None,
                'id': str(product.id),
                'thumbnail_url': thumbnail_url,
                'sizes': list(sizes_data.values()),
                'gallery': [img for color_gallery in gallery_data.values() for img in color_gallery],
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
            products_data.append(product_dict)

        if all_data:
            response = {
                'data': products_data
            }
        else:
            response = {
                'data': products_data,
                'current_page': page,
                'per_page': per_page,
                'last_page': paginated_products.pages,
                'total_items': paginated_products.total
            }

        return jsonify(response), 200

    except Exception as e:
        return create_error_response({"error": str(e)}, status_code=500)

@products_bp.route(PRODUCT_LISTS_BY_ID_API, methods=['GET'])
def get_product_by_id(product_id):
    try:
        product = Products.objects(id=product_id).first()

        if not product:
            return create_error_response({"error": "Product not found"}, status_code=404)
        
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

            for image in variant.images:
                if variant.color not in gallery_data:
                    gallery_data[variant.color] = []
                gallery_data[variant.color].append({
                    'color': variant.color,
                    'id': str(image.id),
                    'img_url': url_for('serve_uploaded_files', filename=image.image_url, _external=True)
                })

        thumbnail_url = None
        if product.variants and product.variants[0].images:
            thumbnail_url = url_for('serve_uploaded_files', filename=product.variants[0].images[0].image_url, _external=True)

        product_data = {
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
            'gallery': [img for color_gallery in gallery_data.values() for img in color_gallery],
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

        response = {
            'data': product_data,
        }

        return jsonify(response), 200

    except Exception as e:
        return create_error_response({"error": str(e)}, status_code=500)