# 🔄 Google Drive Automatic Sync Setup

This guide explains how to set up automatic synchronization between Google Drive and your RAG vector database using webhooks.

## 📋 Overview

The automatic sync system provides:
- **Real-time updates**: Documents are processed immediately when changed in Google Drive
- **Automatic deletion**: Removed documents are deleted from vector database
- **Error handling**: Failed sync attempts are tracked and can be retried
- **Deduplication**: Only changed documents are re-processed

## 🏗️ Architecture

```
Google Drive → Webhook → FastAPI → Background Tasks → Vector DB
                ↓
            Sync Tracker (Database)
```

### Components:

1. **Webhook Endpoint** (`/webhooks/google-drive`): Receives Google Drive notifications
2. **Sync Service**: Processes document changes in background
3. **Document Sync Model**: Tracks sync state in PostgreSQL
4. **Delete Functions**: Removes document chunks from Qdrant

## 🚀 Setup Instructions

### 1. Environment Configuration

Set these environment variables:

```bash
# Required for webhook functionality
export WEBHOOK_BASE_URL="https://your-domain.com"
export GOOGLE_WEBHOOK_TOKEN="your-secure-random-token"

# Existing RAG configuration
export GDRIVE_ROOT_ID="your-google-drive-folder-id"
export GOOGLE_APPLICATION_CREDENTIALS="path/to/service-account.json"

# Database configuration (existing)
export DATABASE_URL="postgresql://user:pass@localhost/dbname"

# Qdrant configuration (existing)
export QDRANT_HOST="localhost"
export QDRANT_PORT="6333"
export QDRANT_COLLECTION_NAME="documents"
```

### 2. Database Migration

Run the migration to create the document sync table:

```bash
alembic upgrade head
```

### 3. Deploy Webhook Endpoint

Your FastAPI application must be publicly accessible for Google to send webhooks.

#### Option A: Production Deployment
Deploy to a cloud provider (AWS, GCP, Heroku) with HTTPS

#### Option B: Local Testing with ngrok
```bash
# Install ngrok
# Start your FastAPI server
uvicorn main:app --host 0.0.0.0 --port 8001

# In another terminal, expose it publicly
ngrok http 8001

# Use the ngrok URL as your WEBHOOK_BASE_URL
export WEBHOOK_BASE_URL="https://abc123.ngrok.io"
```

### 4. Set Up Google Drive Webhook

Use the webhook manager to register your endpoint:

```bash
python app/rag/webhook_manager.py
```

Choose option 1 to set up webhook for your main folder.

### 5. Test the Setup

Run the test suite:

```bash
python app/rag/test_webhook.py
```

## 📊 Monitoring

### Check Webhook Status

Visit: `https://your-domain.com/webhooks/google-drive/status`

### View Sync Records

Query the database:

```sql
SELECT * FROM document_sync ORDER BY updated_at DESC LIMIT 10;
```

### Server Logs

Monitor your FastAPI logs for webhook notifications:

```
INFO: Received Google Drive webhook: channel=orris-sync-123, state=update
INFO: Queued background task for update notification
INFO: Processing Drive change: update for resource abc123
```

## 🔧 Management Commands

### Webhook Manager CLI

```bash
python app/rag/webhook_manager.py
```

Options:
1. **Setup webhook for main folder**: Registers webhook for GDRIVE_ROOT_ID
2. **Setup webhook for custom folder**: Registers webhook for specific folder
3. **Show saved channels**: Lists all registered webhooks
4. **Stop a channel**: Deactivates a webhook
5. **Test webhook setup**: Validates configuration

### Manual Sync

If webhooks fail, you can still run manual sync:

```bash
# Run full ingestion (respects sync tracking)
python app/rag/ingest.py
```

## 🔐 Security

### Webhook Verification

The webhook endpoint verifies incoming requests:

1. **Channel Token**: Matches `GOOGLE_WEBHOOK_TOKEN`
2. **Channel ID**: Must match registered channel patterns
3. **Known Channels**: Cross-references with saved channels

### Best Practices

