from datetime import datetime
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_, desc, asc

from app import db
from app.api import api
from app.models.task import Task
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.category import Category, TaskCategory
from app.utils.decorators import handle_api_errors, require_active_user, paginate_query, validate_json_fields
from app.utils.validators import validate_task_status, validate_task_priority, validate_due_date
from app.utils.helpers import create_api_response, build_search_filters


@api.route('/tasks', methods=['POST'])
@require_active_user
@validate_json_fields(
    required_fields=['title', 'project_id'],
    optional_fields=['description', 'assigned_to', 'priority', 'due_date', 'category_ids']
)
@handle_api_errors
def create_task():
    """Create a new task"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Validate project exists and user has access
    project = Project.query.get(data['project_id'])
    if not project:
        return create_api_response(False, 'Project not found', None, 404)
    
    user = User.query.get(current_user_id)
    if not user.can_access_project(data['project_id']):
        return create_api_response(False, 'Access denied to project', None, 403)
    
    # Validate assigned user exists and has access to project
    if data.get('assigned_to'):
        assigned_user = User.query.get(data['assigned_to'])
        if not assigned_user:
            return create_api_response(False, 'Assigned user not found', None, 404)
        if not assigned_user.can_access_project(data['project_id']):
            return create_api_response(False, 'Assigned user does not have access to project', None, 400)
    
    # Validate priority
    priority = data.get('priority', 'medium')
    priority_validation = validate_task_priority(priority)
    if not priority_validation['valid']:
        return create_api_response(False, priority_validation['message'], None, 400)
    
    # Validate due date
    due_date_validation = validate_due_date(data.get('due_date'))
    if not due_date_validation['valid']:
        return create_api_response(False, due_date_validation['message'], None, 400)
    
    # Create task
    task = Task(
        title=data['title'].strip(),
        description=data.get('description', '').strip(),
        project_id=data['project_id'],
        created_by=current_user_id,
        assigned_to=data.get('assigned_to'),
        priority=priority,
        due_date=due_date_validation['date']
    )
    
    try:
        db.session.add(task)
        db.session.flush()  # Get task ID
        
        # Add categories if provided
        if data.get('category_ids'):
            for category_id in data['category_ids']:
                category = Category.query.filter_by(id=category_id, user_id=current_user_id).first()
                if category:
                    task.add_category(category_id)
        
        db.session.commit()
        
        return create_api_response(
            True,
            'Task created successfully',
            {'task': task.to_dict(include_categories=True)},
            201
        )
        
    except Exception as e:
        db.session.rollback()
        return create_api_response(False, 'Failed to create task', None, 500)


@api.route('/tasks', methods=['GET'])
@require_active_user
@paginate_query
@handle_api_errors
def get_tasks(page=1, per_page=20):
    """Get tasks with filtering and pagination"""
    current_user_id = get_jwt_identity()
    
    # Build query with user access restrictions
    query = db.session.query(Task).join(Project).filter(
        or_(
            Project.owner_id == current_user_id,
            Project.id.in_(
                db.session.query(Project.id)
                .join(ProjectMember)
                .filter(ProjectMember.user_id == current_user_id)
            )
        )
    )
    
    # Apply filters
    project_id = request.args.get('project_id', type=int)
    if project_id:
        query = query.filter(Task.project_id == project_id)
    
    status = request.args.get('status')
    if status:
        query = query.filter(Task.status == status)
    
    priority = request.args.get('priority')
    if priority:
        query = query.filter(Task.priority == priority)
    
    assigned_to = request.args.get('assigned_to', type=int)
    if assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)
    
    created_by = request.args.get('created_by', type=int)
    if created_by:
        query = query.filter(Task.created_by == created_by)
    
    # Search filter
    search = request.args.get('search')
    if search:
        search_filter = build_search_filters(search, [Task.title, Task.description])
        if search_filter is not None:
            query = query.filter(search_filter)
    
    # Date filters
    due_before = request.args.get('due_before')
    if due_before:
        try:
            due_date = datetime.fromisoformat(due_before.replace('Z', '+00:00'))
            query = query.filter(Task.due_date <= due_date)
        except ValueError:
            return create_api_response(False, 'Invalid due_before date format', None, 400)
    
    due_after = request.args.get('due_after')
    if due_after:
        try:
            due_date = datetime.fromisoformat(due_after.replace('Z', '+00:00'))
            query = query.filter(Task.due_date >= due_date)
        except ValueError:
            return create_api_response(False, 'Invalid due_after date format', None, 400)
    
    # Overdue filter
    overdue = request.args.get('overdue')
    if overdue and overdue.lower() == 'true':
        query = query.filter(
            and_(
                Task.due_date < datetime.utcnow(),
                Task.status.notin_(['completed', 'cancelled'])
            )
        )
    
    # Category filter
    category_id = request.args.get('category_id', type=int)
    if category_id:
        query = query.join(TaskCategory).filter(TaskCategory.category_id == category_id)
    
    # Sorting
    sort_by = request.args.get('sort_by', 'created_at')
    sort_order = request.args.get('sort_order', 'desc').lower()
    
    if sort_by == 'priority':
        # Custom priority sorting
        priority_order = db.case(
            (Task.priority == 'critical', 4),
            (Task.priority == 'high', 3),
            (Task.priority == 'medium', 2),
            (Task.priority == 'low', 1)
        )
        query = query.order_by(desc(priority_order) if sort_order == 'desc' else asc(priority_order))
    elif hasattr(Task, sort_by):
        sort_column = getattr(Task, sort_by)
        query = query.order_by(desc(sort_column) if sort_order == 'desc' else asc(sort_column))
    
    # Pagination
    tasks = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    include_details = request.args.get('include_details', 'false').lower() == 'true'
    
    return create_api_response(
        True,
        'Tasks retrieved successfully',
        {
            'tasks': [task.to_dict(
                include_categories=include_details,
                include_comments=False,
                include_attachments=False
            ) for task in tasks.items],
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


@api.route('/tasks/<int:task_id>', methods=['GET'])
@require_active_user
@handle_api_errors
def get_task(task_id):
    """Get a specific task"""
    current_user_id = get_jwt_identity()
    
    task = Task.query.get(task_id)
    if not task:
        return create_api_response(False, 'Task not found', None, 404)
    
    if not task.can_user_view(current_user_id):
        return create_api_response(False, 'Access denied', None, 403)
    
    include_comments = request.args.get('include_comments', 'false').lower() == 'true'
    include_attachments = request.args.get('include_attachments', 'false').lower() == 'true'
    
    return create_api_response(
        True,
        'Task retrieved successfully',
        {
            'task': task.to_dict(
                include_categories=True,
                include_comments=include_comments,
                include_attachments=include_attachments
            )
        }
    )


@api.route('/tasks/<int:task_id>', methods=['PUT'])
@require_active_user
@validate_json_fields(
    optional_fields=['title', 'description', 'status', 'priority', 'assigned_to', 'due_date', 'category_ids']
)
@handle_api_errors
def update_task(task_id):
    """Update a task"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    task = Task.query.get(task_id)
    if not task:
        return create_api_response(False, 'Task not found', None, 404)
    
    if not task.can_user_edit(current_user_id):
        return create_api_response(False, 'Permission denied', None, 403)
    
    updated = False
    
    # Update basic fields
    if 'title' in data and data['title'].strip() != task.title:
        task.title = data['title'].strip()
        updated = True
    
    if 'description' in data and data['description'] != task.description:
        task.description = data['description']
        updated = True
    
    # Validate and update status
    if 'status' in data:
        status_validation = validate_task_status(data['status'])
        if not status_validation['valid']:
            return create_api_response(False, status_validation['message'], None, 400)
        if data['status'] != task.status:
            task.update_status(data['status'])
            updated = True
    
    # Validate and update priority
    if 'priority' in data:
        priority_validation = validate_task_priority(data['priority'])
        if not priority_validation['valid']:
            return create_api_response(False, priority_validation['message'], None, 400)
        if data['priority'] != task.priority:
            task.priority = data['priority']
            updated = True
    
    # Update assigned user
    if 'assigned_to' in data:
        if data['assigned_to'] is not None:
            assigned_user = User.query.get(data['assigned_to'])
            if not assigned_user:
                return create_api_response(False, 'Assigned user not found', None, 404)
            if not assigned_user.can_access_project(task.project_id):
                return create_api_response(False, 'Assigned user does not have access to project', None, 400)
        
        if data['assigned_to'] != task.assigned_to:
            task.assigned_to = data['assigned_to']
            updated = True
    
    # Validate and update due date
    if 'due_date' in data:
        due_date_validation = validate_due_date(data['due_date'])
        if not due_date_validation['valid']:
            return create_api_response(False, due_date_validation['message'], None, 400)
        
        new_due_date = due_date_validation['date']
        if new_due_date != task.due_date:
            task.due_date = new_due_date
            updated = True
    
    # Update categories
    if 'category_ids' in data:
        # Remove existing categories
        existing_categories = TaskCategory.query.filter_by(task_id=task_id).all()
        for tc in existing_categories:
            db.session.delete(tc)
        
        # Add new categories
        if data['category_ids']:
            for category_id in data['category_ids']:
                category = Category.query.filter_by(id=category_id, user_id=current_user_id).first()
                if category:
                    task.add_category(category_id)
        
        updated = True
    
    if not updated:
        return create_api_response(True, 'No changes made', {'task': task.to_dict(include_categories=True)})
    
    try:
        if updated and 'category_ids' not in data:  # Categories are handled separately
            task.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return create_api_response(
            True,
            'Task updated successfully',
            {'task': task.to_dict(include_categories=True)}
        )
        
    except Exception as e:
        db.session.rollback()
        return create_api_response(False, 'Failed to update task', None, 500)


