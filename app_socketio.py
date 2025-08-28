#!/usr/bin/env python3
"""
Task Manager Application with WebSocket Support
Main application entry point with Flask-SocketIO integration
"""

import os
from app import create_app, socketio, db
from flask_migrate import upgrade

# Create application instance
app = create_app(os.getenv('FLASK_ENV', 'default'))

@app.cli.command()
def deploy():
    """Run deployment tasks."""
    # Create database tables
    db.create_all()
    
    # Migrate database to latest revision
    upgrade()

@app.shell_context_processor
def make_shell_context():
    """Make database models available in shell context."""
    from app.models.user import User
    from app.models.project import Project
    from app.models.task import Task
    from app.models.comment import Comment
    from app.models.project_member import ProjectMember
    
    return {
        'db': db,
        'User': User,
        'Project': Project,
        'Task': Task,
        'Comment': Comment,
        'ProjectMember': ProjectMember,
        'app': app,
        'socketio': socketio
    }

# Health check endpoint (must be defined before any database operations)
@app.route('/health')
def health_check():
    """Health check endpoint for deployment monitoring."""
    return {
        'status': 'healthy',
        'message': 'Task Manager API is running',
        'websocket_enabled': True
    }

# Initialize database tables safely
def init_database():
    """Initialize database tables safely."""
    try:
        with app.app_context():
            db.create_all()
            app.logger.info("Database tables created successfully")
    except Exception as e:
        app.logger.error(f"Database initialization error: {e}")
        # Don't fail the app startup, just log the error

# Initialize database on startup (safer approach)
if not app.config.get('TESTING'):
    init_database()

# WebSocket status endpoint
@app.route('/websocket/status')
def websocket_status():
    """WebSocket status endpoint."""
    try:
        from app.websocket.events import connected_users, user_rooms
        return {
            'websocket_enabled': True,
            'connected_users': len(connected_users),
            'active_rooms': len(user_rooms),
            'status': 'active'
        }
    except Exception as e:
        # If websocket imports fail, still return a basic status
        return {
            'websocket_enabled': True,
            'connected_users': 0,
            'active_rooms': 0,
            'status': 'limited',
            'error': str(e)
        }

# For production deployment with gunicorn
if __name__ == '__main__':
    # Run with SocketIO support for development
    port = int(os.environ.get('PORT', 8080))
    socketio.run(
        app,
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('FLASK_ENV') == 'development',
        allow_unsafe_werkzeug=True  # For development only
    )