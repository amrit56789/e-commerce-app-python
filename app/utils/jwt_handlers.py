from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt
from flask_jwt_extended.exceptions import JWTExtendedException
from jwt.exceptions import PyJWTError

def jwt_error_handler(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return f(*args, **kwargs)
        except JWTExtendedException as e:
            return unauthorized_response(str(e))
        except PyJWTError as e:
            return invalid_token_response(str(e))
        except Exception as e:
            return create_error_response(str(e), 500)
    return decorated_function

def unauthorized_response(message=None):
    return jsonify({
        'error': 'Unauthorized',
        'message': message or 'Missing or invalid Authorization header'
    }), 401

def invalid_token_response(message=None):
    return jsonify({
        'error': 'Invalid token',
        'message': 'Invalid JWT token'
    }), 401

def expired_token_response(message=None):
    return jsonify({
        'error': 'Token expired',
        'message': message or 'Token has expired'
    }), 401

def create_error_response(message, status_code):
    return jsonify({
        'error': 'Authentication failed',
        'message': message
    }), status_code
