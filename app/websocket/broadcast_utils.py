"""
WebSocket Broadcasting Utilities
Helper functions for broadcasting real-time updates from API endpoints
"""

from app import socketio, db
from app.models.task import Task
from app.models.project import Project
from app.models.project_member import ProjectMember
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def broadcast_task_assignment(task, assigned_to_user, assigned_by_user):
    """
    Broadcast task assignment notification
    """
    try:
        # Send notification to newly assigned user
        socketio.emit('task_assigned', {
            'task': {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'project_id': task.project_id,
                'due_date': task.due_date.isoformat() if task.due_date else None
            },
            'assigned_to': {
                'id': assigned_to_user.id,
                'username': assigned_to_user.username,
                'full_name': assigned_to_user.full_name
            },
            'assigned_by': {
                'id': assigned_by_user.id,
                'username': assigned_by_user.username,
                'full_name': assigned_by_user.full_name
            },
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"user_{assigned_to_user.id}")

        # Broadcast to project room
        socketio.emit('task_assignment_changed', {
            'task_id': task.id,
            'task_title': task.title,
            'assigned_to': {
                'id': assigned_to_user.id,
                'username': assigned_to_user.username,
                'full_name': assigned_to_user.full_name
            },
            'assigned_by': {
                'id': assigned_by_user.id,
                'username': assigned_by_user.username,
                'full_name': assigned_by_user.full_name
            },
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"project_{task.project_id}")
        
        logger.info(f"Task {task.id} assignment broadcasted")
        
    except Exception as e:
        logger.error(f"Error broadcasting task assignment: {e}")


def broadcast_project_member_added(project, new_member_user, added_by_user):
    """
    Broadcast when a new member is added to a project
    """
    try:
        # Notify the new member
        socketio.emit('project_member_added', {
            'project': {
                'id': project.id,
                'name': project.name,
                'description': project.description
            },
            'new_member': {
                'id': new_member_user.id,
                'username': new_member_user.username,
                'full_name': new_member_user.full_name
            },
            'added_by': {
                'id': added_by_user.id,
                'username': added_by_user.username,
                'full_name': added_by_user.full_name
            },
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"user_{new_member_user.id}")

        # Broadcast to project room
        socketio.emit('project_member_joined', {
            'project_id': project.id,
            'project_name': project.name,
            'new_member': {
                'id': new_member_user.id,
                'username': new_member_user.username,
                'full_name': new_member_user.full_name
            },
            'added_by': {
                'id': added_by_user.id,
                'username': added_by_user.username,
                'full_name': added_by_user.full_name
            },
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"project_{project.id}")
        
        logger.info(f"Project member addition broadcasted for project {project.id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting project member addition: {e}")


def broadcast_task_due_reminder(task):
    """
    Broadcast task due date reminder
    """
    try:
        if not task.assigned_to or not task.due_date:
            return
            
        # Send reminder to assigned user
        socketio.emit('task_due_reminder', {
            'task': {
                'id': task.id,
                'title': task.title,
                'description': task.description,
                'status': task.status,
                'priority': task.priority,
                'project_id': task.project_id,
                'due_date': task.due_date.isoformat()
            },
            'reminder_type': 'due_soon',
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"user_{task.assigned_to}")

        # Also broadcast to project room for awareness
        socketio.emit('task_due_alert', {
            'task_id': task.id,
            'task_title': task.title,
            'assigned_to': task.assigned_to,
            'due_date': task.due_date.isoformat(),
            'priority': task.priority,
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"project_{task.project_id}")
        
        logger.info(f"Task due reminder broadcasted for task {task.id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting task due reminder: {e}")


def broadcast_project_stats_update(project_id):
    """
    Broadcast updated project statistics
    """
    try:
        # Calculate project statistics
        total_tasks = db.session.query(Task).filter_by(project_id=project_id).count()
        completed_tasks = db.session.query(Task).filter_by(
            project_id=project_id, 
            status='completed'
        ).count()
        in_progress_tasks = db.session.query(Task).filter_by(
            project_id=project_id, 
            status='in_progress'
        ).count()
        pending_tasks = db.session.query(Task).filter_by(
            project_id=project_id, 
            status='pending'
        ).count()
        
        progress_percentage = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

        # Broadcast statistics to project room
        socketio.emit('project_stats_updated', {
            'project_id': project_id,
            'stats': {
                'total_tasks': total_tasks,
                'completed_tasks': completed_tasks,
                'in_progress_tasks': in_progress_tasks,
                'pending_tasks': pending_tasks,
                'progress_percentage': round(progress_percentage, 2)
            },
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"project_{project_id}")
        
        logger.info(f"Project stats updated for project {project_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting project stats: {e}")


def broadcast_bulk_task_update(project_id, task_ids, changes, updated_by_user):
    """
    Broadcast bulk task update
    """
    try:
        socketio.emit('bulk_task_update', {
            'project_id': project_id,
            'task_ids': task_ids,
            'changes': changes,
            'updated_by': {
                'id': updated_by_user.id,
                'username': updated_by_user.username,
                'full_name': updated_by_user.full_name
            },
            'timestamp': datetime.utcnow().isoformat()
        }, room=f"project_{project_id}")
        
        # Also update project stats
        broadcast_project_stats_update(project_id)
        
        logger.info(f"Bulk task update broadcasted for project {project_id}")
        
    except Exception as e:
        logger.error(f"Error broadcasting bulk task update: {e}")


def broadcast_system_maintenance(message, maintenance_type='info'):
    """
    Broadcast system-wide maintenance or important messages
    """
    try:
        socketio.emit('system_announcement', {
            'type': maintenance_type,
            'message': message,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        logger.info(f"System announcement broadcasted: {message}")
        
    except Exception as e:
        logger.error(f"Error broadcasting system announcement: {e}")


def get_project_activity_summary(project_id, hours=24):
    """
    Get activity summary for a project in the last N hours
    """
    from datetime import datetime, timedelta
    
    try:
        # This would typically query activity logs
        # For now, return a basic structure
        activity_summary = {
            'project_id': project_id,
            'timeframe_hours': hours,
            'tasks_created': 0,
            'tasks_updated': 0,
            'tasks_completed': 0,
            'comments_added': 0,
            'active_users': 0,
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return activity_summary
        
    except Exception as e:
        logger.error(f"Error getting project activity summary: {e}")
        return None