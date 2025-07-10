from functools import wraps
from flask import request, jsonify
from app.models import User, Role

def role_required(roles):
    def decorator(func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            user_id = request.headers.get('X-User-ID') 
            user = User.objects(id=user_id).first()
            if user is None or user.role not in roles:
                return jsonify({"message": "Unauthorized"}), 403
            return func(*args, **kwargs)
        return wrapped_function
    return decorator
