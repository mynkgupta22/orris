#!/usr/bin/env python3
"""
Comprehensive Webhook Debugging Tool
This script helps diagnose webhook issues step by step
"""

import os
import json
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

# Import our app modules
from app.core.database import SessionLocal
from app.services.webhook_channel_service import WebhookChannelService
from app.rag.integrations.drive import get_drive_service

load_dotenv('config/.env')

class WebhookDebugger:
    def __init__(self):
        self.webhook_base_url = os.getenv('WEBHOOK_BASE_URL')
        self.gdrive_root_id = os.getenv('GDRIVE_ROOT_ID')
        self.db = SessionLocal()
    
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
    
    def check_1_environment(self):
        """Check environment configuration"""
        print("🔧 STEP 1: Environment Configuration")
        print("=" * 50)
        
        required_vars = [
            'WEBHOOK_BASE_URL',
            'GDRIVE_ROOT_ID',
            'GOOGLE_APPLICATION_CREDENTIALS',
        ]
        
        for var in required_vars:
            value = os.getenv(var)
            if value:
                if 'CREDENTIALS' in var:
                    # Check if file exists
                    if os.path.exists(value):
                        print(f"✅ {var}: File exists")
                    else:
                        print(f"❌ {var}: File NOT found at {value}")
                else:
                    print(f"✅ {var}: {value}")
            else:
                print(f"❌ {var}: NOT SET")
        print()
    
    def check_2_app_status(self):
        """Check if FastAPI app is running"""
        print("🚀 STEP 2: FastAPI Application Status")
        print("=" * 50)
        
        try:
            response = requests.get('http://localhost:8001/health', timeout=3)
            print(f"✅ FastAPI app: Running (HTTP {response.status_code})")
            
            # Check if webhook endpoint exists
            webhook_test = requests.get('http://localhost:8001/docs', timeout=3)
            print(f"✅ API docs: Available (HTTP {webhook_test.status_code})")
            
        except requests.exceptions.ConnectionError:
            print("❌ FastAPI app: NOT RUNNING")
            print("   Solution: Run 'uvicorn main:app --host 0.0.0.0 --port 8001 --reload'")
        except Exception as e:
            print(f"❌ FastAPI app: Error - {e}")
        print()
    
    def check_3_ngrok_status(self):
        """Check ngrok tunnel status"""
        print("🌐 STEP 3: Ngrok Tunnel Status")
        print("=" * 50)
        
        if not self.webhook_base_url:
            print("❌ No WEBHOOK_BASE_URL configured")
            return
        
        try:
            # Test ngrok URL
            response = requests.get(f"{self.webhook_base_url}/health", timeout=5)
            print(f"✅ Ngrok tunnel: Working (HTTP {response.status_code})")
            
            # Test webhook endpoint specifically
            webhook_url = f"{self.webhook_base_url}/webhooks/google-drive"
            test_data = {"test": "ping"}
            webhook_response = requests.post(webhook_url, json=test_data, timeout=5)
            print(f"✅ Webhook endpoint: Responding (HTTP {webhook_response.status_code})")
            
        except requests.exceptions.Timeout:
            print("❌ Ngrok tunnel: TIMEOUT")
            print("   Solution: Check if ngrok is running and restart if needed")
        except requests.exceptions.ConnectionError:
            print("❌ Ngrok tunnel: CONNECTION FAILED")
            print("   Solution: Start new ngrok session: 'ngrok http 8001'")
        except Exception as e:
            print(f"❌ Ngrok tunnel: Error - {e}")
        print()
    
    def check_4_database_webhooks(self):
        """Check webhook registration in database"""
        print("💾 STEP 4: Database Webhook Registration")
        print("=" * 50)
        
        try:
            active_webhooks = WebhookChannelService.get_active_webhook_channels(self.db)
            print(f"📊 Active webhooks in database: {len(active_webhooks)}")
            
            if not active_webhooks:
                print("❌ No active webhooks found in database")
                print("   Solution: Register webhook using webhook setup script")
                return
            
            for i, webhook in enumerate(active_webhooks, 1):
                print(f"\n   Webhook {i}:")
                print(f"     Channel ID: {webhook.channel_id}")
                print(f"     Resource ID: {webhook.resource_id}")
                print(f"     Folder ID: {webhook.folder_id}")
                print(f"     Webhook URL: {webhook.webhook_url}")
                
                # Check expiration
                if webhook.expiration:
                    exp_time = int(webhook.expiration) / 1000
                    current_time = time.time()
                    hours_left = (exp_time - current_time) / 3600
                    
                    if hours_left > 0:
                        print(f"     Status: ✅ Valid ({hours_left:.1f}h remaining)")
                    else:
                        print(f"     Status: ❌ EXPIRED ({abs(hours_left):.1f}h ago)")
                        print("     Solution: Run webhook renewal service")
                
        except Exception as e:
            print(f"❌ Database error: {e}")
        print()
    
    def check_5_google_drive_access(self):
        """Check Google Drive API access"""
        print("📁 STEP 5: Google Drive API Access")
        print("=" * 50)
        
        try:
            drive_service = get_drive_service()
            print("✅ Google Drive API: Connected")
            
            # Test folder access
            if self.gdrive_root_id:
                folder = drive_service.files().get(fileId=self.gdrive_root_id).execute()
                print(f"✅ Target folder: '{folder['name']}'")
                
                # List recent files
                query = f"'{self.gdrive_root_id}' in parents"
                results = drive_service.files().list(
                    q=query,
                    fields='files(id, name, mimeType, modifiedTime)',
                    orderBy='modifiedTime desc',
                    pageSize=3
                ).execute()
                
                files = results.get('files', [])
                print(f"📁 Files in folder: {len(files)}")
                if files:
                    print("   Recent files:")
                    for file in files[:3]:
                        print(f"     - {file['name']} ({file['modifiedTime']})")
            
        except Exception as e:
            print(f"❌ Google Drive API: Error - {e}")
        print()
    
    def check_6_webhook_test(self):
        """Perform manual webhook test"""
        print("🧪 STEP 6: Manual Webhook Test")
        print("=" * 50)
        
        if not self.webhook_base_url:
            print("❌ Cannot test - no webhook URL")
            return
        
        webhook_url = f"{self.webhook_base_url}/webhooks/google-drive"
        
        # Simulate Google Drive webhook payload
        test_payload = {
            "message": {
                "data": "eyJ0ZXN0IjogInRydWUifQ==",  # base64 encoded {"test": "true"}
                "messageId": f"test-{int(time.time())}",
                "publishTime": datetime.utcnow().isoformat() + "Z"
            }
        }
        
        try:
            print(f"🔄 Sending test webhook to: {webhook_url}")
            response = requests.post(
                webhook_url, 
                json=test_payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            print(f"✅ Test webhook response: HTTP {response.status_code}")
            if response.text:
                print(f"   Response: {response.text[:200]}...")
            
        except Exception as e:
            print(f"❌ Test webhook failed: {e}")
        print()
    
    def check_7_recent_logs(self):
        """Check for recent webhook activity"""
        print("📋 STEP 7: Recent Activity Check")
        print("=" * 50)
        
        # This would check application logs in a real scenario
        print("💡 To monitor real-time webhook activity:")
        print("   1. Upload a file to Google Drive")
        print("   2. Watch FastAPI terminal for incoming requests")
        print("   3. Look for POST requests to /webhooks/google-drive")
        print("   4. Check for sync processing logs")
        print()
    
    def run_full_diagnostic(self):
        """Run complete webhook diagnostic"""
        print("🔍 WEBHOOK DIAGNOSTIC REPORT")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        print()
        
        self.check_1_environment()
        self.check_2_app_status()
        self.check_3_ngrok_status()
        self.check_4_database_webhooks()
        self.check_5_google_drive_access()
        self.check_6_webhook_test()
        self.check_7_recent_logs()
        
        print("🎯 NEXT STEPS:")
        print("=" * 50)
        print("1. Fix any ❌ issues found above")
        print("2. Upload a test file to Google Drive")
        print("3. Monitor FastAPI logs for webhook calls")
        print("4. If still not working, check Google Drive webhook delays (can take 1-5 minutes)")

if __name__ == "__main__":
    debugger = WebhookDebugger()
    debugger.run_full_diagnostic()
