from flask import request
from flask_socketio import emit, join_room, leave_room, disconnect
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from . import socketio


@socketio.on('connect')
def on_connect(auth=None):
    """Handle client connection"""
    try:
        # Verify JWT token
        token = None
        if auth and 'token' in auth:
            token = auth['token']
        elif request.args.get('token'):
            token = request.args.get('token')
        
        if not token:
            print("Connection rejected: No token provided")
            disconnect()
            return False
            
        # Set token in request context for verification
        request.environ['HTTP_AUTHORIZATION'] = f'Bearer {token}'
        
        try:
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            
            # Join user-specific room for real-time updates
            join_room(f'user_{user_id}')
            
            print(f"User {user_id} connected to WebSocket")
            emit('status', {'message': 'Connected successfully', 'user_id': user_id})
            
        except Exception as e:
            print(f"JWT verification failed: {e}")
            disconnect()
            return False
            
    except Exception as e:
        print(f"Connection error: {e}")
        disconnect()
        return False


@socketio.on('disconnect')
def on_disconnect():
    """Handle client disconnection"""
    try:
        user_id = get_jwt_identity()
        if user_id:
            leave_room(f'user_{user_id}')
            print(f"User {user_id} disconnected from WebSocket")
    except:
        pass


@socketio.on('join_project')
def on_join_project(data):
    """Join a project room for project-specific updates"""
    try:
        verify_jwt_in_request()
        user_id = get_jwt_identity()
        project_id = data.get('project_id')
        
        if project_id:
            # TODO: Verify user has access to this project
            join_room(f'project_{project_id}')
            emit('status', {'message': f'Joined project {project_id} room'})
            
    except Exception as e:
        emit('error', {'message': 'Failed to join project room'})


@socketio.on('leave_project')
def on_leave_project(data):
    """Leave a project room"""
    try:
        project_id = data.get('project_id')
        if project_id:
            leave_room(f'project_{project_id}')
            emit('status', {'message': f'Left project {project_id} room'})
            
    except Exception as e:
        emit('error', {'message': 'Failed to leave project room'})


# Utility functions for broadcasting updates
def broadcast_task_update(task_data, event_type='task_updated'):
    """Broadcast task updates to relevant users"""
    try:
        # Broadcast to task creator/assignee
        if task_data.get('created_by'):
            socketio.emit(event_type, task_data, room=f"user_{task_data['created_by']}")
        
        if task_data.get('assigned_to') and task_data['assigned_to'] != task_data.get('created_by'):
            socketio.emit(event_type, task_data, room=f"user_{task_data['assigned_to']}")
        
        # Broadcast to project members if task belongs to a project
        if task_data.get('project_id'):
            socketio.emit(event_type, task_data, room=f"project_{task_data['project_id']}")
            
    except Exception as e:
        print(f"Error broadcasting task update: {e}")


def broadcast_project_update(project_data, event_type='project_updated'):
    """Broadcast project updates to project members"""
    try:
        # Broadcast to project owner
        if project_data.get('owner_id'):
            socketio.emit(event_type, project_data, room=f"user_{project_data['owner_id']}")
        
        # Broadcast to project room (all members)
        if project_data.get('id'):
            socketio.emit(event_type, project_data, room=f"project_{project_data['id']}")
            
    except Exception as e:
        print(f"Error broadcasting project update: {e}")


def broadcast_user_notification(user_id, notification_data):
    """Send notification to specific user"""
    try:
        socketio.emit('notification', notification_data, room=f"user_{user_id}")
    except Exception as e:
        print(f"Error sending user notification: {e}")