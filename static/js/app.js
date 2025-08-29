/**
 * Task Manager Frontend JavaScript
 * Handles API interactions and real-time updates
 */

// Global variables
let socket = null;
let authToken = localStorage.getItem('authToken');
const API_BASE = window.location.origin;

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Task Manager App initialized');
    initializeAuth();
    initializeWebSocket();
});

// Authentication functions
function initializeAuth() {
    const token = localStorage.getItem('authToken');
    const currentPath = window.location.pathname;
    
    // Skip auth check for login/register pages
    if (currentPath === '/login' || currentPath === '/register') {
        return;
    }
    
    if (token) {
        // Verify token is still valid
        fetch(`${API_BASE}/api/v1/users/me`, {
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                localStorage.removeItem('authToken');
                redirectToLogin();
            } else {
                return response.json();
            }
        })
        .then(userData => {
            if (userData) {
                updateUserInfo(userData);
            }
        })
        .catch(() => {
            localStorage.removeItem('authToken');
            redirectToLogin();
        });
    } else {
        redirectToLogin();
    }
}

function redirectToLogin() {
    if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        window.location.href = '/login';
    }
}

function updateUserInfo(userData) {
    const userNameElements = document.querySelectorAll('#user-name');
    userNameElements.forEach(element => {
        element.textContent = userData.full_name || userData.username;
    });
}

function logout() {
    fetch(`${API_BASE}/api/v1/auth/logout`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${authToken}`,
            'Content-Type': 'application/json'
        }
    })
    .then(() => {
        localStorage.removeItem('authToken');
        authToken = null;
        if (socket) {
            socket.disconnect();
        }
        window.location.href = '/login';
    })
    .catch(() => {
        localStorage.removeItem('authToken');
        authToken = null;
        window.location.href = '/login';
    });
}

// WebSocket functions
function initializeWebSocket() {
    if (!authToken || window.location.pathname === '/login' || window.location.pathname === '/register') {
        return;
    }

    try {
        socket = io({
            auth: {
                token: authToken
            },
            transports: ['websocket', 'polling']
        });

        socket.on('connect', function() {
            console.log('WebSocket connected');
            updateWebSocketStatus('connected');
        });

        socket.on('disconnect', function() {
            console.log('WebSocket disconnected');
            updateWebSocketStatus('disconnected');
        });

        socket.on('connect_error', function(error) {
            console.error('WebSocket connection error:', error);
            updateWebSocketStatus('disconnected');
        });

        socket.on('error', function(error) {
            console.error('WebSocket error:', error);
            showAlert(error.message || 'WebSocket error', 'error');
        });

        // Task events
        socket.on('task_created', function(data) {
            console.log('Task created:', data);
            showAlert(`New task created: ${data.title}`, 'success');
            if (typeof window.refreshTasks === 'function') {
                window.refreshTasks();
            }
        });

        socket.on('task_updated', function(data) {
            console.log('Task updated:', data);
            showAlert(`Task updated: ${data.title}`, 'info');
            if (typeof window.refreshTasks === 'function') {
                window.refreshTasks();
            }
        });

        socket.on('task_deleted', function(data) {
            console.log('Task deleted:', data);
            showAlert(`Task deleted: ${data.title}`, 'info');
            if (typeof window.refreshTasks === 'function') {
                window.refreshTasks();
            }
        });

        // Project events
        socket.on('project_created', function(data) {
            console.log('Project created:', data);
            showAlert(`New project created: ${data.name}`, 'success');
            if (typeof window.refreshProjects === 'function') {
                window.refreshProjects();
            }
        });

        socket.on('project_updated', function(data) {
            console.log('Project updated:', data);
            showAlert(`Project updated: ${data.name}`, 'info');
            if (typeof window.refreshProjects === 'function') {
                window.refreshProjects();
            }
        });

        socket.on('project_deleted', function(data) {
            console.log('Project deleted:', data);
            showAlert(`Project deleted: ${data.name}`, 'info');
            if (typeof window.refreshProjects === 'function') {
                window.refreshProjects();
            }
        });

        // Notification events
        socket.on('notification', function(data) {
            console.log('Notification:', data);
            showAlert(data.message, data.type || 'info');
        });

    } catch (error) {
        console.error('WebSocket initialization failed:', error);
        updateWebSocketStatus('disconnected');
    }
}

function updateWebSocketStatus(status) {
    const statusElement = document.getElementById('websocket-status');
    if (statusElement) {
        statusElement.className = `websocket-status ${status}`;
        statusElement.textContent = status.charAt(0).toUpperCase() + status.slice(1);
    }
}

// Utility functions
function showAlert(message, type = 'info') {
    const alertsContainer = document.getElementById('alerts');
    if (!alertsContainer) return;
    
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type === 'error' ? 'error' : type}`;
    alertDiv.textContent = message;
    
    // Add close button
    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = '&times;';
    closeBtn.style.cssText = 'float: right; background: none; border: none; font-size: 1.2em; cursor: pointer; margin-left: 10px;';
    closeBtn.onclick = () => alertDiv.remove();
    alertDiv.appendChild(closeBtn);
    
    alertsContainer.appendChild(alertDiv);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

function showLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'flex';
    }
}

