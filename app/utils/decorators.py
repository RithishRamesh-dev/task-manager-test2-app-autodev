from functools import wraps
from flask import jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.user import User


def handle_api_errors(f):
    """Decorator to handle common API errors"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except ValueError as e:
            current_app.logger.warning(f'Validation error in {f.__name__}: {str(e)}')
            return jsonify({
                'success': False,
                'message': str(e)
            }), 400
        except Exception as e:
            current_app.logger.error(f'Unexpected error in {f.__name__}: {str(e)}')
            return jsonify({
                'success': False,
                'message': 'An unexpected error occurred'
            }), 500
    return decorated_function


def require_json(f):
    """Decorator to ensure request contains JSON data"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        if not request.is_json:
            return jsonify({
                'success': False,
                'message': 'Request must contain JSON data'
            }), 400
        return f(*args, **kwargs)
    return decorated_function


def require_active_user(f):
    """Decorator to ensure current user is active"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return jsonify({
                'success': False,
                'message': 'Account is deactivated or not found'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


def require_verified_user(f):
    """Decorator to ensure current user is verified"""
    @wraps(f)
    @jwt_required()
    def decorated_function(*args, **kwargs):
        current_user_id = get_jwt_identity()
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            }), 404
        
        if not user.is_active:
            return jsonify({
                'success': False,
                'message': 'Account is deactivated'
            }), 403
        
        if not user.is_verified:
            return jsonify({
                'success': False,
                'message': 'Account is not verified'
            }), 403
        
        return f(*args, **kwargs)
    return decorated_function


def validate_json_fields(required_fields=None, optional_fields=None):
    """Decorator to validate JSON fields in request"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask import request
            
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'message': 'Request must contain JSON data'
                }), 400
            
            data = request.get_json()
            
            # Check required fields
            if required_fields:
                for field in required_fields:
                    if field not in data or data[field] is None:
                        return jsonify({
                            'success': False,
                            'message': f'{field.replace("_", " ").title()} is required'
                        }), 400
            
            # Check for unexpected fields
            if optional_fields is not None:
                allowed_fields = set(required_fields or []) | set(optional_fields or [])
                unexpected_fields = set(data.keys()) - allowed_fields
                if unexpected_fields:
                    return jsonify({
                        'success': False,
                        'message': f"Unexpected fields: {', '.join(unexpected_fields)}"
                    }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def paginate_query(f):
    """Decorator to add pagination to query results"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        from flask import request
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)  # Max 100 items per page
        
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = 20
        
        # Add pagination info to kwargs
        kwargs['page'] = page
        kwargs['per_page'] = per_page
        
        return f(*args, **kwargs)
    return decorated_function