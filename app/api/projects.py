from datetime import datetime
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_, desc

from app import db
from app.api import api
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.user import User
from app.models.task import Task
from app.utils.decorators import handle_api_errors, require_active_user, paginate_query, validate_json_fields
from app.utils.helpers import create_api_response, build_search_filters


@api.route('/projects', methods=['POST'])
@jwt_required()
@require_active_user
@validate_json_fields(
    required_fields=['name'],
    optional_fields=['description']
)
@handle_api_errors
def create_project():
    """Create a new project"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    # Check if project with same name exists for user
    existing_project = Project.query.filter(
        and_(
            Project.name.ilike(data['name'].strip()),
            Project.owner_id == current_user_id
        )
    ).first()
    
    if existing_project:
        return create_api_response(False, 'Project with this name already exists', None, 409)
    
    # Create project
    project = Project(
        name=data['name'].strip(),
        description=data.get('description', '').strip(),
        owner_id=current_user_id
    )
    
    try:
        db.session.add(project)
        db.session.commit()
        
        return create_api_response(
            True,
            'Project created successfully',
            {'project': project.to_dict()},
            201
        )
        
    except Exception as e:
        db.session.rollback()
        return create_api_response(False, 'Failed to create project', None, 500)


@api.route('/projects', methods=['GET'])
@jwt_required()
@require_active_user
@paginate_query
@handle_api_errors
def get_projects(page=1, per_page=20):
    """Get user's projects with pagination"""
    current_user_id = get_jwt_identity()
    user = User.query.get(current_user_id)
    
    # Base query for projects user has access to
    owned_projects = db.session.query(Project).filter(Project.owner_id == current_user_id)
    member_projects = db.session.query(Project).join(ProjectMember).filter(
        ProjectMember.user_id == current_user_id
    )
    
    # Combine queries
    query = owned_projects.union(member_projects)
    
    # Apply search filter if provided
    search = request.args.get('search')
    if search:
        search_filter = build_search_filters(search, [Project.name, Project.description])
        if search_filter is not None:
            query = query.filter(search_filter)
    
    # Apply status filter if provided
    status = request.args.get('status')
    if status:
        query = query.filter(Project.status == status)
    
    # Sort by creation date (newest first)
    query = query.order_by(desc(Project.created_at))
    
    # Pagination
    projects = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    include_stats = request.args.get('include_stats', 'false').lower() == 'true'
    project_list = []
    
    for project in projects.items:
        project_data = project.to_dict()
        
        if include_stats:
            # Add project statistics
            total_tasks = Task.query.filter_by(project_id=project.id).count()
            completed_tasks = Task.query.filter_by(project_id=project.id, status='completed').count()
            
            project_data.update({
                'task_stats': {
                    'total': total_tasks,
                    'completed': completed_tasks,
                    'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
                }
            })
        
        project_list.append(project_data)
    
    return create_api_response(
        True,
        'Projects retrieved successfully',
        {
            'projects': project_list,
            'pagination': {
                'page': projects.page,
                'per_page': projects.per_page,
                'total': projects.total,
                'pages': projects.pages,
                'has_next': projects.has_next,
                'has_prev': projects.has_prev
            }
        }
    )


