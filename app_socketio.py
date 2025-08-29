#!/usr/bin/env python3
"""
Task Manager Application with WebSocket Support
Main application entry point with Flask-SocketIO integration
"""

import os
import sys
from flask import Flask

# Initialize variables
app = None
socketio = None
db = None
startup_error = None

def create_application():
    """Create application with proper error handling"""
    global app, socketio, db, startup_error
    
    try:
        from app import create_app, socketio as _socketio, db as _db
        from flask_migrate import upgrade
        
        # Set Flask environment first
        config_name = os.getenv('FLASK_ENV', 'production')
        print(f"Creating app with config: {config_name}", file=sys.stderr)
        
        app = create_app(config_name)
        socketio = _socketio
        db = _db
        
        # Add health check endpoint directly to the app
        @app.route('/health')
        def health_check():
            """Health check endpoint for deployment monitoring."""
            print("Health check called - SUCCESS path", file=sys.stderr)
            return 'OK', 200

        @app.route('/websocket/status')  
        def websocket_status():
            """WebSocket status endpoint."""
            return {
                'websocket_enabled': True,
                'connected_users': 0,
                'active_rooms': 0,
                'status': 'active'
            }

        @app.route('/init-db', methods=['POST'])
        def init_database():
            """Initialize database tables."""
            try:
                with app.app_context():
                    db.create_all()
                    return {
                        'status': 'success',
                        'message': 'Database tables created successfully'
                    }
            except Exception as e:
                print(f"Database initialization error: {e}", file=sys.stderr)
                return {
                    'status': 'error',
                    'message': f'Database initialization failed: {str(e)}'
                }, 500
        
        print("Application created successfully", file=sys.stderr)
        return app
        
    except Exception as e:
        startup_error = str(e)
        print(f"Error creating application: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        
        # Create a minimal Flask app for error handling
        app = Flask(__name__)
        
        @app.route('/health')
        def health_error():
            print(f"Health check called - ERROR path: {startup_error}", file=sys.stderr)
            return 'ERROR', 500
            
        @app.route('/')
        def index_error():
            return {'status': 'error', 'message': f'Application failed to start: {startup_error}'}, 500
        
        socketio = None
        db = None
        return app

# Create the application
app = create_application()

if app is not None:
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


# For production deployment with gunicorn
if __name__ == '__main__':
    # Run with SocketIO support for development
    port = int(os.environ.get('PORT', 8080))
    if socketio is not None:
        socketio.run(
            app,
            host='0.0.0.0',
            port=port,
            debug=os.environ.get('FLASK_ENV') == 'development',
            allow_unsafe_werkzeug=True  # For development only
        )
    else:
        # Fallback to regular Flask if SocketIO failed to initialize
        app.run(
            host='0.0.0.0',
            port=port,
            debug=os.environ.get('FLASK_ENV') == 'development'
        )