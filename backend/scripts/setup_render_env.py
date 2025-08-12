#!/usr/bin/env python3
"""
Script to help identify required environment variables for Render deployment.
Run this locally to see what variables you need to set in your Render dashboard.
"""

import os
from pathlib import Path

def check_environment_variables():
    """Check which environment variables are set and which are missing"""
    
    required_vars = {
        "WEBHOOK_BASE_URL": "Your Render app URL (e.g., https://orris-backend.onrender.com)",
        "GOOGLE_APPLICATION_CREDENTIALS_JSON": "Google service account JSON content",
        "EVIDEV_DATA_FOLDER_ID": "Main Google Drive folder ID",
        "NOMIC_API_KEY": "Nomic API key for embeddings",
        "QDRANT_URL": "Qdrant cloud URL",
        "QDRANT_API_KEY": "Qdrant API key",
    }
    
    optional_vars = {
        "INGEST_TMP_DIR": "/tmp (default)",
        "TEMP_DIR": "/tmp (default)",
        "GOOGLE_DRIVE_SCOPES": "https://www.googleapis.com/auth/drive.readonly (default)",
        "GOOGLE_WEBHOOK_TOKEN": "orris-webhook-token (default)",
        "USE_VISION": "true (default)",
        "CHUNK_SIZE": "800 (default)",
        "CHUNK_OVERLAP": "50 (default)",
    }
    
    print("=== REQUIRED ENVIRONMENT VARIABLES ===\n")
    
    missing_required = []
    for var, description in required_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: SET")
            if var == "GOOGLE_APPLICATION_CREDENTIALS_JSON":
                print(f"   Content preview: {value[:50]}...")
            else:
                print(f"   Value: {value}")
        else:
            print(f"❌ {var}: MISSING")
            print(f"   Description: {description}")
            missing_required.append(var)
        print()
    
    print("=== OPTIONAL ENVIRONMENT VARIABLES ===\n")
    
    for var, description in optional_vars.items():
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {value}")
        else:
            print(f"⚠️  {var}: Using default ({description})")
        print()
    
    if missing_required:
        print("=== ACTION REQUIRED ===")
        print("You need to set these environment variables in your Render dashboard:")
        for var in missing_required:
            print(f"  - {var}")
        print("\nGo to your Render dashboard → Your App → Environment → Environment Variables")
    else:
        print("✅ All required environment variables are set!")

if __name__ == "__main__":
    check_environment_variables()
