import os
import base64
import uuid
from werkzeug.utils import secure_filename
from flask import current_app, request, url_for
from .validation import validate_required_fields
import socket

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

image_store = {}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_local_ip():
    """Get the local IP address of the machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

def upload_image(image):
    if image and not allowed_file(image.filename):
        return None, 'Invalid image file type'

    if image:
        os.makedirs(current_app.config['UPLOAD_FOLDER'], exist_ok=True)

        ext = image.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        image.save(filepath)

        return filename, None  # only return filename
    return None, None


def validate_fields(data, required_fields):
    is_valid, validation_errors = validate_required_fields(data, required_fields)
    if not is_valid:
        return False, validation_errors
    return True, None
