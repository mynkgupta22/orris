# Webhook Channels Database Migration

## Overview

This migration moves webhook channel management from JSON file storage to PostgreSQL database storage for better reliability, concurrency, and production deployment.

## Changes Made

### 1. **New Database Model**
- **File**: `app/models/webhook_channel.py`
- **Table**: `webhook_channels`
- **Fields**:
  - `id` (Primary Key)
  - `channel_id` (Unique, Indexed)
  - `resource_id`
  - `folder_id` (Indexed)
  - `webhook_url`
  - `description`
  - `expiration`
  - `status` (Indexed)
  - `created_at`
  - `updated_at`

### 2. **New Service Layer**
- **File**: `app/services/webhook_channel_service.py`
- **Features**:
  - CRUD operations for webhook channels
  - Automatic session management
  - Migration from JSON file
  - Expiration detection

### 3. **Updated Services**
- **webhook_renewal.py**: Now uses database instead of JSON
- **sync_service.py**: Updated folder ID lookup to use database
- **main.py**: Added automatic migration and initialization

### 4. **Database Migration**
- **File**: `alembic/versions/2025_08_13_1200-add_webhook_channels_add_webhook_channels_table.py`
- Creates the `webhook_channels` table with proper indexes

## Deployment Instructions

### For New Deployments (No Existing Data)

1. **Set Environment Variables**:
   ```bash
   WEBHOOK_BASE_URL=https://your-app.onrender.com
   GDRIVE_ROOT_ID=your-google-drive-folder-id
   DATABASE_URL=postgresql://username:password@host:port/database
   ```

2. **Run Database Migration**:
   ```bash
   alembic upgrade head
   ```

3. **Start Application**:
   ```bash
   python main.py
   ```
   
   The app will automatically:
   - Create webhook channels table
   - Initialize webhooks if environment variables are set
   - Start the renewal service

### For Existing Deployments (With JSON Data)

1. **Set Environment Variables** (same as above)

2. **Run Database Migration**:
   ```bash
   alembic upgrade head
   ```

3. **Migrate Existing Data** (Optional - done automatically):
   ```bash
   python scripts/migrate_webhooks_to_db.py
   ```

4. **Start Application**:
   ```bash
   python main.py
   ```
   
   The app will automatically:
   - Migrate existing JSON data to database (if any)
   - Initialize new webhooks if needed
   - Start the renewal service

## Migration Process

### Automatic Migration (Recommended)
The application automatically migrates data on startup:

1. **Checks for existing JSON file**
2. **Migrates data to database** if file exists
3. **Initializes new webhooks** if none exist in database
4. **Starts renewal service** using database

### Manual Migration
If you prefer manual control:

```bash
# Run migration script
python scripts/migrate_webhooks_to_db.py

# Verify migration
# Check database: SELECT * FROM webhook_channels;
```

## Key Benefits

### 1. **Production Ready**
- ✅ No file system dependencies
- ✅ Better concurrency handling
- ✅ Atomic operations
- ✅ Proper indexing for performance

### 2. **Reliability**
- ✅ ACID transactions
- ✅ No file corruption risks
- ✅ Better error handling
- ✅ Automatic session management

### 3. **Scalability**
- ✅ Supports multiple app instances
- ✅ Database-level locking
- ✅ Better query performance
- ✅ Easier monitoring and debugging

## Database Schema

```sql
CREATE TABLE webhook_channels (
    id SERIAL PRIMARY KEY,
    channel_id VARCHAR(255) UNIQUE NOT NULL,
    resource_id VARCHAR(255) NOT NULL,
    folder_id VARCHAR(255) NOT NULL,
    webhook_url TEXT NOT NULL,
    description VARCHAR(500) DEFAULT 'Main RAG Folder',
    expiration VARCHAR(50),
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_webhook_channels_channel_id ON webhook_channels(channel_id);
CREATE INDEX ix_webhook_channels_folder_id ON webhook_channels(folder_id);
CREATE INDEX ix_webhook_channels_status ON webhook_channels(status);
```

## API Usage Examples

### Create Webhook Channel
```python
from app.services.webhook_channel_service import WebhookChannelService

channel_data = {
    "channel_id": "orris-sync-folder-123",
    "resource_id": "resource-456",
    "folder_id": "1NmJmAGWP4TMIzw4Algfl5OkiWgYdsfgh",
    "webhook_url": "https://your-app.onrender.com/webhooks/google-drive",
    "expiration": "1755098913000",
    "status": "active"
}

channel = WebhookChannelService.create_webhook_channel(db, channel_data)
```

### Get Active Channels
```python
active_channels = WebhookChannelService.get_active_webhook_channels(db)
```

### Update Channel
```python
updated_channel = WebhookChannelService.update_webhook_channel(
    db, 
    "orris-sync-folder-123", 
    {"status": "inactive"}
)
```

## Troubleshooting

### Migration Issues
- **Problem**: Migration script fails
- **Solution**: Check database connection and permissions

### Missing Webhooks
- **Problem**: No webhooks after deployment
- **Solution**: Ensure `WEBHOOK_BASE_URL` and `GDRIVE_ROOT_ID` are set

### Performance Issues
- **Problem**: Slow webhook lookups
- **Solution**: Ensure database indexes are created properly

### Data Consistency
- **Problem**: Duplicate channels
- **Solution**: Use the service layer methods which handle deduplication

## Monitoring

Monitor these aspects in production:

1. **Database Performance**:
   ```sql
   SELECT COUNT(*) FROM webhook_channels WHERE status = 'active';
   ```

2. **Webhook Expiration**:
   ```sql
   SELECT channel_id, expiration FROM webhook_channels 
   WHERE status = 'active' AND expiration < :threshold;
   ```

3. **Application Logs**:
   - Look for "Successfully renewed webhook" messages
   - Monitor "Failed to renew webhook" errors

## Rollback Plan

If issues occur, you can temporarily rollback:

1. **Stop the application**
2. **Restore JSON file** from backup
3. **Revert code changes** to use JSON file
4. **Restart application**

Note: This should only be a temporary measure. The database approach is recommended for production.