- Use HTTPS for webhook endpoint
- Set strong `GOOGLE_WEBHOOK_TOKEN`
- Monitor webhook logs for suspicious activity
- Regularly rotate webhook tokens

## 🎯 Sync Workflow

### Document Update Flow

1. **Change Detected**: Google Drive sends webhook notification
2. **Background Processing**: Webhook queues background task
3. **Document Download**: Fetch updated document from Drive
4. **Delete Old Chunks**: Remove existing document chunks from vector DB
5. **Process Document**: Extract text, create chunks, generate embeddings
6. **Index New Chunks**: Store updated chunks in vector DB
7. **Mark Synced**: Update sync status in database

### Document Deletion Flow

1. **Deletion Detected**: Google Drive sends 'remove' or 'trash' notification
2. **Chunk Deletion**: Remove all chunks for document from vector DB
3. **Mark Deleted**: Update sync status in database

## 🐛 Troubleshooting

### Common Issues

#### Webhook Not Receiving Notifications

1. **Check URL accessibility**: Ensure webhook URL is publicly accessible
2. **Verify SSL certificate**: Google requires valid HTTPS
3. **Check Google Drive permissions**: Service account needs access to folder
4. **Review webhook expiration**: Channels expire after 24-48 hours

```bash
# Test webhook accessibility
curl -X POST https://your-domain.com/webhooks/google-drive/status

# Check webhook registration
python app/rag/webhook_manager.py  # Option 3: Show saved channels
```

#### Processing Failures

1. **Check sync status**: Query `document_sync` table for failed documents
2. **Review server logs**: Look for processing errors
3. **Verify credentials**: Ensure service account has proper permissions
4. **Check Qdrant connection**: Verify vector database is accessible

```sql
-- Find failed sync attempts
SELECT source_doc_name, error_message, retry_count, updated_at 
FROM document_sync 
WHERE sync_status = 'failed' 
ORDER BY updated_at DESC;
```

#### Database Connection Issues

```bash
# Test database connection
python -c "from app.core.database import get_sync_db; print('DB OK' if get_sync_db() else 'DB FAIL')"

# Run pending migrations
alembic upgrade head
```

### Debug Mode

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## 📈 Performance Optimization

### Batch Processing

For high-volume changes, consider implementing batch processing:

1. **Queue notifications**: Store webhook notifications in Redis/database
2. **Batch processor**: Process multiple changes together
3. **Rate limiting**: Avoid overwhelming Google Drive API

### Resource Management

- **Temporary files**: Automatically cleaned after processing
- **Memory usage**: Large documents are streamed to avoid memory issues
- **Concurrent processing**: Background tasks run concurrently

## 🔄 Backup Strategy

### Sync State Recovery

The `document_sync` table provides complete sync history:

- **Replay failed syncs**: Reprocess failed documents
- **Audit trail**: Track all document changes
- **Rollback capability**: Identify and revert problematic changes

### Manual Backup

```bash
# Export sync state
pg_dump -t document_sync your_database > sync_backup.sql

# Full vector database backup
docker exec qdrant-container /qdrant/qdrant --help  # Check backup options
```

## 🎉 Success Metrics

Monitor these metrics to ensure healthy operation:

- **Webhook success rate**: >95% of webhooks processed successfully
- **Sync latency**: Documents synced within 30 seconds of change
- **Error rate**: <5% of documents fail processing
- **Storage growth**: Vector database size matches expected growth

```sql
-- Sync success metrics
SELECT 
    sync_status, 
    COUNT(*) as count, 
    AVG(EXTRACT(EPOCH FROM (last_synced_at - created_at))) as avg_sync_time_seconds
FROM document_sync 
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY sync_status;
```

## 📞 Support

If you encounter issues:

1. **Check logs**: Review FastAPI and webhook logs
2. **Test components**: Use provided test scripts
3. **Verify configuration**: Ensure all environment variables are set
4. **Manual fallback**: Use standard ingestion if webhooks fail

The system is designed to be resilient - webhooks are an optimization over manual sync, not a replacement.