function hideLoading() {
    const loadingOverlay = document.getElementById('loading-overlay');
    if (loadingOverlay) {
        loadingOverlay.style.display = 'none';
    }
}

// API helper functions
async function apiRequest(url, options = {}) {
    const token = localStorage.getItem('authToken');
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    try {
        const response = await fetch(`${API_BASE}${url}`, {
            ...options,
            headers
        });

        if (response.status === 401) {
            localStorage.removeItem('authToken');
            window.location.href = '/login';
            return null;
        }

        return response;
    } catch (error) {
        console.error('API request failed:', error);
        throw error;
    }
}

async function apiGet(url) {
    return await apiRequest(url);
}

async function apiPost(url, data) {
    return await apiRequest(url, {
        method: 'POST',
        body: JSON.stringify(data)
    });
}

async function apiPut(url, data) {
    return await apiRequest(url, {
        method: 'PUT',
        body: JSON.stringify(data)
    });
}

async function apiDelete(url) {
    return await apiRequest(url, {
        method: 'DELETE'
    });
}

// Form handling utilities
function getFormData(formId) {
    const form = document.getElementById(formId);
    const formData = new FormData(form);
    const data = {};
    
    for (let [key, value] of formData.entries()) {
        data[key] = value;
    }
    
    return data;
}

function setFormData(formId, data) {
    const form = document.getElementById(formId);
    if (!form) return;
    
    Object.keys(data).forEach(key => {
        const element = form.querySelector(`[name="${key}"], #${key}`);
        if (element) {
            if (element.type === 'checkbox') {
                element.checked = data[key];
            } else {
                element.value = data[key] || '';
            }
        }
    });
}

function clearForm(formId) {
    const form = document.getElementById(formId);
    if (form) {
        form.reset();
    }
}

// Date utilities
function formatDate(dateString) {
    if (!dateString) return 'No date';
    const date = new Date(dateString);
    return date.toLocaleDateString();
}

function formatDateTime(dateString) {
    if (!dateString) return 'No date';
    const date = new Date(dateString);
    return date.toLocaleString();
}

function isOverdue(dateString) {
    if (!dateString) return false;
    const date = new Date(dateString);
    const now = new Date();
    return date < now;
}

// Modal utilities
function showModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('show');
    }
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('show');
    }
}

// Close modals when clicking outside
document.addEventListener('click', function(event) {
    if (event.target.classList.contains('modal')) {
        event.target.classList.remove('show');
    }
});

// Close modals on Escape key
document.addEventListener('keydown', function(event) {
    if (event.key === 'Escape') {
        const openModals = document.querySelectorAll('.modal.show');
        openModals.forEach(modal => {
            modal.classList.remove('show');
        });
    }
});