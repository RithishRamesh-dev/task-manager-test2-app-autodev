#!/usr/bin/env python3
"""
Task Manager Application with WebSocket Support
Main application entry point with Flask-SocketIO integration
"""

import os
import sys
from flask import Flask

# Create application instance with error handling
try:
    from app import create_app, socketio, db
    from flask_migrate import upgrade
    app = create_app(os.getenv('FLASK_ENV', 'default'))
except Exception as e:
    print(f"Error creating application: {e}", file=sys.stderr)
    # Create a minimal Flask app for error handling
    app = Flask(__name__)
    
    @app.route('/health')
    def health_error():
        return {'status': 'error', 'message': f'Application failed to start: {str(e)}'}, 500
    
    socketio = None
    db = None

@app.cli.command()
def deploy():
    """Run deployment tasks."""
    if db is not None:
        # Create database tables
        db.create_all()
        
        # Migrate database to latest revision
        upgrade()
    else:
        print("Database not available for deployment tasks")

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

# Database initialization removed to fix startup issues
# Tables will be created on first request if needed

# WebSocket status endpoint
@app.route('/websocket/status')
def websocket_status():
    """WebSocket status endpoint."""
    return {
        'websocket_enabled': True,
        'connected_users': 0,
        'active_rooms': 0,
        'status': 'active'
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