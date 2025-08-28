# DigitalOcean Deployment Guide

## Prerequisites

1. **DigitalOcean Account**: Ensure you have a DigitalOcean account with billing enabled
2. **doctl CLI**: Install and authenticate the DigitalOcean CLI tool
3. **GitHub Repository**: Ensure the repository is public or you have proper access configured

## Quick Deployment

### Option 1: Automated Script (Recommended)

```bash
# 1. Authenticate with DigitalOcean (one-time setup)
doctl auth init

# 2. Run the automated deployment script
./deploy-digitalocean.sh
```

### Option 2: Manual Step-by-Step

#### Step 1: Authenticate doctl
```bash
# Get your API token from: https://cloud.digitalocean.com/account/api/tokens
doctl auth init
```

#### Step 2: Create PostgreSQL Database
```bash
doctl databases create task-manager-test2-db \
  --engine postgres \
  --region nyc3 \
  --size db-s-1vcpu-1gb \
  --num-nodes 1 \
  --version 14
```

#### Step 3: Create App Platform Application
```bash
doctl apps create app-spec.yaml
```

#### Step 4: Verify Deployment
```bash
# Check database status
doctl databases list

# Check app status
doctl apps list

# Get app details
doctl apps get <APP_ID>
```

## Infrastructure Components

### 1. PostgreSQL Database Cluster
- **Name**: task-manager-test2-db
- **Engine**: PostgreSQL 14
- **Region**: NYC3 
- **Configuration**: 1 vCPU, 1GB RAM, 1 node
- **Storage**: 10GB (auto-scaling enabled)

### 2. App Platform Application
- **Name**: task-manager-test2-app
- **Runtime**: Python 3.11
- **Instance**: Basic XXS (0.5 vCPU, 0.5GB RAM)
- **GitHub Integration**: Auto-deploy from staging branch
- **Health Check**: HTTP endpoint at `/health`

## Environment Variables

### Required Variables (Auto-configured)
- `DATABASE_URL`: PostgreSQL connection string (injected by DigitalOcean)
- `FLASK_ENV`: Set to 'production'
- `FLASK_APP`: Set to 'app_socketio.py'
- `PORT`: Set to '5000'

### Security Variables (MUST be updated)
- `SECRET_KEY`: Flask secret key for sessions
- `JWT_SECRET_KEY`: JWT signing secret
- Update these in the App Platform dashboard under Settings → Environment

### Optional Variables
- `CORS_ORIGINS`: Frontend domain(s) for CORS
- `REDIS_URL`: Redis connection string (if using Redis)
- `MAIL_SERVER`, `MAIL_USERNAME`, etc.: Email configuration

## Post-Deployment Configuration

### 1. Database Setup
The application will automatically:
- Create database tables on first run
- Run any pending migrations
- Set up initial schema

### 2. Environment Variables
1. Go to: https://cloud.digitalocean.com/apps/
2. Select your app: task-manager-test2-app  
3. Navigate to Settings → Environment
4. Update production secrets:
   ```
   SECRET_KEY=<generate-strong-secret>
   JWT_SECRET_KEY=<generate-strong-jwt-secret>
   ```

### 3. Custom Domain (Optional)
1. In App Platform settings → Domains
2. Add your custom domain
3. Configure DNS records as instructed
4. Update CORS settings accordingly

### 4. GitHub Integration
1. Ensure GitHub repository permissions are correct
2. Verify deploy-on-push is enabled
3. Test by pushing to staging branch

## Monitoring and Logs

### Application Logs
```bash
# View real-time logs
doctl apps logs <APP_ID> --type run

# View build logs  
doctl apps logs <APP_ID> --type build
```

### Database Monitoring
```bash
# Get database metrics
doctl databases get <DATABASE_ID>

# View connection details
doctl databases connection <DATABASE_ID>
```

### Health Checks
- Application: `https://your-app.ondigitalocean.app/health`
- WebSocket: `https://your-app.ondigitalocean.app/websocket/status`

## Scaling and Performance

### Application Scaling
- **Horizontal**: Increase instance count in app-spec.yaml
- **Vertical**: Change instance_size_slug (basic-xs, basic-s, etc.)

### Database Scaling
- **Storage**: Auto-scaling enabled by default
- **Performance**: Upgrade to larger database sizes via dashboard
- **High Availability**: Add additional nodes for redundancy

## Security Considerations

### 1. Environment Variables
- Never commit secrets to repository
- Use DigitalOcean's secret management
- Regularly rotate secrets

### 2. Database Security
- Database is private by default (VPC)
- SSL connections enforced
- Regular automated backups

### 3. Application Security
- HTTPS enforced by default
- CORS properly configured
- JWT tokens with expiration

## Troubleshooting

### Common Issues

#### 1. Build Failures
```bash
# Check build logs
doctl apps logs <APP_ID> --type build

# Common fixes:
# - Verify requirements.txt is complete
# - Check Python version compatibility
# - Ensure all dependencies are available
```

#### 2. Database Connection Issues
```bash
# Verify database is online
doctl databases get <DATABASE_ID>

# Check connection string format
doctl databases connection <DATABASE_ID>

# Verify environment variables are set correctly
```

#### 3. WebSocket Issues
- Ensure eventlet is in requirements.txt
- Check CORS configuration for WebSocket connections
- Verify health check endpoints are accessible

### Log Analysis
```bash
# Application errors
doctl apps logs <APP_ID> --type run | grep ERROR

# Database connection logs
doctl apps logs <APP_ID> --type run | grep "database"

# WebSocket connection logs  
doctl apps logs <APP_ID> --type run | grep "socketio"
```

## Backup and Recovery

### Database Backups
- **Automatic**: Daily backups retained for 7 days
- **Manual**: Create point-in-time backups via dashboard
- **Restore**: Contact DigitalOcean support for restore procedures

### Application Recovery
- **Source Code**: Stored in GitHub repository
- **Configuration**: app-spec.yaml tracks infrastructure
- **Secrets**: Store securely and separately

## Cost Optimization

### Current Monthly Costs (Estimated)
- **Database**: ~$15/month (db-s-1vcpu-1gb)
- **App Platform**: ~$5/month (Basic XXS tier)
- **Total**: ~$20/month

### Optimization Tips
1. **Right-size Resources**: Start small and scale up
2. **Monitor Usage**: Use DigitalOcean monitoring
3. **Clean Up**: Remove unused resources
4. **Reserved Instances**: Consider for long-term deployments

## Support and Resources

- **DigitalOcean Documentation**: https://docs.digitalocean.com/
- **App Platform Guide**: https://docs.digitalocean.com/products/app-platform/
- **Database Guide**: https://docs.digitalocean.com/products/databases/
- **Community**: https://www.digitalocean.com/community/

## Next Steps After Deployment

1. **Configure Frontend**: Update frontend to connect to deployed API
2. **Set up Monitoring**: Configure alerts and monitoring
3. **Performance Testing**: Load test the application
4. **Security Audit**: Review security configurations
5. **Documentation**: Update API documentation with production URLs