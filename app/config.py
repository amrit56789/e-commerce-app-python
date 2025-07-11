import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
from urllib.parse import quote_plus 
import razorpay

load_dotenv()

username = quote_plus(os.getenv('MONGO_USERNAME'))
password = quote_plus(os.getenv('MONGO_PASSWORD'))

MONGO_URI = f"mongodb+srv://{username}:{password}@cluster0.jfsv6k2.mongodb.net/"

class Config:
    SECRET_KEY = os.getenv('SESSION_SECRET_KEY', 'your-secret-key-here')
    MONGODB_SETTINGS = {
        'db': os.getenv('MONGO_DB'),
        'host': MONGO_URI
    }
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    JWT_ACCESS_TOKEN_EXPIRES = int(os.getenv('JWT_ACCESS_TOKEN_EXPIRES', 3600))
    MAIL_SERVER = os.getenv('MAIL_SERVER')
    MAIL_PORT = int(os.getenv('MAIL_PORT'))
    MAIL_USE_TLS = os.getenv('MAIL_USE_TLS', 'true').lower() == 'true'
    MAIL_USERNAME = os.getenv('MAIL_USERNAME')
    MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.getenv('MAIL_DEFAULT_SENDER')
    
    # Cloudinary configuration
    CLOUDINARY_CLOUD_NAME = os.getenv('CLOUDINARY_CLOUD_NAME')
    CLOUDINARY_API_KEY = os.getenv('CLOUDINARY_API_KEY')
    CLOUDINARY_API_SECRET = os.getenv('CLOUDINARY_API_SECRET')
    
    # Razorpay configuration
    RAZORPAY_KEY_ID = os.getenv('RAZORPAY_KEY_ID')
    RAZORPAY_KEY_SECRET = os.getenv('RAZORPAY_KEY_SECRET')
    
    SERVER_PORT = int(os.getenv('SERVER_PORT', 8080))
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')

    @classmethod
    def init_app(cls, app):
        # Initialize Cloudinary
        cloudinary.config(
            cloud_name=cls.CLOUDINARY_CLOUD_NAME,
            api_key=cls.CLOUDINARY_API_KEY,
            api_secret=cls.CLOUDINARY_API_SECRET
        )
        
        # Initialize Razorpay
        app.razorpay_client = razorpay.Client(auth=(cls.RAZORPAY_KEY_ID, cls.RAZORPAY_KEY_SECRET))