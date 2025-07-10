import re

def validate_email(email):
    email_regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if not re.match(email_regex, email):
        return False, 'Please enter a valid email.'
    
    return True, ''

def validate_password(password):
    
    if len(password) < 6:
        return False, 'Password must be at least 6 characters long.'
    
    has_upper = any(c.isupper() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(not c.isalnum() for c in password)

    if not (has_upper and has_digit and has_special):
        return False, 'Password must contain at least one uppercase letter, one number, and one special character.'
    
    return True, ''

def validate_required_fields(data, fields, custom_errors=None):
    errors = {}
    for field in fields:
        keys = field.split('.')
        value = data
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                value = None
                break

        if value is None or (isinstance(value, str) and not value.strip()):
            error_message = custom_errors.get(field, f"The {field} field is required.") if custom_errors else f"The {field} field is required."
            errors[field] = error_message

    if errors:
        return False, errors
    return True, {}
