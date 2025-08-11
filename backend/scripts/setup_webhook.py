import os
import sys

sys.path.append('.')

from app.services.sync_service import setup_drive_webhook

webhook_url = f"{os.getenv('WEBHOOK_BASE_URL')}/webhooks/google-drive"
folder_id = os.getenv('GDRIVE_ROOT_ID')

print(f"Setting up webhook for folder: {folder_id}")
print(f"Webhook URL: {webhook_url}")

if folder_id:
    try:
        result = setup_drive_webhook(webhook_url, folder_id)
        print(f"✅ Webhook setup successful: {result}")
    except Exception as e:
        print(f"❌ Webhook setup failed: {e}")
else:
    print("❌ GDRIVE_ROOT_ID not set")
