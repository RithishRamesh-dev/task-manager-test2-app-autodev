#!/usr/bin/env python3
"""
Ultra-minimal Flask app to test DigitalOcean App Platform deployment
"""

import os
from flask import Flask, jsonify

# Create minimal Flask app
app = Flask(__name__)

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'message': 'Simple Flask app is running',
        'port': os.environ.get('PORT', '8080')
    })

@app.route('/')
def index():
    """Root endpoint."""
    return jsonify({
        'message': 'Simple Flask app deployed successfully',
        'endpoints': ['/health', '/test']
    })

@app.route('/test')
def test():
    """Test endpoint."""
    return jsonify({
        'message': 'Test endpoint working',
        'status': 'success'
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )