import re
from datetime import datetime


def validate_email(email):
    """Validate email format using regex"""
    if not email:
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """Validate password strength"""
    if not password:
        return {'valid': False, 'message': 'Password is required'}
    
    if len(password) < 8:
        return {'valid': False, 'message': 'Password must be at least 8 characters long'}
    
    if len(password) > 128:
        return {'valid': False, 'message': 'Password must be less than 128 characters'}
    
    # Check for at least one letter and one number
    if not re.search(r'[a-zA-Z]', password):
        return {'valid': False, 'message': 'Password must contain at least one letter'}
    
    if not re.search(r'\d', password):
        return {'valid': False, 'message': 'Password must contain at least one number'}
    
    return {'valid': True, 'message': 'Password is valid'}


def validate_username(username):
    """Validate username format"""
    if not username:
        return {'valid': False, 'message': 'Username is required'}
    
    if len(username) < 3:
        return {'valid': False, 'message': 'Username must be at least 3 characters long'}
    
    if len(username) > 80:
        return {'valid': False, 'message': 'Username must be less than 80 characters'}
    
    # Only alphanumeric characters, underscores, and hyphens
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        return {'valid': False, 'message': 'Username can only contain letters, numbers, underscores, and hyphens'}
    
    return {'valid': True, 'message': 'Username is valid'}


def validate_name(name, field_name='Name'):
    """Validate first name or last name"""
    if not name:
        return {'valid': False, 'message': f'{field_name} is required'}
    
    if len(name) < 1:
        return {'valid': False, 'message': f'{field_name} cannot be empty'}
    
    if len(name) > 100:
        return {'valid': False, 'message': f'{field_name} must be less than 100 characters'}
    
    # Only letters, spaces, hyphens, and apostrophes
    if not re.match(r'^[a-zA-Z\s\'-]+$', name):
        return {'valid': False, 'message': f'{field_name} can only contain letters, spaces, hyphens, and apostrophes'}
    
    return {'valid': True, 'message': f'{field_name} is valid'}


def validate_task_status(status):
    """Validate task status"""
    valid_statuses = ['pending', 'in_progress', 'completed', 'cancelled']
    if status not in valid_statuses:
        return {'valid': False, 'message': f"Status must be one of: {', '.join(valid_statuses)}"}
    return {'valid': True, 'message': 'Status is valid'}


def validate_task_priority(priority):
    """Validate task priority"""
    valid_priorities = ['low', 'medium', 'high', 'critical']
    if priority not in valid_priorities:
        return {'valid': False, 'message': f'Priority must be one of: {', '.join(valid_priorities)}'}
    return {'valid': True, 'message': 'Priority is valid'}


def validate_due_date(due_date_str):
    """Validate and parse due date"""
    if not due_date_str:
        return {'valid': True, 'date': None, 'message': 'Due date is optional'}
    
    try:
        # Try to parse ISO format
        due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
        
        # Check if date is in the past (allowing same day)
        if due_date.date() < datetime.utcnow().date():
            return {'valid': False, 'date': None, 'message': 'Due date cannot be in the past'}
        
        return {'valid': True, 'date': due_date, 'message': 'Due date is valid'}
        
    except ValueError:
        return {'valid': False, 'date': None, 'message': 'Invalid due date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)'}


def validate_color_hex(color):
    """Validate hex color code"""
    if not color:
        return {'valid': False, 'message': 'Color is required'}
    
    # Check if it's a valid hex color
    if not re.match(r'^#[0-9A-Fa-f]{6}$', color):
        return {'valid': False, 'message': 'Color must be a valid hex code (e.g., #FF5733)'}
    
    return {'valid': True, 'message': 'Color is valid'}


def validate_file_size(file_size, max_size_mb=16):
    """Validate file size"""
    max_size_bytes = max_size_mb * 1024 * 1024
    
    if file_size > max_size_bytes:
        return {'valid': False, 'message': f'File size must be less than {max_size_mb}MB'}
    
    return {'valid': True, 'message': 'File size is valid'}


def validate_mime_type(mime_type, allowed_types=None):
    """Validate MIME type"""
    if allowed_types is None:
        allowed_types = [
            'text/plain', 'text/csv',
            'application/pdf', 'application/msword',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.ms-excel',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'
        ]
    
    if mime_type not in allowed_types:
        return {'valid': False, 'message': 'File type not allowed'}
    
    return {'valid': True, 'message': 'File type is valid'}