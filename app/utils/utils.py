from flask import jsonify
import secrets
import string


def create_error_response(errors, status_code=400):
    return jsonify({'errors': errors}), status_code


def generate_random_password(length=12):
    # Define the characters to choose from
    alphabet = string.ascii_letters + string.digits + string.punctuation
    # Generate a random password of the given length
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

def generate_referral_code():
    prefix = "REF-"
    chars = string.ascii_uppercase + string.digits
    random_part = ''.join(secrets.choice(chars) for _ in range(12))
    return prefix + random_part