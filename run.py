#!/usr/bin/env python3
"""
Task Manager Application Entry Point

This file serves as the main entry point for the Flask application.
"""

import os
from app import create_app, db
from app.models import User, Project, ProjectMember, Task, TaskComment, Category, TaskCategory, Attachment

# Create Flask application instance
app = create_app(os.environ.get('FLASK_ENV', 'development'))

# Make shell context available for flask shell command
@app.shell_context_processor
def make_shell_context():
    """Make database models available in flask shell"""
    return {
        'db': db,
        'User': User,
        'Project': Project,
        'ProjectMember': ProjectMember,
        'Task': Task,
        'TaskComment': TaskComment,
        'Category': Category,
        'TaskCategory': TaskCategory,
        'Attachment': Attachment
    }

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)