from flask import Blueprint, request, jsonify, current_app
from app.models import User, Role, Seller, Address, Identification
from app.utils.validation import validate_email, validate_required_fields
from app.utils.utils import generate_random_password, create_error_response
from app import db
from mongoengine import ValidationError
from app.utils.image_upload import upload_image, validate_fields
from constants import ADD_SELLER, ADDRESS_TYPES, UPDATE_SELLER, APPROVAL_STATUSES, ROLE_ADMIN, ROLE_SELLER, ROLE_USER

seller_bp = Blueprint('seller', __name__, url_prefix='/user')

@seller_bp.route(ADD_SELLER, methods=['POST'])
def add_seller():
    data = request.form
    files = request.files

    required_fields = [
        'email', 'first_name', 'last_name', 'phoneNumber',
        'address[line1]', 'address[city]', 'address[state]',
        'address[country]', 'address[postal_code]',
        'businessName', 'businessType', 'businessEmail', 'businessMobile',
        'gstNumber', 'panNumber', 'addressProofIdType', 'idNumber'
    ]

    is_valid, errors = validate_required_fields(data, required_fields)
    if not is_valid:
        return create_error_response({"error": errors}, 400)

    required_files = ['panCardFront', 'addressProofFront']
    missing_files = {}
    for file_key in required_files:
        if file_key not in files or files.get(file_key).filename == '':
            missing_files[file_key] = f"The {file_key} file is required."
    if missing_files:
        return create_error_response({"error": missing_files}, 400)

    is_valid, email_error = validate_email(data.get('email'))
    if not is_valid:
        return create_error_response({"error": email_error}, 400)

    if User.objects(email=data.get('email')).first():
        return create_error_response({"error": "User with this email already exists"}, 409)

    role = Role.objects(name='user').first()
    if not role:
        return create_error_response({"error": "Default role not found"}, 500)

    with db.connection.start_session() as session:
        session.start_transaction()
        try:
            user = User(
                email=data.get('email'),
                first_name=data.get('first_name'),
                last_name=data.get('last_name'),
                phone_number=data.get('phoneNumber'),
                role=role,
                password=generate_random_password()
            )
            user.save(session=session)

            personal_address_type = data.get('address[type]', 'Home')
            if personal_address_type not in ADDRESS_TYPES:
                raise ValidationError(f"Invalid personal address type: {personal_address_type}")

            personal_address = Address(
                user_id=user,
                line1=data.get('address[line1]'),
                line2=data.get('address[streetLine2]', ''),
                city=data.get('address[city]'),
                state=data.get('address[state]'),
                postal_code=data.get('address[postal_code]'),
                country=data.get('address[country]'),
                type=personal_address_type,
                is_primary=True
            )
            personal_address.save(session=session)

            business_address = None
            if data.get('businessAddress[line1]'):
                business_address_type = data.get('businessAddress[type]', 'Business')
                if business_address_type not in ADDRESS_TYPES:
                    raise ValidationError(f"Invalid business address type: {business_address_type}")

                business_address = Address(
                    user_id=user,
                    line1=data.get('businessAddress[line1]'),
                    line2=data.get('businessAddress[streetLine2]', ''),
                    city=data.get('businessAddress[city]'),
                    state=data.get('businessAddress[state]'),
                    postal_code=data.get('businessAddress[postal_code]'),
                    country=data.get('businessAddress[country]'),
                    type=business_address_type,
                    is_primary=False,
                    is_business_address=True
                )
                business_address.save(session=session)

            seller = Seller(
                user_id=user,
                businessName=data.get('businessName'),
                businessType=data.get('businessType'),
                businessEmail=data.get('businessEmail'),
                businessMobile=data.get('businessMobile'),
                address=personal_address,
                gst_number=data.get('gstNumber'),
                is_approved='pending'
            )
            seller.save(session=session)

            pan_card_front_url, err = upload_image(files.get('panCardFront'))
            if err:
                raise Exception(err)

            address_proof_front_url, err = upload_image(files.get('addressProofFront'))
            if err:
                raise Exception(err)

            identification = Identification(
                user_id=user,
                address_proof_id_type=data.get('addressProofIdType'),
                address_proof_front=address_proof_front_url,
                pan_number=data.get('panNumber'),
                pan_card_front=pan_card_front_url,
                id_number=data.get('idNumber')
            )
            identification.save(session=session)

            session.commit_transaction()

            return jsonify({
                "message": "Seller registered successfully. Awaiting approval.",
                "user_id": str(user.id),
                "seller_id": str(seller.id),
                "address_id": str(personal_address.id),
                "business_address_id": str(business_address.id) if business_address else None
            }), 200

        except ValidationError as e:
            session.abort_transaction()
            return create_error_response({"error": f"Validation error: {str(e)}"}, 400)
        except Exception as e:
            session.abort_transaction()
            import traceback
            traceback.print_exc()
            return create_error_response({"error": f"Internal server error: {str(e)}"}, 500)


