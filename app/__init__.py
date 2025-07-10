from flask import Flask, redirect, url_for, session, g, current_app
from app.extensions import db, jwt, mail, bcrypt
from .config import Config
from app.models import User
import os
from app.utils.sidebar import sidebar_context
from flask_cors import CORS
import firebase_admin
from firebase_admin import credentials, messaging

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app)
    
    app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
    app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    bcrypt.init_app(app)

    # Import models here
    from app.models.user import User
    from app.models.role import Role
    from app.models.seller import Seller
    from app.models.brands import ProductBrands
    from app.models.address import Address
    from app.models.identification import Identification
    from app.models.category_modal import Category, SubCategory, SubSubCategory
    from app.models.products import Products, ProductVariant
    from app.models.search_keyword_analytics import SearchKeywordAnalytics
    from app.seed_data import seed_data

    from app.models.brands import ProductBrands
    from app.seed_data import seed_data

    
    sidebar_context(app)
    with app.app_context():
        Role.initialize_roles()
        User.create_default_admin()
        seed_data()

    # Import routes and blueprints
    from app.routes.api.auth import auth_bp
    from app.routes.web import admin_api
    from app.routes.api.user import user_bp
    from app.routes.api.seller import seller_bp
    from app.routes.api.category import category_bp
    from app.routes.api.subcategory import subcategory_bp
    from app.routes.api.sub_sub_category import sub_sub_category_bp
    from app.routes.api.products import products_bp
    from app.routes.api.brands import brand_bp
    from app.routes.api.cart import cart_bp
    from app.routes.api.wishlist_bp import wishlist_bp
    from app.routes.api.saveforlater_bp import saveforlater_bp
    from app.routes.api.product_search_api import search_bp
    from app.routes.api.order_api import order_bp
    from app.routes.api.manage_address_api import address_bp
    from app.routes.api.dashboard_sales_api import sales_api
    from app.routes.api.product_review_api import reviews_bp
    from app.routes.api.promo_code_api import promo_bp
    
    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_api)
    app.register_blueprint(user_bp)
    app.register_blueprint(seller_bp)
    app.register_blueprint(category_bp)
    app.register_blueprint(subcategory_bp)
    app.register_blueprint(sub_sub_category_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(brand_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(wishlist_bp)
    app.register_blueprint(saveforlater_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(order_bp)
    app.register_blueprint(address_bp)
    app.register_blueprint(sales_api)
    app.register_blueprint(reviews_bp)
    app.register_blueprint(promo_bp)

    from app.utils.image_upload import image_store
    import base64
    from flask import Response, send_from_directory
    cred = credentials.Certificate("./serviceAccountKey.json")
    firebase_admin.initialize_app(cred)
    @app.route('/image/<image_id>')
    def serve_image(image_id):
        image_info = image_store.get(image_id)
        if not image_info:
            return "Image not found", 404

        decoded_image = base64.b64decode(image_info['data'])
        return Response(decoded_image, mimetype=image_info['content_type'])

    @app.before_request
    def before_request():
        if 'user_id' in session:
            g.current_user = User.objects(id=session['user_id']).first()
        else:
            g.current_user = None

    @app.route('/')
    def index():
        return redirect(url_for('admin_api.login_page'))

    @app.route('/static/uploads/<path:filename>')
    def serve_uploaded_files(filename):
        uploads_dir = os.path.join(app.root_path, 'static', 'uploads')
        return send_from_directory(uploads_dir, filename)

    return app
