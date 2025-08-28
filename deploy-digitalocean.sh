#!/bin/bash

# DigitalOcean Infrastructure Provisioning Script
# For task-manager-test2-app

set -e  # Exit on any error

echo "🚀 Starting DigitalOcean infrastructure provisioning..."
echo "==============================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if doctl is authenticated
echo "📋 Checking doctl authentication..."
if ! doctl auth whoami &>/dev/null; then
    echo -e "${RED}❌ doctl is not authenticated. Please run 'doctl auth init' first.${NC}"
    echo "   Visit: https://cloud.digitalocean.com/account/api/tokens to get your token"
    exit 1
fi

echo -e "${GREEN}✅ doctl is authenticated${NC}"

# Step 1: Create PostgreSQL Database Cluster
echo ""
echo "🗄️  Creating PostgreSQL database cluster..."
echo "================================================"

DB_NAME="task-manager-test2-db"
REGION="nyc3"
SIZE="db-s-1vcpu-1gb"
POSTGRES_VERSION="14"

# Check if database already exists
if doctl databases list --format Name --no-header | grep -q "^${DB_NAME}$"; then
    echo -e "${YELLOW}⚠️  Database cluster '${DB_NAME}' already exists${NC}"
    DB_ID=$(doctl databases list --format ID,Name --no-header | grep "${DB_NAME}" | awk '{print $1}')
else
    echo "Creating database cluster: ${DB_NAME}"
    DB_ID=$(doctl databases create "${DB_NAME}" \
        --engine postgres \
        --region "${REGION}" \
        --size "${SIZE}" \
        --num-nodes 1 \
        --version "${POSTGRES_VERSION}" \
        --format ID --no-header)
    
    echo -e "${GREEN}✅ Database cluster created with ID: ${DB_ID}${NC}"
    
    # Wait for database to be ready
    echo "⏳ Waiting for database to be ready..."
    while true; do
        STATUS=$(doctl databases get "${DB_ID}" --format Status --no-header)
        if [ "$STATUS" = "online" ]; then
            echo -e "${GREEN}✅ Database is online and ready${NC}"
            break
        else
            echo "Database status: ${STATUS} - waiting..."
            sleep 30
        fi
    done
fi

# Step 2: Create App Platform Application  
echo ""
echo "📱 Creating App Platform application..."
echo "======================================"

APP_NAME="task-manager-test2-app"

# Check if app already exists
if doctl apps list --format Spec.Name --no-header | grep -q "^${APP_NAME}$"; then
    echo -e "${YELLOW}⚠️  App '${APP_NAME}' already exists${NC}"
    APP_ID=$(doctl apps list --format ID,Spec.Name --no-header | grep "${APP_NAME}" | awk '{print $1}')
else
    echo "Creating app: ${APP_NAME}"
    if [ ! -f "app-spec.yaml" ]; then
        echo -e "${RED}❌ app-spec.yaml not found. Please ensure it exists in the current directory.${NC}"
        exit 1
    fi
    
    APP_ID=$(doctl apps create app-spec.yaml --format ID --no-header)
    echo -e "${GREEN}✅ App created with ID: ${APP_ID}${NC}"
    
    # Wait for initial deployment
    echo "⏳ Waiting for initial deployment..."
    sleep 60  # Give it a minute to start
fi

# Step 3: Get connection information
echo ""
echo "🔗 Getting connection information..."
echo "=================================="

echo "Database Information:"
echo "===================="
doctl databases get "${DB_ID}" --format Name,Status,Engine,Version,Connection

echo ""
echo "App Information:"
echo "==============="
doctl apps get "${APP_ID}" --format Spec.Name,DefaultIngress,LiveURL

# Step 4: Display next steps
echo ""
echo "📝 Next Steps:"
echo "============="
echo "1. Database linking:"
echo "   - The database should be automatically linked via the app-spec.yaml"
echo "   - If not, visit: https://cloud.digitalocean.com/apps/${APP_ID}/settings"
echo "   - Link the database '${DB_NAME}' in the Resources tab"
echo ""
echo "2. Environment Variables (if not auto-configured):"
echo "   - Set DATABASE_URL to the connection string from the database"
echo "   - Update SECRET_KEY and JWT_SECRET_KEY in production"
echo ""
echo "3. Domain Configuration:"
echo "   - Configure your custom domain in the App Platform settings"
echo "   - Update CORS settings if needed"
echo ""
echo "4. GitHub Integration:"
echo "   - Ensure GitHub repository access is properly configured"
echo "   - Verify deploy-on-push is enabled for the staging branch"
echo ""

# Get the app URL
APP_URL=$(doctl apps get "${APP_ID}" --format LiveURL --no-header)
if [ -n "${APP_URL}" ] && [ "${APP_URL}" != "<no value>" ]; then
    echo -e "${GREEN}🎉 Deployment complete! Your app should be available at:${NC}"
    echo -e "${GREEN}${APP_URL}${NC}"
    echo ""
    echo "Health check: ${APP_URL}/health"
    echo "WebSocket status: ${APP_URL}/websocket/status"
else
    echo -e "${YELLOW}⏳ App is still deploying. Check status with:${NC}"
    echo "doctl apps get ${APP_ID}"
fi

echo ""
echo -e "${GREEN}✅ Infrastructure provisioning completed!${NC}"
echo "Database ID: ${DB_ID}"
echo "App ID: ${APP_ID}"

# Optional: Open in browser
read -p "🌐 Open DigitalOcean dashboard? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    open "https://cloud.digitalocean.com/apps/${APP_ID}"
fi