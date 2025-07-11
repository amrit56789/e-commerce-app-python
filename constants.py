# Role constants
ROLE_ADMIN = "admin"
ROLE_SELLER = "seller"
ROLE_USER = "user"
ALL_ROLES = [ROLE_ADMIN, ROLE_SELLER, ROLE_USER]

# Gender constants
GENDER_MALE = "male"
GENDER_FEMALE = "female"
GENDER_OTHER = "other"
GENDER_CHOICES = [GENDER_MALE, GENDER_FEMALE, GENDER_OTHER]

OTP_EXPIRY_MINUTES = 10

# Allowed Size and Allowed Gender constants 
ALLOWED_SIZES = ['XS', 'S', 'M', 'L', 'XL', 'XXL', 'XXXL']
ALLOWED_GENDERS = ['Men', 'Women', 'Unisex', 'Kids']

APPROVAL_STATUSES = ['pending', 'approved', 'cancelled']

ORDER_STATUS = ['pending', 'confirmed', 'processing', 'shipped', 'outOfDelivery', 'delivered', 'cancelled', 'return', 'refund']

ADDRESS_TYPES = ['Home', 'Office', 'Work', 'Store', 'Business', 'Other']

INDIAN_STATES = [
        "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
        "Chandigarh", "Chhattisgarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi",
        "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand",
        "Karnataka", "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh", "Maharashtra",
        "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Puducherry", "Punjab",
        "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
        "Uttarakhand", "West Bengal"
    ];

REFERRAL_REWARDS = {
    'referrer': {
        'points': 100,
        'reason': 'Referral bonus for inviting a user'
    },
    'referred': {
        'points': 50,
        'reason': 'Referral bonus for signing up with a code'
    }
}

RAZOR_PAY_PAYMENT_LINK = f'https://api.razorpay.com/v1/payment_links'

PROMO_CODE_TYPES = ['percentage', 'fixed_amount']
PROMO_CODE_APPLICABLE_TO = ['all', 'specific']

# API Endpoint Constants
REGISTER = f'/register'
LOGIN = f'/login'
FORGOT_PASSWORD = f'/send-email-code'
VERIFY_OTP = f'/verify-email-code'
AUTHENTICATE_USER = f'/verify-user'
RESET_PASSWORD = f'/reset-password'
RESEND_OTP = f'/resend-otp'

# WEB Endpoint Constants Start
Login_WEB_URL = f'/login'
SIGNUP_WEB_URL = f'/signup'
FORGOT_PASSWORD_WEB_URL = f'/forgot-password'
VERIFY_OTP_WEB_URL= f'/verify-otp'
RESET_PASSWORD_WEB_URL = f'/reset-password'

DASHBOARD_WEB_URL = f'/dashboard'

ALL_USER_LIST_WEB_URL = f'/all-users-list'
ADD_NEW_USER_LIST_WEB_URL = f'/add-new-user'
EDIT_USER_WEB_URL = f'/users/edit/<string:user_id>'

ADD_SELLER_WEB_URL = f'/add-new-seller'
GET_SELLER_LIST_WEB_URL = f'/seller/list'
GET_SELLERS_API_URL = '/api/sellers'
EDIT_SELLERS_PAGE_WEB_URL = '/seller/edit/<seller_id>'

CATEGORY_LIST_WEB_URL = '/category-list'
ADD_CATEGORY_WEB_URL = '/add-new-category'
CATEGORY_LIST_WEB_URL = '/category/list'
SEARCH_CATEGORY_WEB_URL = f'/api/categories/search'
GET_CATEGORIES_FILTER_API_URL = '/categories-list'
DELETE_CATEGORIES_API_WEB_URL = '/delete_category/<category_id>'
EDIT_CATEGORY_WEB_URL = '/category/edit/<category_id>'

