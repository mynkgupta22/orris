import os
import io
import logging
from typing import List, Dict, Optional
from datetime import datetime
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from googleapiclient.http import MediaIoBaseDownload
from config import Config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class GoogleDriveClient:
    """Google Drive client for fetching files from structured folder layout"""
    
    SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
    
    def __init__(self):
        self.service = self._authenticate()
        self.evidev_data_folder_id = Config.EVIDEV_DATA_FOLDER_ID
        
    def _authenticate(self):
        """Authenticate using service account"""
        try:
            credentials = service_account.Credentials.from_service_account_file(
                Config.GOOGLE_SERVICE_ACCOUNT_PATH, 
                scopes=self.SCOPES
            )
            service = build('drive', 'v3', credentials=credentials)
            logger.info("Successfully authenticated with Google Drive")
            return service
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    def get_folder_structure(self) -> Dict[str, str]:
        """Get NON PI and PI folder IDs"""
        try:
            # Get children of EVIDEV_DATA folder
            results = self.service.files().list(
                q=f"'{self.evidev_data_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            
            folders = {}
            for folder in results.get('files', []):
                folders[folder['name']] = folder['id']
            
            logger.info(f"Found folders: {list(folders.keys())}")
            return folders
            
        except Exception as e:
            logger.error(f"Failed to get folder structure: {e}")
            raise
    
    def get_pi_subfolders(self, pi_folder_id: str) -> Dict[str, str]:
        """Get all uid subfolders in PI folder"""
        try:
            results = self.service.files().list(
                q=f"'{pi_folder_id}' in parents and mimeType='application/vnd.google-apps.folder'",
                fields="files(id, name)"
            ).execute()
            
            subfolders = {}
            for folder in results.get('files', []):
                subfolders[folder['name']] = folder['id']  # name = uid (e.g., 'a20')
            
            logger.info(f"Found PI subfolders: {list(subfolders.keys())}")
            return subfolders
            
        except Exception as e:
            logger.error(f"Failed to get PI subfolders: {e}")
            raise
    
    def list_files_in_folder(self, folder_id: str) -> List[Dict]:
        """List all files in a folder (non-recursively)"""
        try:
            query = f"'{folder_id}' in parents and mimeType != 'application/vnd.google-apps.folder'"
            results = self.service.files().list(
                q=query,
                fields="files(id, name, mimeType, createdTime, owners, parents)"
            ).execute()
            
            files = results.get('files', [])
            logger.info(f"Found {len(files)} files in folder {folder_id}")
            return files
            
        except Exception as e:
            logger.error(f"Failed to list files in folder {folder_id}: {e}")
            raise
    
    def download_file(self, file_id: str, file_name: str) -> str:
        """Download file to temp directory and return local path"""
        try:
            # Ensure temp directory exists
            os.makedirs(Config.TEMP_DIR, exist_ok=True)
            
            # Download file
            request = self.service.files().get_media(fileId=file_id)
            local_path = os.path.join(Config.TEMP_DIR, file_name)
            
            with io.FileIO(local_path, 'wb') as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
            
            logger.info(f"Downloaded {file_name} to {local_path}")
            return local_path
            
        except Exception as e:
            logger.error(f"Failed to download file {file_id}: {e}")
            raise
    
    def fetch_all_files(self) -> List[Dict]:
        """Fetch all files from both NON PI and PI folders with metadata"""
        all_files = []
        
        try:
            # Get folder structure
            folders = self.get_folder_structure()
            
            # Process NON PI folder
            if 'NON PI' in folders:
                non_pi_files = self.list_files_in_folder(folders['NON PI'])
                for file_info in non_pi_files:
                    metadata = self._create_file_metadata(
                        file_info, 
                        parent_folder_type='NON_PI',
                        uid=None
                    )
                    all_files.append(metadata)
            
            # Process PI folder and subfolders
            if 'PI' in folders:
                pi_subfolders = self.get_pi_subfolders(folders['PI'])
                for uid, subfolder_id in pi_subfolders.items():
                    pi_files = self.list_files_in_folder(subfolder_id)
                    for file_info in pi_files:
                        metadata = self._create_file_metadata(
                            file_info,
                            parent_folder_type='PI',
                            uid=uid
                        )
                        all_files.append(metadata)
            
            logger.info(f"Total files found: {len(all_files)}")
            return all_files
            
        except Exception as e:
            logger.error(f"Failed to fetch all files: {e}")
            raise
    
    def _create_file_metadata(self, file_info: Dict, parent_folder_type: str, uid: Optional[str]) -> Dict:
        """Create metadata object for a file"""
        owner_email = file_info.get('owners', [{}])[0].get('emailAddress', 'unknown')
        
        metadata = {
            'file_id': file_info['id'],
            'file_name': file_info['name'],
            'mime_type': file_info['mimeType'],
            'created_at': file_info['createdTime'],
            'owner_email': owner_email,
            'parent_folder_type': parent_folder_type,
            'uid': uid
        }
        
        return metadata

# Test function for visibility
def test_google_drive_connection():
    """Test function to verify Google Drive connection and list files"""
    try:
        Config.validate()
        client = GoogleDriveClient()
        
        print("Testing Google Drive connection...")
        folders = client.get_folder_structure()
        print(f"Available folders: {folders}")
        
        files = client.fetch_all_files()
        print(f"\nFound {len(files)} total files:")
        
        for file_meta in files[:5]:  # Show first 5 files
            print(f"- {file_meta['file_name']} ({file_meta['parent_folder_type']})")
            if file_meta['uid']:
                print(f"  UID: {file_meta['uid']}")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    test_google_drive_connection()