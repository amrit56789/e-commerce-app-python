from flask import jsonify
from functools import wraps
from flask_jwt_extended import get_jwt, verify_jwt_in_request

def role_required(role):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            if claims['role'] != role:
                return jsonify({'message': f'{role} role required'}), 403
            return f(*args, **kwargs)
        return decorated_function
    return decorator