"""
API Blueprint package for the Task Manager Application

This module contains all API endpoints and related functionality.
"""

from flask import Blueprint

# Create the main API blueprint
api = Blueprint('api', __name__, url_prefix='/api/v1')

# Import all route modules to register them with the blueprint
from app.api import auth, tasks, projects, categories, attachments, users

__all__ = ['api']