@api.route('/tasks/<int:task_id>', methods=['DELETE'])
@require_active_user
@handle_api_errors
def delete_task(task_id):
    """Delete a task"""
    current_user_id = get_jwt_identity()
    
    task = Task.query.get(task_id)
    if not task:
        return create_api_response(False, 'Task not found', None, 404)
    
    if not task.can_user_edit(current_user_id):
        return create_api_response(False, 'Permission denied', None, 403)
    
    try:
        db.session.delete(task)
        db.session.commit()
        
        return create_api_response(True, 'Task deleted successfully')
        
    except Exception as e:
        db.session.rollback()
        return create_api_response(False, 'Failed to delete task', None, 500)


@api.route('/tasks/<int:task_id>/assign', methods=['POST'])
@require_active_user
@validate_json_fields(required_fields=['user_id'])
@handle_api_errors
def assign_task(task_id):
    """Assign task to a user"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    task = Task.query.get(task_id)
    if not task:
        return create_api_response(False, 'Task not found', None, 404)
    
    if not task.can_user_edit(current_user_id):
        return create_api_response(False, 'Permission denied', None, 403)
    
    # Validate assigned user
    assigned_user = User.query.get(data['user_id'])
    if not assigned_user:
        return create_api_response(False, 'User not found', None, 404)
    
    if not assigned_user.can_access_project(task.project_id):
        return create_api_response(False, 'User does not have access to project', None, 400)
    
    try:
        task.assign_to_user(data['user_id'])
        db.session.commit()
        
        return create_api_response(
            True,
            'Task assigned successfully',
            {'task': task.to_dict()}
        )
        
    except Exception as e:
        db.session.rollback()
        return create_api_response(False, 'Failed to assign task', None, 500)


@api.route('/tasks/<int:task_id>/unassign', methods=['POST'])
@require_active_user
@handle_api_errors
def unassign_task(task_id):
    """Unassign task from current user"""
    current_user_id = get_jwt_identity()
    
    task = Task.query.get(task_id)
    if not task:
        return create_api_response(False, 'Task not found', None, 404)
    
    if not task.can_user_edit(current_user_id):
        return create_api_response(False, 'Permission denied', None, 403)
    
    try:
        task.unassign()
        db.session.commit()
        
        return create_api_response(
            True,
            'Task unassigned successfully',
            {'task': task.to_dict()}
        )
        
    except Exception as e:
        db.session.rollback()
        return create_api_response(False, 'Failed to unassign task', None, 500)


@api.route('/tasks/my', methods=['GET'])
@require_active_user
@paginate_query
@handle_api_errors
def get_my_tasks(page=1, per_page=20):
    """Get tasks assigned to current user"""
    current_user_id = get_jwt_identity()
    
    # Get tasks assigned to user or created by user
    query = Task.query.filter(
        or_(
            Task.assigned_to == current_user_id,
            Task.created_by == current_user_id
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
        'My tasks retrieved successfully',
        {
            'tasks': [task.to_dict(include_categories=True) for task in tasks.items],
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