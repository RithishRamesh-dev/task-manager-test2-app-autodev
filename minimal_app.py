#!/usr/bin/env python3
"""
Minimal Flask app for debugging DigitalOcean App Platform deployment issues
"""

import os
from flask import Flask

# Create minimal Flask app
app = Flask(__name__)

@app.route('/health')
def health_check():
    """Basic health check endpoint."""
    return {
        'status': 'healthy',
        'message': 'Minimal Flask app is running'
    }

@app.route('/')
def index():
    """Basic index route."""
    return {
        'message': 'Minimal Flask app is working',
        'port': os.environ.get('PORT', '5000'),
        'flask_env': os.environ.get('FLASK_ENV', 'not set')
    }

if __name__ == '__main__':
    # Run the app
    port = int(os.environ.get('PORT', 5000))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('FLASK_ENV') == 'development'
    )