@api.route('/projects/<int:project_id>', methods=['GET'])
@jwt_required()
@require_active_user
@handle_api_errors
def get_project(project_id):
    """Get a specific project"""
    current_user_id = get_jwt_identity()
    
    project = Project.query.get(project_id)
    if not project:
        return create_api_response(False, 'Project not found', None, 404)
    
    user = User.query.get(current_user_id)
    if not user.can_access_project(project_id):
        return create_api_response(False, 'Access denied', None, 403)
    
    # Get project details with statistics
    project_data = project.to_dict()
    
    # Add member information if user is owner or member
    if project.owner_id == current_user_id or user.can_access_project(project_id):
        members = db.session.query(User).join(ProjectMember).filter(
            ProjectMember.project_id == project_id
        ).all()
        
        project_data['members'] = [{
            'id': member.id,
            'username': member.username,
            'full_name': member.full_name,
            'email': member.email
        } for member in members]
        
        # Add owner information
        owner = User.query.get(project.owner_id)
        project_data['owner'] = {
            'id': owner.id,
            'username': owner.username,
            'full_name': owner.full_name,
            'email': owner.email
        }
    
    # Add task statistics
    total_tasks = Task.query.filter_by(project_id=project_id).count()
    completed_tasks = Task.query.filter_by(project_id=project_id, status='completed').count()
    in_progress_tasks = Task.query.filter_by(project_id=project_id, status='in_progress').count()
    pending_tasks = Task.query.filter_by(project_id=project_id, status='pending').count()
    
    project_data['task_stats'] = {
        'total': total_tasks,
        'completed': completed_tasks,
        'in_progress': in_progress_tasks,
        'pending': pending_tasks,
        'completion_rate': (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0
    }
    
    return create_api_response(
        True,
        'Project retrieved successfully',
        {'project': project_data}
    )


@api.route('/projects/<int:project_id>', methods=['PUT'])
@jwt_required()
@require_active_user
@validate_json_fields(
    optional_fields=['name', 'description', 'status']
)
@handle_api_errors
def update_project(project_id):
    """Update a project (only owner can update)"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    project = Project.query.get(project_id)
    if not project:
        return create_api_response(False, 'Project not found', None, 404)
    
    if project.owner_id != current_user_id:
        return create_api_response(False, 'Only project owner can update project', None, 403)
    
    updated = False
    
    # Update name
    if 'name' in data and data['name'].strip() != project.name:
        # Check if another project with same name exists
        existing_project = Project.query.filter(
            and_(
                Project.name.ilike(data['name'].strip()),
                Project.owner_id == current_user_id,
                Project.id != project_id
            )
        ).first()
        
        if existing_project:
            return create_api_response(False, 'Project with this name already exists', None, 409)
        
        project.name = data['name'].strip()
        updated = True
    
    # Update description
    if 'description' in data and data['description'] != project.description:
        project.description = data['description']
        updated = True
    
    # Update status
    if 'status' in data:
        valid_statuses = ['active', 'inactive', 'completed', 'archived']
        if data['status'] not in valid_statuses:
            return create_api_response(False, f"Status must be one of: {', '.join(valid_statuses)}", None, 400)
        
        if data['status'] != project.status:
            project.status = data['status']
            updated = True
    
    if not updated:
        return create_api_response(True, 'No changes made', {'project': project.to_dict()})
    
    try:
        project.updated_at = datetime.utcnow()
        db.session.commit()
        
        return create_api_response(
            True,
            'Project updated successfully',
            {'project': project.to_dict()}
        )
        
    except Exception as e:
        db.session.rollback()
        return create_api_response(False, 'Failed to update project', None, 500)


@api.route('/projects/<int:project_id>', methods=['DELETE'])
@jwt_required()
@require_active_user
@handle_api_errors
def delete_project(project_id):
    """Delete a project (only owner can delete)"""
    current_user_id = get_jwt_identity()
    
    project = Project.query.get(project_id)
    if not project:
        return create_api_response(False, 'Project not found', None, 404)
    
    if project.owner_id != current_user_id:
        return create_api_response(False, 'Only project owner can delete project', None, 403)
    
    # Check if project has tasks
    task_count = Task.query.filter_by(project_id=project_id).count()
    force_delete = request.args.get('force', 'false').lower() == 'true'
    
    if task_count > 0 and not force_delete:
        return create_api_response(
            False,
            f'Project has {task_count} tasks. Use ?force=true to delete anyway.',
            None,
            400
        )
    
    try:
        db.session.delete(project)
        db.session.commit()
        
        return create_api_response(True, 'Project deleted successfully')
        
    except Exception as e:
        db.session.rollback()
        return create_api_response(False, 'Failed to delete project', None, 500)


@api.route('/projects/<int:project_id>/members', methods=['POST'])
@jwt_required()
@require_active_user
@validate_json_fields(required_fields=['user_id'])
@handle_api_errors
def add_project_member(project_id):
    """Add member to project (only owner can add members)"""
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    project = Project.query.get(project_id)
    if not project:
        return create_api_response(False, 'Project not found', None, 404)
    
    if project.owner_id != current_user_id:
        return create_api_response(False, 'Only project owner can add members', None, 403)
    
    # Check if user exists
    user = User.query.get(data['user_id'])
    if not user:
        return create_api_response(False, 'User not found', None, 404)
    
    # Check if user is already a member
    existing_member = ProjectMember.query.filter_by(
        project_id=project_id,
        user_id=data['user_id']
    ).first()
    
    if existing_member:
        return create_api_response(False, 'User is already a project member', None, 409)
    
    # Don't add owner as member
    if data['user_id'] == project.owner_id:
        return create_api_response(False, 'Project owner cannot be added as member', None, 400)
    
    try:
        member = ProjectMember(project_id=project_id, user_id=data['user_id'])
        db.session.add(member)
        db.session.commit()
        
        return create_api_response(
            True,
            'Member added successfully',
            {'member': {
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'email': user.email
            }},
            201
        )
        
    except Exception as e:
        db.session.rollback()
        return create_api_response(False, 'Failed to add member', None, 500)


@api.route('/projects/<int:project_id>/members/<int:user_id>', methods=['DELETE'])
@jwt_required()
@require_active_user
@handle_api_errors
def remove_project_member(project_id, user_id):
    """Remove member from project (only owner can remove members)"""
    current_user_id = get_jwt_identity()
    
    project = Project.query.get(project_id)
    if not project:
        return create_api_response(False, 'Project not found', None, 404)
    
    if project.owner_id != current_user_id:
        return create_api_response(False, 'Only project owner can remove members', None, 403)
    
    # Find and remove membership
    member = ProjectMember.query.filter_by(
        project_id=project_id,
        user_id=user_id
    ).first()
    
    if not member:
        return create_api_response(False, 'User is not a project member', None, 404)
    
    try:
        db.session.delete(member)
        db.session.commit()
        
        return create_api_response(True, 'Member removed successfully')
        
    except Exception as e:
        db.session.rollback()
        return create_api_response(False, 'Failed to remove member', None, 500)


@api.route('/projects/<int:project_id>/members', methods=['GET'])
@jwt_required()
@require_active_user
@handle_api_errors
def get_project_members(project_id):
    """Get project members"""
    current_user_id = get_jwt_identity()
    
    project = Project.query.get(project_id)
    if not project:
        return create_api_response(False, 'Project not found', None, 404)
    
    user = User.query.get(current_user_id)
    if not user.can_access_project(project_id):
        return create_api_response(False, 'Access denied', None, 403)
    
    # Get all members
    members = db.session.query(User).join(ProjectMember).filter(
        ProjectMember.project_id == project_id
    ).all()
    
    # Get owner
    owner = User.query.get(project.owner_id)
    
    return create_api_response(
        True,
        'Project members retrieved successfully',
        {
            'owner': {
                'id': owner.id,
                'username': owner.username,
                'full_name': owner.full_name,
                'email': owner.email
            },
            'members': [{
                'id': member.id,
                'username': member.username,
                'full_name': member.full_name,
                'email': member.email
            } for member in members]
        }
    )