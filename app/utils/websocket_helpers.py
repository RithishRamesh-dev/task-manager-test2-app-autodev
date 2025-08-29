"""
WebSocket helper functions for broadcasting real-time updates
"""
from datetime import datetime
from app.websockets.events import broadcast_task_update, broadcast_project_update, broadcast_user_notification


def emit_task_created(task):
    """Emit task creation event"""
    task_data = task.to_dict()
    broadcast_task_update(task_data, 'task_created')


def emit_task_updated(task):
    """Emit task update event"""
    task_data = task.to_dict()
    broadcast_task_update(task_data, 'task_updated')


def emit_task_deleted(task):
    """Emit task deletion event"""
    task_data = task.to_dict()
    broadcast_task_update(task_data, 'task_deleted')


def emit_project_created(project):
    """Emit project creation event"""
    project_data = project.to_dict()
    broadcast_project_update(project_data, 'project_created')


def emit_project_updated(project):
    """Emit project update event"""
    project_data = project.to_dict()
    broadcast_project_update(project_data, 'project_updated')


def emit_project_deleted(project):
    """Emit project deletion event"""
    project_data = project.to_dict()
    broadcast_project_update(project_data, 'project_deleted')


def emit_user_notification(user_id, message, notification_type='info'):
    """Send notification to specific user"""
    notification_data = {
        'message': message,
        'type': notification_type,
        'timestamp': datetime.now().isoformat()
    }
    broadcast_user_notification(user_id, notification_data)