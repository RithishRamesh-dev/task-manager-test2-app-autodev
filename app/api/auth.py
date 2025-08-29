from datetime import datetime, timedelta
from flask import request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, create_refresh_token, jwt_required, 
    get_jwt_identity, get_jwt
)
from werkzeug.security import check_password_hash
from sqlalchemy import or_

from app import db
from app.api import api
from app.models.user import User
from app.utils.validators import validate_email, validate_password
from app.utils.decorators import handle_api_errors

# In-memory blacklist for revoked tokens (in production, use Redis)
blacklisted_tokens = set()


@api.route('/auth/register', methods=['POST'])
@handle_api_errors
def register():
    """Register a new user"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['username', 'email', 'first_name', 'last_name', 'password']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'success': False,
                'message': f'{field.replace("_", " ").title()} is required'
            }), 400
    
    # Validate email format
    if not validate_email(data['email']):
        return jsonify({
            'success': False,
            'message': 'Invalid email format'
        }), 400
    
    # Validate password strength
    password_validation = validate_password(data['password'])
    if not password_validation['valid']:
        return jsonify({
            'success': False,
            'message': password_validation['message']
        }), 400
    
    # Check if user already exists
    existing_user = User.query.filter(
        or_(User.username == data['username'], User.email == data['email'])
    ).first()
    
    if existing_user:
        field = 'username' if existing_user.username == data['username'] else 'email'
        return jsonify({
            'success': False,
            'message': f'User with this {field} already exists'
        }), 409
    
    # Create new user
    try:
        user = User(
            username=data['username'],
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            password=data['password']
        )
        
        db.session.add(user)
        db.session.commit()
        
        # Generate tokens
        access_token = create_access_token(
            identity=user.id,
            additional_claims={'username': user.username, 'email': user.email}
        )
        refresh_token = create_refresh_token(identity=user.id)
        
        return jsonify({
            'success': True,
            'message': 'User registered successfully',
            'data': {
                'user': user.to_dict(),
                'access_token': access_token,
                'refresh_token': refresh_token
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Registration error: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Registration failed. Please try again.'
        }), 500


@api.route('/auth/login', methods=['POST'])
@handle_api_errors
def login():
    """Authenticate user and return JWT tokens"""
    data = request.get_json()
    
    # Validate required fields
    if not data.get('identifier') or not data.get('password'):
        return jsonify({
            'success': False,
            'message': 'Username/email and password are required'
        }), 400
    
    # Find user by username or email
    user = User.query.filter(
        or_(User.username == data['identifier'], User.email == data['identifier'])
    ).first()
    
    if not user or not user.check_password(data['password']):
        return jsonify({
            'success': False,
            'message': 'Invalid credentials'
        }), 401
    
    if not user.is_active:
        return jsonify({
            'success': False,
            'message': 'Account is deactivated. Please contact support.'
        }), 403
    
    # Generate tokens
    access_token = create_access_token(
        identity=user.id,
        additional_claims={'username': user.username, 'email': user.email}
    )
    refresh_token = create_refresh_token(identity=user.id)
    
    return jsonify({
        'success': True,
        'message': 'Login successful',
        'data': {
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }
    }), 200


@api.route('/auth/refresh', methods=['POST'])
@jwt_required(refresh=True)
@handle_api_errors
def refresh():
    """Refresh access token using refresh token"""
    current_user_id = get_jwt_identity()
    
    # Check if user still exists and is active
    user = User.query.get(current_user_id)
    if not user or not user.is_active:
        return jsonify({
            'success': False,
            'message': 'Invalid user or account deactivated'
        }), 401
    
    # Generate new access token
    new_access_token = create_access_token(
        identity=user.id,
        additional_claims={'username': user.username, 'email': user.email}
    )
    
    return jsonify({
        'success': True,
        'message': 'Token refreshed successfully',
        'data': {
            'access_token': new_access_token
        }
    }), 200


@api.route('/auth/logout', methods=['POST'])
@jwt_required()
@handle_api_errors
def logout():
    """Logout user and blacklist token"""
    jti = get_jwt()['jti']
    blacklisted_tokens.add(jti)
    
    return jsonify({
        'success': True,
        'message': 'Successfully logged out'
    }), 200


@api.route('/auth/profile', methods=['GET'])
@jwt_required()
@handle_api_errors
def get_profile():
    """Get current user's profile"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404
    
    return jsonify({
        'success': True,
        'message': 'Profile retrieved successfully',
        'data': {'user': user.to_dict()}
    }), 200


@api.route('/auth/profile', methods=['PUT'])
@jwt_required()
@handle_api_errors
def update_profile():
    """Update current user's profile"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404
    
    data = request.get_json()
    
    # Update allowed fields
    updatable_fields = ['first_name', 'last_name', 'email']
    updated = False
    
    for field in updatable_fields:
        if field in data and data[field] != getattr(user, field):
            # Special validation for email
            if field == 'email':
                if not validate_email(data[field]):
                    return jsonify({
                        'success': False,
                        'message': 'Invalid email format'
                    }), 400
                
                # Check if email already exists
                existing_user = User.query.filter(
                    User.email == data[field],
                    User.id != user.id
                ).first()
                
                if existing_user:
                    return jsonify({
                        'success': False,
                        'message': 'Email already in use'
                    }), 409
            
            setattr(user, field, data[field])
            updated = True
    
    # Update full_name if first_name or last_name changed
    if 'first_name' in data or 'last_name' in data:
        user.full_name = f"{user.first_name} {user.last_name}"
        updated = True
    
    if not updated:
        return jsonify({
            'success': True,
            'message': 'No changes made',
            'data': {'user': user.to_dict()}
        }), 200
    
    try:
        db.session.commit()
        return jsonify({
            'success': True,
            'message': 'Profile updated successfully',
            'data': {'user': user.to_dict()}
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Profile update error: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Failed to update profile'
        }), 500


@api.route('/auth/change-password', methods=['PUT'])
@jwt_required()
@handle_api_errors
def change_password():
    """Change user's password"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404
    
    data = request.get_json()
    
    # Validate required fields
    if not data.get('current_password') or not data.get('new_password'):
        return jsonify({
            'success': False,
            'message': 'Current password and new password are required'
        }), 400
    
    # Verify current password
    if not user.check_password(data['current_password']):
        return jsonify({
            'success': False,
            'message': 'Current password is incorrect'
        }), 400
    
    # Validate new password
    password_validation = validate_password(data['new_password'])
    if not password_validation['valid']:
        return jsonify({
            'success': False,
            'message': password_validation['message']
        }), 400
    
    # Check if new password is different from current
    if user.check_password(data['new_password']):
        return jsonify({
            'success': False,
            'message': 'New password must be different from current password'
        }), 400
    
    try:
        user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Password change error: {str(e)}')
        return jsonify({
            'success': False,
            'message': 'Failed to change password'
        }), 500


# JWT token blacklist checker
def check_if_token_revoked():
    """Check if JWT token is blacklisted"""
    if request.endpoint and 'auth' in request.endpoint:
        try:
            jwt_payload = get_jwt()
            jti = jwt_payload['jti']
            if jti in blacklisted_tokens:
                return jsonify({
                    'success': False,
                    'message': 'Token has been revoked'
                }), 401
        except:
            # No JWT token present or invalid, let other decorators handle it
            pass