from flask import Blueprint

admin_api = Blueprint("admin_api", __name__, url_prefix="")

from .auth_routes import *
from .dashboard_routes import *
from .user_routes import *
from .seller_routes import *
from .category_routes import *
from .sub_category_routes import *
from .sub_sub_category_routes import *
from .products_routes import *
from .order_routes import *
from .settings_routes import *
from .brands_routes import *
from .seller_routes import *
from .promo_code_routes import *