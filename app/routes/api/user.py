from flask import Blueprint, request, jsonify, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models import User, Role, Seller, Address, Identification
import cloudinary.uploader
from constants import GET_USER_PROFILE, UPDATE_PROFILE, UPDATE_PROFILE_PIC, DELETE_PROFILE_PIC, ADD_SELLER
from app.utils.validation import validate_email, validate_password, validate_required_fields
from app.utils.utils import generate_random_password
from app import db
from mongoengine import ValidationError
from werkzeug.utils import secure_filename
import os
from app.utils.utils import create_error_response
from app.utils.image_upload import upload_image

user_bp = Blueprint('user', __name__, url_prefix='/api/user')

# Get user profile
@user_bp.route(GET_USER_PROFILE, methods=['GET'])
@jwt_required()
def get_user_profile():
    user_id = get_jwt_identity()
    user = User.objects(id=user_id).first()

    if not user:
        return jsonify({'message': 'User not found'}), 404

    profile = {
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone_number": user.phone_number,
        "profile_url": url_for('serve_uploaded_files', filename=user.profile_pic, _external=True) if user.profile_pic else None,
        "id": str(user.id),
        "role": {
            "name": user.role.name if user.role else None,
            "id": str(user.role.id) if user.role else None
        }
    }

    return jsonify({"data": profile}), 200


# Update user profile
@user_bp.route(UPDATE_PROFILE, methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    user = User.objects(id=user_id).first()

    if not user:
        return jsonify({'message': 'User not found'}), 404

    data = request.get_json()
    user.first_name = data.get('first_name', user.first_name)
    user.last_name = data.get('last_name', user.last_name)
    user.phone_number = data.get('phone_number', user.phone_number)
    user.gender = data.get('gender', user.gender)
    user.save()

    return jsonify({'message': 'Profile updated successfully'}), 200

@user_bp.route(UPDATE_PROFILE_PIC, methods=['POST'])
@jwt_required()
def update_profile_picture():
    user_id = get_jwt_identity()
    user = User.objects(id=user_id).first()

    if not user:
        return create_error_response({"error": "User not found"}, 404)

    if 'image' not in request.files:
        return create_error_response({"error": "No file part"}, 400)

    profile_image_file = request.files['image']

    try:
        uploaded_image_url, upload_error = upload_image(profile_image_file)

        if upload_error:
            return create_error_response({"error": upload_error}, 400)

        user.profile_pic = uploaded_image_url
        user.save()

        return jsonify({
            'status': 'success',
            "message": "Profile picture updated",
        }), 200

    except Exception as e:
        return create_error_response({"error": "Upload failed", "details": str(e)}, 500)

# Delete profile picture
@user_bp.route(DELETE_PROFILE_PIC, methods=['DELETE'])
@jwt_required()
def delete_profile_picture():
    user_id = get_jwt_identity()
    user = User.objects(id=user_id).first()

    if not user:
        return create_error_response({"error": "User not found"}, 404)

    if not user.profile_pic:
        return create_error_response({"error": "No profile picture found"}, 404)

    try:
        user.profile_pic = None
        user.save()

        return jsonify({
            'status': 'success',
            'message': 'Profile picture deleted successfully',
        }), 200

    except Exception as e:
        return create_error_response({"error": "Deletion failed", "details": str(e)}, 500)
