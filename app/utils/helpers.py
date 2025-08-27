import os
import secrets
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app


def generate_unique_filename(original_filename):
    """Generate a unique filename while preserving the extension"""
    if not original_filename:
        return str(uuid.uuid4())
    
    # Secure the filename
    filename = secure_filename(original_filename)
    
    # Get file extension
    name, ext = os.path.splitext(filename)
    
    # Generate unique filename
    unique_id = str(uuid.uuid4())
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    
    return f"{timestamp}_{unique_id}{ext}"


def allowed_file(filename, allowed_extensions=None):
    """Check if file extension is allowed"""
    if allowed_extensions is None:
        allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', {
            'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'
        })
    
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions


def get_file_size_formatted(size_bytes):
    """Convert bytes to human readable format"""
    if size_bytes == 0:
        return '0 B'
    
    size_names = ['B', 'KB', 'MB', 'GB', 'TB']
    i = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and i < len(size_names) - 1:
        size /= 1024.0
        i += 1
    
    return f"{size:.1f} {size_names[i]}"


def create_api_response(success=True, message='', data=None, status_code=200):
    """Create standardized API response"""
    response = {
        'success': success,
        'message': message
    }
    
    if data is not None:
        response['data'] = data
    
    return response, status_code


def parse_date_range(start_date_str, end_date_str):
    """Parse date range strings to datetime objects"""
    start_date = None
    end_date = None
    
    try:
        if start_date_str:
            start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
        
        if end_date_str:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            # Set end date to end of day if no time specified
            if end_date.time() == datetime.min.time():
                end_date = end_date.replace(hour=23, minute=59, second=59)
        
    except ValueError as e:
        raise ValueError(f'Invalid date format: {str(e)}')
    
    # Validate date range
    if start_date and end_date and start_date > end_date:
        raise ValueError('Start date cannot be after end date')
    
    return start_date, end_date


def get_user_timezone():
    """Get user timezone (placeholder for future implementation)"""
    # For now, return UTC. In the future, this could be based on user preferences
    return 'UTC'


def format_datetime_for_user(dt, timezone='UTC'):
    """Format datetime for user display"""
    if not dt:
        return None
    
    # For now, return ISO format. In the future, format based on user preferences
    return dt.isoformat()


def generate_api_key():
    """Generate a secure API key"""
    return secrets.token_urlsafe(32)


def mask_email(email):
    """Mask email address for privacy"""
    if not email or '@' not in email:
        return email
    
    username, domain = email.split('@', 1)
    
    if len(username) <= 2:
        masked_username = username[0] + '*'
    else:
        masked_username = username[0] + '*' * (len(username) - 2) + username[-1]
    
    return f"{masked_username}@{domain}"


def calculate_task_completion_rate(tasks):
    """Calculate completion rate for a list of tasks"""
    if not tasks:
        return 0.0
    
    completed_tasks = sum(1 for task in tasks if task.status == 'completed')
    return (completed_tasks / len(tasks)) * 100


def get_priority_weight(priority):
    """Get numeric weight for priority sorting"""
    priority_weights = {
        'critical': 4,
        'high': 3,
        'medium': 2,
        'low': 1
    }
    return priority_weights.get(priority, 2)


def sanitize_search_query(query):
    """Sanitize search query to prevent SQL injection"""
    if not query:
        return ''
    
    # Remove potentially dangerous characters
    dangerous_chars = ['%', '_', ';', '--', '/*', '*/', 'xp_', 'sp_']
    
    sanitized = str(query).strip()
    
    for char in dangerous_chars:
        sanitized = sanitized.replace(char, '')
    
    return sanitized[:100]  # Limit length


def build_search_filters(query, fields):
    """Build search filters for multiple fields"""
    from sqlalchemy import or_, and_
    
    if not query or not fields:
        return None
    
    sanitized_query = sanitize_search_query(query)
    if not sanitized_query:
        return None
    
    search_term = f"%{sanitized_query}%"
    filters = []
    
    for field in fields:
        if hasattr(field, 'ilike'):
            filters.append(field.ilike(search_term))
    
    return or_(*filters) if filters else None