SUBCATEGORY_LIST_WEB_URL = f'/sub-categories/list'
Add_SUBCATEGORY_LIST_WEB_URL = f'/subcategories/add'
GET_SUBCATEGORIES_FILTER_API_URL = '/api/subcategories'
SEARCH_SUB_CATEGORY_WEB_URL = f'/api/sub-categories/search'
EDIT_SUB_CATEGORY_WEB_URL = '/sub-category/edit/<sub_category_id>'
UPDATE_SUB_CATEGORY_WEB_URL = '/update_sub_category/<sub_category_id>'
DELETE_SUB_CATEGORY_WEB_URL = '/delete_sub_category/<sub_category_id>'

SUB_SUB_CATEGORY_LIST_WEB_URL = f'/sub-sub-category-list'
SUB_SUB_CATEGORY_WEB_URL = f'sub-sub-category/add'
DELETE_SUB_SUB_CATEGORY_WEB_URL = '/delete-sub-sub-category/<sub_sub_category_id>'
EDIT_SUB_SUB_CATEGORY_WEB_URL= '/sub-sub-category/edit/<sub_sub_category_id>'
UPDATE_SUB_SUB_CATEGORY_WEB_URL = f'/sub-sub-category/update/<sub_sub_category_id>'


ADD_NEW_PRODUCT_WEB_URL = f'/api/products/add'
ADD_PRODUCT_PAGE_WEB_URL = f'/products/add'
GET_PRODUCT_LIST_WEB_URL = f'/products/list'
GET_PRODUCT_DETAILS_WEB_URL = f'/products/<product_id>'
GET_PROUDCT_EDIT_PAGE_BY_ID_WEB_URL = f'/products/edit/<product_id>'
EDIT_PRODUCT_WEB_URL = f'/api/products/edit'
REMOVE_PRODUCT_IMAGE_WEB_URL = f'/api/products/remove-image'

GET_BRANDS_WEB_URL = f'/brands/list'
ADD_BRAND_WEB_URL = f'/brands/add'
UPDATE_BRAND_WEB_URL = f'/brands/edit/<brand_id>'

GET_BRANDS_WEB_URL = f'/brands/list'
ADD_BRAND_WEB_URL = f'/brands/add'
UPDATE_BRAND_WEB_URL = f'/brands/edit/<brand_id>'

ORDER_LIST_WEB_URL = '/orders'
ORDER_STATUS_UPDATE_WEB_URL = f'/orders/<order_id>/update-status'
ORDER_DETAILS_PAGE_WEB_URL = f'/order-details/<order_id>'

ADD_PROMO_CODE_WEB_URL = '/add-promo-code'
PROMO_CODE_LIST_WEB_URL = '/promo-code-list'
EDIT_PROMO_CODE = f'/promo-code/edit/<promo_code_id>'
UPDATE_PROMO_CODE_WEB_URL = f'/promo-code/update/<promo_code_id>'
DELETE_PROMO_CODE = '/api/promo-code/<string:promo_code_id>/delete'
VALIDATE_PROMO_CODE = '/api/orders/validate-promo-code'
PROMO_CODE_LIST = f'/api/promo-code/list'
# WEB Endpoint Constants End

# API Endpoint Constants Start

# User API Endpoint Constants
GET_USER_PROFILE = f'/me'
UPDATE_PROFILE = f'/update-profile'
UPDATE_PROFILE_PIC = f'/update-profile-pic'
DELETE_PROFILE_PIC = f'/delete-profile-pic'
LOGOUT = f'/logout'
ADD_SELLER = f'/add-new-seller'
UPDATE_SELLER = f'/seller/update'

# Category API Endpoint Constants
API_CATEGORY_LIST = '/api/categories/list'
API_ADD_CATEGORY = '/api/categories/add'
API_CATEGORY_LIST_BY_ID = '/api/categories/list/<string:category_id>'

# Sub Category API Endpoint Constants
API_SUBCATEGORY_LIST = '/api/sub-categories/list'
API_ADD_SUBCATEGORY = '/api/sub-categories/add'
API_GET_SUBCATEGORIES_BY_CATEGORY_ID = '/api/sub-categories/list/<category_id>'

# Sub Sub Category API Endpoint Constants
SUB_SUB_CATEGORY_ADD_API = '/api/sub-sub-category/add'
GET_SUBSUBCATEGORIES_BY_CATEGORY_ID_API = '/api/sub-sub-categories/list';
# Sub Sub Category API Endpoint Constants End