@seller_bp.route(UPDATE_SELLER, methods=['PUT'])
def update_seller():
    data = request.form
    files = request.files
    seller_id = data.get('seller_id')

    if not seller_id:
        return create_error_response({"error": "Seller ID is required"}, 400)

    seller = Seller.objects(id=seller_id).first()
    if not seller:
        return create_error_response({"error": "Seller not found"}, 404)

    user = User.objects(id=seller.user_id.id).first()
    if not user:
        return create_error_response({"error": "Associated user not found"}, 404)

    updatable_user_fields = ['email', 'first_name', 'last_name', 'phoneNumber']
    updatable_seller_fields = ['businessName', 'businessType', 'businessEmail', 'businessMobile', 'gst_number']
    updatable_address_fields = ['address[line1]', 'address[line2]', 'address[city]', 'address[state]', 
                              'address[postal_code]', 'address[country]', 'address[type]']
    updatable_business_address_fields = ['businessAddress[line1]', 'businessAddress[line2]', 
                                       'businessAddress[city]', 'businessAddress[state]', 
                                       'businessAddress[postal_code]', 'businessAddress[country]', 
                                       'businessAddress[type]']
    updatable_identification_fields = ['addressProofIdType', 'idNumber', 'panNumber']
    update_seller_status = ['is_approved']

    missing_files = {}
    if 'panCardFront' not in files and 'panCardFront' not in data:
        missing_files['panCardFront'] = "PAN card front image is required"
    if 'addressProofFront' not in files and 'addressProofFront' not in data:
        missing_files['addressProofFront'] = "Address proof front image is required"
    if missing_files:
        return create_error_response({"error": missing_files}, 400)

    with db.connection.start_session() as session:
        session.start_transaction()
        try:
            if 'email' in data:
                is_valid, email_error = validate_email(data.get('email'))
                if not is_valid:
                    return create_error_response({"error": email_error}, 400)
                existing_user = User.objects(email=data.get('email')).first()
                if existing_user and str(existing_user.id) != str(user.id):
                    return create_error_response({"error": "Email already in use"}, 409)

            for field in updatable_user_fields:
                if field in data:
                    if field == 'phoneNumber':
                        setattr(user, 'phone_number', data.get(field))
                    else:
                        setattr(user, field, data.get(field))
            user.save(session=session)

            personal_address = seller.address or Address.objects(
                user_id=user.id, 
                is_primary=True
            ).first()

            if any(field in data for field in updatable_address_fields):
                if not personal_address:
                    personal_address = Address(
                        user_id=user.id, 
                        is_primary=True,
                        is_business_address=False
                    )
                
                address_data = {}
                for key in updatable_address_fields:
                    if key in data:
                        field_name = key.split('[')[1][:-1]
                        address_data[field_name] = data.get(key)
                
                address_data.update({
                    'is_primary': True,
                    'is_business_address': False,
                    'type': address_data.get('type', 'personal')
                })
                
                if address_data['type'] not in ADDRESS_TYPES:
                    raise ValidationError(f"Invalid personal address type: {address_data['type']}")
                
                for key, value in address_data.items():
                    setattr(personal_address, key, value)
                
                personal_address.save(session=session)

            business_address = seller.businessAddress or Address.objects(
                user_id=user.id, 
                is_business_address=True
            ).first()

            if any(field in data for field in updatable_business_address_fields):
                business_address_data = {}
                for key in updatable_business_address_fields:
                    if key in data:
                        field_name = key.split('[')[1][:-1]
                        business_address_data[field_name] = data.get(key)
                
                if not business_address:
                    business_address = Address(
                        user_id=user.id,
                        is_primary=False,
                        is_business_address=True,
                        type=business_address_data.get('type', 'business')
                    )
                
                business_address_data.update({
                    'is_primary': False,
                    'is_business_address': True,
                    'type': business_address_data.get('type', 'business')
                })
                
                if business_address_data['type'] not in ADDRESS_TYPES:
                    raise ValidationError(f"Invalid business address type: {business_address_data['type']}")
                
                for key, value in business_address_data.items():
                    setattr(business_address, key, value)
                
                business_address.save(session=session)
                seller.businessAddress = business_address

            for field in updatable_seller_fields:
                if field in data:
                    setattr(seller, field, data.get(field))
            
            for field in update_seller_status:
                if field in data:
                    if field == 'is_approved':
                        if data.get(field) not in APPROVAL_STATUSES:
                            return create_error_response({"error": f"Invalid status. Must be one of: {APPROVAL_STATUSES}"}, 400)
                        
                        if data.get(field) == "approved":
                            new_role = Role.objects(name="seller").first()
                        else:
                            new_role = Role.objects(name="user").first()
                            
                        if not new_role:
                            return create_error_response({"error": "Role not found in system"}, 500)
                        
                        if user.role != new_role:
                            user.role = new_role
                            user.save(session=session)
                    
                    setattr(seller, field, data.get(field))
            
            if personal_address:
                seller.address = personal_address
            seller.save(session=session)

            identification = Identification.objects(user_id=user.id).first()
            if any(field in data for field in updatable_identification_fields) or 'panCardFront' in files or 'addressProofFront' in files:
                if not identification:
                    identification = Identification(user_id=user.id)
                
                if 'addressProofIdType' in data:
                    identification.address_proof_id_type = data.get('addressProofIdType')
                if 'idNumber' in data:
                    identification.id_number = data.get('idNumber')
                if 'panNumber' in data:
                    identification.pan_number = data.get('panNumber')
                
                if 'panCardFront' in files and files['panCardFront'].filename:
                    pan_card_front_url, err = upload_image(files['panCardFront'])
                    if err:
                        raise Exception(err)
                    identification.pan_card_front = pan_card_front_url.split('/')[-1]
                elif data.get('panCardFront'):
                    if data['panCardFront'].startswith('http'):
                        identification.pan_card_front = data['panCardFront'].split('/')[-1]
                    else:
                        identification.pan_card_front = data['panCardFront']
                
                if 'addressProofFront' in files and files['addressProofFront'].filename:
                    address_proof_front_url, err = upload_image(files['addressProofFront'])
                    if err:
                        raise Exception(err)
                    identification.address_proof_front = address_proof_front_url.split('/')[-1]
                elif data.get('addressProofFront'):
                    if data['addressProofFront'].startswith('http'):
                        identification.address_proof_front = data['addressProofFront'].split('/')[-1]
                    else:
                        identification.address_proof_front = data['addressProofFront']
                
                identification.save(session=session)

            session.commit_transaction()

            return jsonify({
                "message": "Seller updated successfully",
                "user_id": str(user.id),
                "seller_id": str(seller.id),
                "address_id": str(personal_address.id) if personal_address else None,
                "business_address_id": str(business_address.id) if business_address else None,
                "identification_id": str(identification.id) if identification else None,
                "is_approved": seller.is_approved,
                "approved_by": str(seller.approved_by.id) if seller.approved_by else None,
                "role": user.role.name if user.role else None
            }), 200

        except ValidationError as e:
            session.abort_transaction()
            return create_error_response({"error": f"Validation error: {str(e)}"}, 400)
        except Exception as e:
            session.abort_transaction()
            import traceback
            traceback.print_exc()
            return create_error_response({"error": f"Internal server error: {str(e)}"}, 500)