# Deployment Guide for Orris RAG API

## Overview

Complete deployment guide for the Orris RAG API on cloud platforms like Render or DigitalOcean.

## Pre-Deployment Checklist

### ✅ Database Migration
- [x] WebhookChannel model created
- [x] Database migration files generated
- [x] Automatic migration implemented
- [x] Service layer updated

### ✅ Environment Configuration
- [x] Environment variables documented
- [x] Configuration validation added
- [x] Production settings optimized

### ✅ Dependencies
- [x] Requirements.txt updated
- [x] All dependencies pinned
- [x] Production dependencies identified

## Environment Variables

### Required Variables
```bash
# Database
DATABASE_URL=postgresql://username:password@host:port/database

# Google Drive Integration - Choose ONE method:
# Method 1: For Production (recommended for cloud deployment)
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"your-project-id","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...","client_email":"your-service@project.iam.gserviceaccount.com","client_id":"...","auth_uri":"https://accounts.google.com/o/oauth2/auth","token_uri":"https://oauth2.googleapis.com/token","auth_provider_x509_cert_url":"https://www.googleapis.com/oauth2/v1/certs","client_x509_cert_url":"..."}'

# Method 2: For Local Development (file-based)
GOOGLE_SERVICE_ACCOUNT_FILE=./config/service-account.json
# OR
GOOGLE_APPLICATION_CREDENTIALS=./config/service-account.json

# Google Drive Configuration
GDRIVE_ROOT_ID=your-google-drive-folder-id

# Webhook Configuration
WEBHOOK_BASE_URL=https://your-app.onrender.com

# JWT Authentication
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Qdrant Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=orris_rag

# Claude AI (Optional)
ANTHROPIC_API_KEY=your-anthropic-api-key
```

### Optional Variables
```bash
# Application Settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# CORS Settings
ALLOWED_ORIGINS=https://your-frontend.com,https://www.your-frontend.com

# File Upload Settings
MAX_FILE_SIZE=10485760  # 10MB in bytes
ALLOWED_FILE_TYPES=pdf,txt,docx,md
```

## Deployment Platforms

### Render Deployment

#### 1. **Create PostgreSQL Database**
1. Go to Render Dashboard
2. Create new PostgreSQL database
3. Note the connection details

#### 2. **Create Web Service**
1. Connect your GitHub repository
2. Choose "Web Service"
3. Configure build settings:
   ```bash
   # Build Command
   pip install -r requirements.txt
   
   # Start Command
   python main.py
   ```

#### 3. **Environment Variables**
Add all required environment variables in Render dashboard.

#### 4. **Deploy**
1. Click "Create Web Service"
2. Monitor deployment logs
3. Verify database migration runs successfully

### DigitalOcean App Platform

#### 1. **Create App**
1. Connect GitHub repository
2. Choose "Python" app type
3. Configure build settings:
   ```yaml
   # .do/app.yaml
   name: orris-rag-api
   services:
   - name: api
     source_dir: backend
     github:
       repo: your-username/orris
       branch: main
     run_command: python main.py
     environment_slug: python
     instance_count: 1
     instance_size_slug: basic-xxs
     envs:
     - key: DATABASE_URL
       value: ${db.DATABASE_URL}
   databases:
   - name: orris-db
     engine: PG
     version: "13"
   ```

#### 2. **Environment Variables**
Configure in DigitalOcean dashboard or app.yaml file.

#### 3. **Deploy**
Push to GitHub branch to trigger deployment.

## Docker Deployment (Alternative)

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["python", "main.py"]
```

### Docker Compose (for local testing)
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/orris
      - GDRIVE_ROOT_ID=your-folder-id
      - WEBHOOK_BASE_URL=http://localhost:8000
    depends_on:
      - db
      - qdrant

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=orris
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  qdrant:
    image: qdrant/qdrant
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  postgres_data:
  qdrant_data:
```

## Post-Deployment Steps

