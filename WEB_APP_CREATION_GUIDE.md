# Create App Platform Application via Web Dashboard

## Step-by-Step Instructions

### 1. Open App Platform Dashboard
- Visit: https://cloud.digitalocean.com/apps
- Click **"Create App"** button

### 2. Configure Source
- **Source Type**: Select "GitHub"
- **Repository**: RithishRamesh-dev/task-manager-test2-app-autodev
- **Branch**: staging
- **Autodeploy**: Enable (checkbox checked)

### 3. Configure App Settings
- **App Name**: task-manager-test2-app
- **Region**: New York 3 (nyc3)

### 4. Configure Service (Python Application)
- **Service Name**: task-manager-api
- **Source Directory**: / (root)
- **Environment**: Python
- **Instance Type**: Basic ($5/month)
- **Instance Size**: 512 MB RAM, 1 vCPU

### 5. Configure Build & Run Commands
- **Build Command**: 
  ```bash
  pip install -r requirements.txt
  flask db upgrade || echo "Migration completed"
  ```
- **Run Command**: 
  ```bash
  python app_socketio.py
  ```

### 6. Environment Variables
Add these environment variables:

| Key | Value | Type |
|-----|-------|------|
| FLASK_ENV | production | Plain Text |
| FLASK_APP | app_socketio.py | Plain Text |
| PORT | 5000 | Plain Text |
| PYTHONPATH | /app | Plain Text |
| SECRET_KEY | [Generate Strong Secret] | Secret |
| JWT_SECRET_KEY | [Generate Strong Secret] | Secret |

### 7. Configure Database
- **Add Database**: Yes
- **Database Type**: PostgreSQL
- **Existing Cluster**: task-manager-test2-db
- **Database Name**: db

### 8. Configure Health Check
- **HTTP Path**: /health
- **Port**: 5000
- **Initial Delay**: 30 seconds
- **Period**: 10 seconds
- **Timeout**: 5 seconds

### 9. Review and Deploy
- Review all settings
- Click **"Create Resources"**
- Wait for deployment to complete (usually 5-10 minutes)

## Expected Result
- App will be available at: https://task-manager-test2-app-[random].ondigitalocean.app
- Database will be automatically connected
- Health check endpoint: [app-url]/health
- WebSocket status: [app-url]/websocket/status

## Post-Deployment Steps
1. Update SECRET_KEY and JWT_SECRET_KEY with strong values
2. Configure CORS origins if needed
3. Test the application endpoints
4. Monitor logs for any issues