from datetime import datetime
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import and_, desc

from app import db
from app.api import api
from app.models.category import Category, TaskCategory
from app.models.task import Task
from app.utils.decorators import handle_api_errors, require_active_user, paginate_query, validate_json_fields
from app.utils.validators import validate_color_hex
from app.utils.helpers import create_api_response, build_search_filters


@api.route('/categories', methods=['POST'])
@require_active_user
@validate_json_fields(
    required_fields=['name'],
    optional_fields=['color']
)
@handle_api_errors
def create_category():
    """Create a new category"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate color if provided
    color = data.get('color', '#007bff')
    color_validation = validate_color_hex(color)
    if not color_validation['valid']:
        return create_api_response(False, color_validation['message'], None, 400)
    
    # Check if category with same name exists for user
    existing_category = Category.query.filter(
        and_(
            Category.name.ilike(data['name'].strip()),
            Category.user_id == current_user_id
        )
    ).first()
    
    if existing_category:
        return create_api_response(False, 'Category with this name already exists', None, 409)
    
    # Create category
    category = Category(
        name=data['name'].strip(),
        color=color,
        user_id=current_user_id
    )
    
    try:
        db.session.add(category)
        db.session.commit()
        
        return create_api_response(
            True,
            'Category created successfully',
            {'category': category.to_dict()},
            201
        )
        
    except Exception as e:
        db.session.rollback()
        return create_api_response(False, 'Failed to create category', None, 500)


@api.route('/categories', methods=['GET'])
@require_active_user
@paginate_query
@handle_api_errors
def get_categories(page=1, per_page=50):
    """Get user's categories"""
    current_user_id = get_jwt_identity()
    
    # Base query for user's categories
    query = Category.query.filter(Category.user_id == current_user_id)
    
    # Apply search filter if provided
    search = request.args.get('search')
    if search:
        search_filter = build_search_filters(search, [Category.name])
        if search_filter is not None:
            query = query.filter(search_filter)
    
    # Sort by name
    query = query.order_by(Category.name.asc())
    
    # Pagination
    categories = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    include_task_count = request.args.get('include_task_count', 'false').lower() == 'true'
    
    return create_api_response(
        True,
        'Categories retrieved successfully',
        {
            'categories': [category.to_dict(include_task_count=include_task_count) for category in categories.items],
            'pagination': {
                'page': categories.page,
                'per_page': categories.per_page,
                'total': categories.total,
                'pages': categories.pages,
                'has_next': categories.has_next,
                'has_prev': categories.has_prev
            }
        }
    )


@api.route('/categories/<int:category_id>', methods=['GET'])
@require_active_user
@handle_api_errors
def get_category(category_id):
    """Get a specific category"""
    current_user_id = get_jwt_identity()
    
    category = Category.query.filter(
        and_(Category.id == category_id, Category.user_id == current_user_id)
    ).first()
    
    if not category:
        return create_api_response(False, 'Category not found', None, 404)
    
    # Get tasks in this category
    tasks = category.get_tasks()
    
    category_data = category.to_dict(include_task_count=True)
    category_data['tasks'] = [{
        'id': task.id,
        'title': task.title,
        'status': task.status,
        'priority': task.priority,
        'project_id': task.project_id,
        'assigned_to': task.assigned_to,
        'due_date': task.due_date.isoformat() if task.due_date else None,
        'is_overdue': task.is_overdue()
    } for task in tasks]
    
    return create_api_response(
        True,
        'Category retrieved successfully',
        {'category': category_data}
    )


