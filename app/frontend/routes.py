from flask import render_template, redirect, url_for, jsonify
from . import frontend


@frontend.route('/')
def index():
    """Main landing page - redirect to dashboard for authenticated users"""
    return redirect(url_for('frontend.dashboard'))


@frontend.route('/login')
def login():
    """Login page"""
    return render_template('auth/login.html')


@frontend.route('/register')
def register():
    """Registration page"""
    return render_template('auth/register.html')


@frontend.route('/dashboard')
def dashboard():
    """Dashboard page"""
    return render_template('dashboard.html', current_user='user')


@frontend.route('/tasks')
def tasks():
    """Tasks management page"""
    return render_template('tasks.html', current_user='user')


@frontend.route('/projects')
def projects():
    """Projects management page"""
    return render_template('projects.html', current_user='user')


# API status endpoint for backward compatibility
@frontend.route('/health')
def health():
    """Health check endpoint"""
    return jsonify({
        "name": "Task Manager API",
        "version": "1.0.0",
        "status": "running",
        "documentation": "RESTful API for task management with JWT authentication",
        "endpoints": {
            "auth": "/api/v1/auth/*",
            "users": "/api/v1/users",
            "projects": "/api/v1/projects", 
            "tasks": "/api/v1/tasks",
            "categories": "/api/v1/categories",
            "websocket": "/websocket/status",
            "health": "/health"
        }
    })


@frontend.route('/websocket/status')
def websocket_status():
    """WebSocket status endpoint"""
    return jsonify({
        "websocket": "active",
        "status": "running",
        "transports": ["websocket", "polling"]
    })