### 1. **Verify Database**
```bash
# Check if tables are created
curl https://your-app.onrender.com/health

# Check webhook channels
# Should return active webhook channels
```

### 2. **Test Webhook Integration**
1. Upload a file to the configured Google Drive folder
2. Check application logs for webhook notifications
3. Verify file is processed and indexed

### 3. **Test RAG API**
```bash
# Test chat endpoint
curl -X POST https://your-app.onrender.com/chat \
  -H "Content-Type: application/json" \
  -d '{"query": "What documents do you have?"}'
```

### 4. **Monitor Health**
```bash
# Health check endpoint
curl https://your-app.onrender.com/health

# Expected response:
{
  "status": "healthy",
  "database": "connected",
  "qdrant": "connected",
  "webhooks": "active"
}
```

## Monitoring and Maintenance

### Application Logs
Monitor these log messages:
- `Successfully migrated X webhook channels from JSON to database`
- `Webhook channels initialized successfully`
- `Successfully renewed webhook for channel: X`
- `Failed to renew webhook for channel: X`

### Database Monitoring
```sql
-- Check webhook channels
SELECT COUNT(*) as total_channels FROM webhook_channels;

-- Check active webhooks
SELECT COUNT(*) as active_webhooks 
FROM webhook_channels 
WHERE status = 'active';

-- Check expiring webhooks (next 24 hours)
SELECT channel_id, expiration 
FROM webhook_channels 
WHERE status = 'active' 
AND CAST(expiration AS BIGINT) < EXTRACT(EPOCH FROM NOW() + INTERVAL '24 hours') * 1000;
```

### Performance Monitoring
- Monitor response times for `/chat` endpoint
- Check Qdrant collection size and performance
- Monitor database connection pool usage
- Track webhook renewal success rate

## Troubleshooting

### Common Issues

#### 1. **Database Connection Failed**
- **Cause**: Incorrect DATABASE_URL
- **Solution**: Verify connection string format and credentials

#### 2. **Webhook Creation Failed**
- **Cause**: Missing WEBHOOK_BASE_URL or GDRIVE_ROOT_ID
- **Solution**: Set environment variables and restart app

#### 3. **File Upload Not Working**
- **Cause**: Google Drive permissions or webhook not active
- **Solution**: Check webhook status in database, verify Google Drive permissions

#### 4. **Migration Failed**
- **Cause**: Database permissions or existing data conflicts
- **Solution**: Check logs, run manual migration script

### Log Analysis
```bash
# Check recent application logs
# On Render: View logs in dashboard
# On DigitalOcean: Use doctl or dashboard
# Local: Check console output

# Look for these patterns:
# ERROR: Failed to connect to database
# INFO: Successfully migrated webhook channels
# WARNING: Webhook expiring soon
```

## Security Considerations

### 1. **Environment Variables**
- Never commit secrets to git
- Use platform-specific secret management
- Rotate secrets regularly

### 2. **Database Security**
- Use SSL connections
- Restrict database access by IP
- Regular backups

### 3. **API Security**
- Enable HTTPS only
- Implement rate limiting
- Validate all inputs
- Use proper authentication

### 4. **Google Drive Integration**
- Use service accounts with minimal permissions
- Regularly rotate service account keys
- Monitor API usage

## Scaling Considerations

### Horizontal Scaling
- Database connection pooling
- Shared webhook channel management
- Stateless application design

### Vertical Scaling
- Monitor memory usage for vector operations
- Database query optimization
- Efficient file processing

### Performance Optimization
- Index database queries
- Cache frequently accessed data
- Optimize Qdrant collection settings
- Implement request caching

## Backup and Recovery

### Database Backups
- Automated daily backups (most platforms provide this)
- Test restore procedures
- Document recovery steps

### Configuration Backups
- Export environment variables
- Document deployment configurations
- Version control deployment scripts

This completes the production-ready deployment setup for your Orris RAG API! 🚀
