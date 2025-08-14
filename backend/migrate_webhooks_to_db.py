"""
Database Migration Script for Webhook Channels
This script helps migrate webhook channels from JSON file to PostgreSQL database.
Run this once during deployment to migrate existing data.
"""

import os
import sys
import logging

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.webhook_renewal import migrate_json_to_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    print("🔄 Webhook Channels Database Migration")
    print("=" * 50)

    try:
        migrated_count = migrate_json_to_database()

        if migrated_count > 0:
            print(f"✅ Successfully migrated {migrated_count} webhook channels to database")
            print("📝 You can now safely remove the webhook_channels.json file")
        elif migrated_count == 0:
            print("ℹ️  No webhook channels found to migrate or already migrated")

        print("\n🚀 Database migration completed!")
        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)