from flask import render_template, session, redirect, url_for, request, jsonify
from . import admin_api
from app.models import User
from constants import Login_WEB_URL, SIGNUP_WEB_URL, FORGOT_PASSWORD_WEB_URL, VERIFY_OTP_WEB_URL, RESET_PASSWORD_WEB_URL
from app.utils.utils import create_error_response

@admin_api.route(Login_WEB_URL, methods=["GET", "POST"])
def login_page():
    if request.method == 'GET':
        if validate_admin_session():
            return redirect(url_for('admin_api.dashboard'))
        return render_template('admin/authFlow/login.html')

    if request.method == 'POST':
        if not request.form:
            return create_error_response({'error': 'Form data required'}, 400)

        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        fcm_token = request.form.get('fcm_token', '').strip()  # ← Get FCM token

        if not email or not password:
            return create_error_response({'error': 'Email and password required'}, 400)

        try:
            user = User.objects(email=email).first()

            if not user or not user.check_password(password):
                return create_error_response({'error': 'Invalid credentials'}, 401)

            # Save FCM token
            if fcm_token:
                user.fcm_token = fcm_token
                user.save()

            # Set session values
            session['user_id'] = str(user.id)
            session['email'] = user.email

            return jsonify({
                'message': 'Login successful',
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'fcm_token': user.fcm_token
                }
            })

        except Exception as e:
            return create_error_response({'error': 'Login failed', 'details': str(e)}, 500)

def validate_admin_session():
    if 'admin_token' not in session:
        return False
        
    try:
        token = session['admin_token']
        payload = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
        user = User.objects(id=payload['user_id']).first()
        return bool(user and user.is_admin)
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return False


@admin_api.route(SIGNUP_WEB_URL)
def signup_page():
    return render_template('admin/authFlow/signup.html')


@admin_api.route(FORGOT_PASSWORD_WEB_URL)
def forgot_password():
    return render_template('admin/authFlow/forgot_password.html')


@admin_api.route(VERIFY_OTP_WEB_URL)
def verify_otp():
    return render_template('admin/authFlow/verify-otp.html')


@admin_api.route(RESET_PASSWORD_WEB_URL)
def reset_password():
    return render_template('admin/authFlow/reset-password.html')
