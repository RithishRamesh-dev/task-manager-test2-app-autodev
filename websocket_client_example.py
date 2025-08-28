#!/usr/bin/env python3
"""
WebSocket Client Example for Task Manager
Demonstrates how to connect and interact with the real-time WebSocket events
"""

import socketio
import json
from datetime import datetime
import asyncio

class TaskManagerWebSocketClient:
    """WebSocket client for Task Manager real-time functionality"""
    
    def __init__(self, server_url='http://localhost:5000', token=None):
        self.server_url = server_url
        self.token = token
        
        # Initialize SocketIO client
        self.sio = socketio.Client(logger=True, engineio_logger=True)
        
        # Register event handlers
        self._register_handlers()
    
    def _register_handlers(self):
        """Register WebSocket event handlers"""
        
        @self.sio.event
        def connect():
            print(f"[{datetime.now()}] Connected to server")
        
        @self.sio.event
        def disconnect():
            print(f"[{datetime.now()}] Disconnected from server")
        
        @self.sio.event
        def connected(data):
            print(f"[{datetime.now()}] Connection confirmed: {data}")
        
        @self.sio.event
        def error(data):
            print(f"[{datetime.now()}] Error: {data}")
        
        # Task events
        @self.sio.event
        def task_created(data):
            task = data.get('task', {})
            creator = data.get('created_by', {})
            print(f"[{datetime.now()}] 🆕 New task created: '{task.get('title')}' by {creator.get('full_name')}")
        
        @self.sio.event
        def task_updated(data):
            task = data.get('task', {})
            updater = data.get('updated_by', {})
            changes = data.get('changes', {})
            print(f"[{datetime.now()}] 📝 Task updated: '{task.get('title')}' by {updater.get('full_name')}")
            if changes:
                print(f"    Changes: {json.dumps(changes, indent=2)}")
        
        @self.sio.event
        def task_status_changed(data):
            task_title = data.get('task_title')
            old_status = data.get('old_status')
            new_status = data.get('new_status')
            changer = data.get('changed_by', {})
            print(f"[{datetime.now()}] 🔄 Task status changed: '{task_title}' {old_status} → {new_status} by {changer.get('full_name')}")
        
        @self.sio.event
        def task_deleted(data):
            task_title = data.get('task_title')
            deleter = data.get('deleted_by', {})
            print(f"[{datetime.now()}] 🗑️ Task deleted: '{task_title}' by {deleter.get('full_name')}")
        
        # Comment events
        @self.sio.event
        def comment_added(data):
            comment = data.get('comment', {})
            task = data.get('task', {})
            print(f"[{datetime.now()}] 💬 New comment on '{task.get('title')}' by {comment.get('author_name')}: {comment.get('comment_text')}")
        
        # Project events
        @self.sio.event
        def project_updated(data):
            project = data.get('project', {})
            updater = data.get('updated_by', {})
            print(f"[{datetime.now()}] 📁 Project updated: '{project.get('name')}' by {updater.get('full_name')}")
        
        # User interaction events
        @self.sio.event
        def user_connected(data):
            print(f"[{datetime.now()}] 👋 User joined: {data.get('full_name')} ({data.get('username')})")
        
        @self.sio.event
        def user_disconnected(data):
            print(f"[{datetime.now()}] 👋 User left: {data.get('username')}")
        
        @self.sio.event
        def user_typing(data):
            if data.get('is_typing'):
                print(f"[{datetime.now()}] ⌨️ {data.get('full_name')} is typing...")
            else:
                print(f"[{datetime.now()}] ⌨️ {data.get('full_name')} stopped typing")
        
        # Notification events
        @self.sio.event
        def notification(data):
            print(f"[{datetime.now()}] 🔔 Notification: {data.get('message')}")
        
        @self.sio.event
        def online_users(data):
            users = data.get('users', [])
            print(f"[{datetime.now()}] 👥 Online users ({data.get('count', 0)}): {', '.join([u.get('full_name', u.get('username', 'Unknown')) for u in users])}")
        
        @self.sio.event
        def pong(data):
            print(f"[{datetime.now()}] 🏓 Pong received")
    
    def connect(self):
        """Connect to the WebSocket server"""
        try:
            # Connect with token if provided
            if self.token:
                self.sio.connect(self.server_url, auth={'token': self.token})
            else:
                self.sio.connect(self.server_url)
            
            return True
        except Exception as e:
            print(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the WebSocket server"""
        self.sio.disconnect()
    
    def join_project(self, project_id):
        """Join a project room for real-time updates"""
        self.sio.emit('join_project', {'project_id': project_id})
    
    def leave_project(self, project_id):
        """Leave a project room"""
        self.sio.emit('leave_project', {'project_id': project_id})
    
    def send_typing_indicator(self, task_id, is_typing=True):
        """Send typing indicator for a task"""
        self.sio.emit('user_typing', {'task_id': task_id, 'is_typing': is_typing})
    
    def get_online_users(self, project_id):
        """Get list of online users in a project"""
        self.sio.emit('get_online_users', {'project_id': project_id})
    
    def ping(self):
        """Send ping for keepalive"""
        self.sio.emit('ping')
    
    def wait(self):
        """Keep the client running"""
        self.sio.wait()


# Example usage
if __name__ == '__main__':
    import time
    import threading
    
    # Create client instance
    client = TaskManagerWebSocketClient(
        server_url='http://localhost:5000',
        token=None  # Replace with actual JWT token for authenticated connections
    )
    
    # Connect to server
    if client.connect():
        print("Connected! Listening for real-time updates...")
        
        # Example: Join a project room (replace with actual project ID)
        # client.join_project(1)
        
        # Example: Get online users (replace with actual project ID)
        # client.get_online_users(1)
        
        # Send periodic pings
        def send_pings():
            while True:
                time.sleep(30)  # Ping every 30 seconds
                try:
                    client.ping()
                except:
                    break
        
        ping_thread = threading.Thread(target=send_pings, daemon=True)
        ping_thread.start()
        
        try:
            # Keep the client running
            client.wait()
        except KeyboardInterrupt:
            print("\nDisconnecting...")
            client.disconnect()
    else:
        print("Failed to connect to server")