#Product API Endpoint Constants Start
PRODUCT_LISTS_API= f'/api/products/list'
PRODUCT_LISTS__BY_ID_API = f'/api/products/<string:product_id>'
PRODUCT_LISTS_BY_ID_API = f'/api/products/<string:product_id>'
PRODUCT_REVIEW_API = f'/api/products/review'
GET_PRODUCT_REVIEW_BY_ID_API = f'/api/products/<string:product_id>/reviews'
GET_PRODUCT_USER_REVIEW_BY_ID_API = "/api/products/<product_id>/user-review"
GET_SIMILAR_PRODUCT_API = f'/api/products/<product_id>/similar'
#Product API Endpoint Constants End

# Brand Endpoint API Start
GET_BRANDS_LIST_API = '/api/brand/lists'
ADD_BRAND_API = '/api/brands/add'
UPDATE_BRAND_API = '/api/update-brand'
DELETE_BRAND_API = '/brands/delete/<brand_id>'
# Brand Endpoint API End

# Cart Endpoint API Start
CART_ADD = '/api/cart/add'
CART_REMOVE = '/api/cart/remove'
CART_REMOVE_ALL = '/api/cart/remove-all'
CART_LIST = '/api/cart/list'
CART_CHECKOUT = '/api/cart/checkout'
UPDATE_CART = f'/api/cart/update'
# Cart Endpoint API End

# Address Endpoint Start
ADDRESS_ADD = '/api/address/add'
ADDRESS_UPDATE = '/api/address/update'
ADDRESS_REMOVE = '/api/address/remove/<address_id>'
ADDRESS_LIST = '/api/address/list'
ADDRESS_TYPES_API = '/api/address/types-list'
# Address Endpoint End

# Wishlist Endpoint Start
WISHLIST_ADD = '/api/wishlist/add'
WISHLIST_REMOVE = '/api/wishlist/remove'
WISHLIST_LIST = '/api/wishlist/list'
WISHLIST_REMOVE_ALL= '/api/wishlist/remove-all'
WISHLIST_MOVE_TO_CART = '/api/wishlist/to-cart'
# Wishlist Endpoint End

# SaveForLater Endpoint Start
SAVEFORLATER_ADD = '/api/saveforlater/add'
SAVEFORLATER_REMOVE = '/api/saveforlater/remove'
SAVEFORLATER_LIST = '/api/saveforlater'
SAVEFORLATER_TO_CART = '/api/saveforlater/to-cart'
# SaveForLater Endpoint End

# Search Product Endpoint Start
SEARCH_PRODUCT_BY_KEYWORD_API = '/api/search-products'
SEARCH_RECOMMENDATION_API = '/api/search/recommendations'
SEARCH_AUTOCOMPLETE_API = '/api/search/autocomplete'
# Search Product Endpoint End

# Orders Endpoint Start
ORDER_PLACE_API = f'/api/orders/new'
ORDER_LIST_API = f'/api/orders/list'
GET_ORDER_STATUS_TYPES = f'/api/orders/status-types'
PAYMENT_CALLBACK_API = f'/api/payment-callback'
VERIFY_PAYMENT = f'/api/orders/verify-payment'
ORDER_SUCCESS_ROUTE = f'/order-success'
GET_PRODUCT_PURCHASE_STATS = f'/api/products/top-purchased'
# Orders Endpoint End

# Sales OverView Endpoint Start
SALES_OVERVIEW_API = f'/api/sales/overview'
SALES_OVER_TIME_API = f'/api/sales/over-time'
SALES_TOP_PRODUCTS_API = f'/api/sales/top-products'
RECENT_SALES_API = f'/api/sales/recent'
TOP_PRODUCT_SALES_API = f'/api/sales/top-products'
GET_SALES_SELLER = f'/api/sales/sellers'

# Generate Referral Code Enpoint End
RAZORPAY_BASE_URL = 'https://api.razorpay.com/v1/'
CREATE_RAZORPAY_PAYMENT_LINK = 'https://api.razorpay.com/v1/payment_links'