@api.route('/categories/<int:category_id>', methods=['PUT'])
@require_active_user
@validate_json_fields(
    optional_fields=['name', 'color']
)
@handle_api_errors
def update_category(category_id):
    """Update a category"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    category = Category.query.filter(
        and_(Category.id == category_id, Category.user_id == current_user_id)
    ).first()
    
    if not category:
        return create_api_response(False, 'Category not found', None, 404)
    
    updated = False
    
    # Update name
    if 'name' in data and data['name'].strip() != category.name:
        # Check if another category with same name exists
        existing_category = Category.query.filter(
            and_(
                Category.name.ilike(data['name'].strip()),
                Category.user_id == current_user_id,
                Category.id != category_id
            )
        ).first()
        
        if existing_category:
            return create_api_response(False, 'Category with this name already exists', None, 409)
        
        category.name = data['name'].strip()
        updated = True
    
    # Update color
    if 'color' in data and data['color'] != category.color:
        color_validation = validate_color_hex(data['color'])
        if not color_validation['valid']:
            return create_api_response(False, color_validation['message'], None, 400)
        
        category.color = data['color']
        updated = True
    
    if not updated:
        return create_api_response(True, 'No changes made', {'category': category.to_dict()})
    
    try:
        category.updated_at = datetime.utcnow()
        db.session.commit()
        
        return create_api_response(
            True,
            'Category updated successfully',
            {'category': category.to_dict()}
        )
        
    except Exception as e:
        db.session.rollback()
        return create_api_response(False, 'Failed to update category', None, 500)


@api.route('/categories/<int:category_id>', methods=['DELETE'])
@require_active_user
@handle_api_errors
def delete_category(category_id):
    """Delete a category"""
    current_user_id = get_jwt_identity()
    
    category = Category.query.filter(
        and_(Category.id == category_id, Category.user_id == current_user_id)
    ).first()
    
    if not category:
        return create_api_response(False, 'Category not found', None, 404)
    
    # Check if category has tasks
    task_count = category.get_tasks_count()
    force_delete = request.args.get('force', 'false').lower() == 'true'
    
    if task_count > 0 and not force_delete:
        return create_api_response(
            False,
            f'Category has {task_count} tasks. Use ?force=true to delete anyway.',
            None,
            400
        )
    
    try:
        db.session.delete(category)
        db.session.commit()
        
        return create_api_response(True, 'Category deleted successfully')
        
    except Exception as e:
        db.session.rollback()
        return create_api_response(False, 'Failed to delete category', None, 500)


@api.route('/categories/<int:category_id>/tasks', methods=['GET'])
@require_active_user
@paginate_query
@handle_api_errors
def get_category_tasks(category_id, page=1, per_page=20):
    """Get tasks in a specific category"""
    current_user_id = get_jwt_identity()
    
    category = Category.query.filter(
        and_(Category.id == category_id, Category.user_id == current_user_id)
    ).first()
    
    if not category:
        return create_api_response(False, 'Category not found', None, 404)
    
    # Get tasks in this category with user access control
    query = db.session.query(Task).join(TaskCategory).join(Project).filter(
        and_(
            TaskCategory.category_id == category_id,
            or_(
                Project.owner_id == current_user_id,
                Task.assigned_to == current_user_id,
                Task.created_by == current_user_id
            )
        )
    )
    
    # Apply status filter if provided
    status = request.args.get('status')
    if status:
        query = query.filter(Task.status == status)
    
    # Apply priority filter if provided
    priority = request.args.get('priority')
    if priority:
        query = query.filter(Task.priority == priority)
    
    # Sort by priority and creation date
    priority_order = db.case(
        (Task.priority == 'critical', 4),
        (Task.priority == 'high', 3),
        (Task.priority == 'medium', 2),
        (Task.priority == 'low', 1)
    )
    query = query.order_by(desc(priority_order), desc(Task.created_at))
    
    # Pagination
    tasks = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return create_api_response(
        True,
        'Category tasks retrieved successfully',
        {
            'category': category.to_dict(),
            'tasks': [task.to_dict() for task in tasks.items],
            'pagination': {
                'page': tasks.page,
                'per_page': tasks.per_page,
                'total': tasks.total,
                'pages': tasks.pages,
                'has_next': tasks.has_next,
                'has_prev': tasks.has_prev
            }
        }
    )


@api.route('/categories/stats', methods=['GET'])
@require_active_user
@handle_api_errors
def get_category_stats():
    """Get category statistics"""
    current_user_id = get_jwt_identity()
    
    # Get all user categories with task counts
    categories = Category.query.filter(Category.user_id == current_user_id).all()
    
    stats = []
    total_tasks = 0
    
    for category in categories:
        task_count = category.get_tasks_count()
        total_tasks += task_count
        
        # Get task status breakdown for this category
        status_counts = db.session.query(
            Task.status,
            db.func.count(Task.id)
        ).join(TaskCategory).filter(
            TaskCategory.category_id == category.id
        ).group_by(Task.status).all()
        
        status_breakdown = {status: count for status, count in status_counts}
        
        stats.append({
            'category': category.to_dict(),
            'task_count': task_count,
            'status_breakdown': status_breakdown
        })
    
    # Sort by task count (descending)
    stats.sort(key=lambda x: x['task_count'], reverse=True)
    
    return create_api_response(
        True,
        'Category statistics retrieved successfully',
        {
            'total_categories': len(categories),
            'total_tasks': total_tasks,
            'category_stats': stats
        }
    )