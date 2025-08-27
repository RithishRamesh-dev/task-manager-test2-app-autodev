from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from sqlalchemy import or_, and_, desc

from app import db
from app.api import api
from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.task import Task
from app.utils.decorators import handle_api_errors, require_active_user, paginate_query
from app.utils.helpers import create_api_response, build_search_filters, mask_email


@api.route('/users/search', methods=['GET'])
@jwt_required()
@require_active_user
@paginate_query
@handle_api_errors
def search_users(page=1, per_page=20):
    """Search for users (for adding to projects)"""
    current_user_id = get_jwt_identity()
    
    # Get search query
    search = request.args.get('q', '').strip()
    if not search:
        return create_api_response(False, 'Search query is required', None, 400)
    
    # Search in username, first_name, last_name, email
    query = User.query.filter(
        and_(
            User.is_active == True,
            User.id != current_user_id,  # Exclude current user
            or_(
                User.username.ilike(f'%{search}%'),
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    )
    
    # Exclude users already in specific project if project_id provided
    exclude_project_id = request.args.get('exclude_project_id', type=int)
    if exclude_project_id:
        # Get existing member IDs
        existing_member_ids = db.session.query(ProjectMember.user_id).filter_by(
            project_id=exclude_project_id
        ).subquery()
        
        # Get project owner ID
        project = Project.query.get(exclude_project_id)
        exclude_ids = [project.owner_id] if project else []
        
        # Add existing members to exclude list
        query = query.filter(
            and_(
                User.id.notin_(existing_member_ids),
                User.id.notin_(exclude_ids)
            )
        )
    
    # Sort by username
    query = query.order_by(User.username.asc())
    
    # Pagination
    users = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    return create_api_response(
        True,
        'Users found',
        {
            'users': [{
                'id': user.id,
                'username': user.username,
                'full_name': user.full_name,
                'email': mask_email(user.email)  # Mask email for privacy
            } for user in users.items],
            'pagination': {
                'page': users.page,
                'per_page': users.per_page,
                'total': users.total,
                'pages': users.pages,
                'has_next': users.has_next,
                'has_prev': users.has_prev
            }
        }
    )


@api.route('/users/<int:user_id>', methods=['GET'])
@jwt_required()
@require_active_user
@handle_api_errors
def get_user_profile(user_id):
    """Get user profile (limited information for privacy)"""
    current_user_id = get_jwt_identity()
    
    user = User.query.get(user_id)
    if not user or not user.is_active:
        return create_api_response(False, 'User not found', None, 404)
    
    # Check if current user can view this profile
    # Users can view profiles of people they collaborate with
    can_view = False
    
    if user_id == current_user_id:
        can_view = True
    else:
        # Check if they share any projects
        shared_projects = db.session.query(Project.id).filter(
            or_(
                # Projects owned by current user where target user is member
                and_(
                    Project.owner_id == current_user_id,
                    Project.id.in_(
                        db.session.query(ProjectMember.project_id)
                        .filter_by(user_id=user_id)
                    )
                ),
                # Projects owned by target user where current user is member
                and_(
                    Project.owner_id == user_id,
                    Project.id.in_(
                        db.session.query(ProjectMember.project_id)
                        .filter_by(user_id=current_user_id)
                    )
                ),
                # Projects where both are members
                Project.id.in_(
                    db.session.query(ProjectMember.project_id)
                    .filter_by(user_id=current_user_id)
                    .intersect(
                        db.session.query(ProjectMember.project_id)
                        .filter_by(user_id=user_id)
                    )
                )
            )
        ).first()
        
        can_view = shared_projects is not None
    
    if not can_view:
        # Return limited public profile
        return create_api_response(
            True,
            'User profile retrieved',
            {
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'full_name': user.full_name
                }
            }
        )
    
    # Return fuller profile for collaborators
    profile_data = {
        'id': user.id,
        'username': user.username,
        'full_name': user.full_name,
        'created_at': user.created_at.isoformat()
    }
    
    # Add email for current user only
    if user_id == current_user_id:
        profile_data['email'] = user.email
        profile_data['first_name'] = user.first_name
        profile_data['last_name'] = user.last_name
        profile_data['is_verified'] = user.is_verified
        profile_data['updated_at'] = user.updated_at.isoformat()
    else:
        profile_data['email'] = mask_email(user.email)
    
    return create_api_response(
        True,
        'User profile retrieved',
        {'user': profile_data}
    )


@api.route('/users/<int:user_id>/stats', methods=['GET'])
@jwt_required()
@require_active_user
@handle_api_errors
def get_user_stats(user_id):
    """Get user statistics (only for current user or collaborators)"""
    current_user_id = get_jwt_identity()
    
    if user_id != current_user_id:
        return create_api_response(False, 'Access denied', None, 403)
    
    user = User.query.get(user_id)
    if not user or not user.is_active:
        return create_api_response(False, 'User not found', None, 404)
    
    # Get task statistics
    total_tasks_assigned = Task.query.filter_by(assigned_to=user_id).count()
    total_tasks_created = Task.query.filter_by(created_by=user_id).count()
    
    completed_tasks_assigned = Task.query.filter_by(
        assigned_to=user_id,
        status='completed'
    ).count()
    
    completed_tasks_created = Task.query.filter_by(
        created_by=user_id,
        status='completed'
    ).count()
    
    in_progress_tasks = Task.query.filter_by(
        assigned_to=user_id,
        status='in_progress'
    ).count()
    
    pending_tasks = Task.query.filter_by(
        assigned_to=user_id,
        status='pending'
    ).count()
    
    # Get overdue tasks
    overdue_tasks = Task.query.filter(
        and_(
            Task.assigned_to == user_id,
            Task.due_date < db.func.now(),
            Task.status.notin_(['completed', 'cancelled'])
        )
    ).count()
    
    # Get project statistics
    owned_projects = Project.query.filter_by(owner_id=user_id).count()
    member_projects = db.session.query(Project).join(ProjectMember).filter(
        ProjectMember.user_id == user_id
    ).count()
    
    return create_api_response(
        True,
        'User statistics retrieved',
        {
            'user_id': user_id,
            'task_stats': {
                'assigned': {
                    'total': total_tasks_assigned,
                    'completed': completed_tasks_assigned,
                    'in_progress': in_progress_tasks,
                    'pending': pending_tasks,
                    'overdue': overdue_tasks,
                    'completion_rate': (completed_tasks_assigned / total_tasks_assigned * 100) if total_tasks_assigned > 0 else 0
                },
                'created': {
                    'total': total_tasks_created,
                    'completed': completed_tasks_created,
                    'completion_rate': (completed_tasks_created / total_tasks_created * 100) if total_tasks_created > 0 else 0
                }
            },
            'project_stats': {
                'owned': owned_projects,
                'member_of': member_projects,
                'total_access': owned_projects + member_projects
            }
        }
    )


@api.route('/users/me/dashboard', methods=['GET'])
@jwt_required()
@require_active_user
@handle_api_errors
def get_dashboard_data():
    """Get dashboard data for current user"""
    current_user_id = get_jwt_identity()
    
    # Get recent tasks assigned to user
    recent_tasks = Task.query.filter(
        Task.assigned_to == current_user_id
    ).order_by(desc(Task.updated_at)).limit(5).all()
    
    # Get overdue tasks
    overdue_tasks = Task.query.filter(
        and_(
            Task.assigned_to == current_user_id,
            Task.due_date < db.func.now(),
            Task.status.notin_(['completed', 'cancelled'])
        )
    ).order_by(Task.due_date.asc()).limit(5).all()
    
    # Get upcoming tasks (due in next 7 days)
    from datetime import datetime, timedelta
    upcoming_date = datetime.utcnow() + timedelta(days=7)
    
    upcoming_tasks = Task.query.filter(
        and_(
            Task.assigned_to == current_user_id,
            Task.due_date <= upcoming_date,
            Task.due_date >= datetime.utcnow(),
            Task.status.notin_(['completed', 'cancelled'])
        )
    ).order_by(Task.due_date.asc()).limit(5).all()
    
    # Get recent projects
    recent_projects_owned = Project.query.filter_by(
        owner_id=current_user_id
    ).order_by(desc(Project.updated_at)).limit(3).all()
    
    recent_projects_member = db.session.query(Project).join(ProjectMember).filter(
        ProjectMember.user_id == current_user_id
    ).order_by(desc(Project.updated_at)).limit(3).all()
    
    # Combine and limit projects
    all_recent_projects = list(set(recent_projects_owned + recent_projects_member))
    all_recent_projects.sort(key=lambda p: p.updated_at, reverse=True)
    recent_projects = all_recent_projects[:5]
    
    return create_api_response(
        True,
        'Dashboard data retrieved',
        {
            'recent_tasks': [task.to_dict() for task in recent_tasks],
            'overdue_tasks': [task.to_dict() for task in overdue_tasks],
            'upcoming_tasks': [task.to_dict() for task in upcoming_tasks],
            'recent_projects': [project.to_dict() for project in recent_projects],
            'quick_stats': {
                'overdue_count': len(overdue_tasks),
                'upcoming_count': len(upcoming_tasks),
                'total_assigned_tasks': Task.query.filter_by(assigned_to=current_user_id).count(),
                'total_projects': len(all_recent_projects)
            }
        }
    )