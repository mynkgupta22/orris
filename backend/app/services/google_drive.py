from typing import List, Dict, Any, Optional
import json
import httpx
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings


class GoogleDriveDocument:
    def __init__(self, id: str, name: str, content: str, is_pi_restricted: bool = False, metadata: Dict = None):
        self.id = id
        self.name = name
        self.content = content
        self.is_pi_restricted = is_pi_restricted
        self.metadata = metadata or {}


class GoogleDriveService:
    def __init__(self):
        self.folder_id = settings.google_drive_folder_id
        self.scopes = ['https://www.googleapis.com/auth/drive.readonly']

    def _build_service(self, access_token: str):
        """Build Google Drive service with access token"""
        credentials = Credentials(token=access_token)
        return build('drive', 'v3', credentials=credentials)

    async def list_documents(self, access_token: str) -> List[Dict[str, Any]]:
        """List all documents in the specified Google Drive folder"""
        try:
            service = self._build_service(access_token)
            
            # Query to get all files in the specified folder
            query = f"'{self.folder_id}' in parents and trashed=false"
            
            results = service.files().list(
                q=query,
                pageSize=100,
                fields="nextPageToken, files(id, name, mimeType, size, modifiedTime, parents)"
            ).execute()
            
            items = results.get('files', [])
            
            documents = []
            for item in items:
                # Check if document contains PI information based on name or metadata
                is_pi_restricted = self._is_pi_restricted(item['name'])
                
                documents.append({
                    'id': item['id'],
                    'name': item['name'],
                    'mimeType': item['mimeType'],
                    'size': item.get('size', '0'),
                    'modifiedTime': item['modifiedTime'],
                    'is_pi_restricted': is_pi_restricted
                })
            
            return documents
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []

    async def get_document_content(self, document_id: str, access_token: str) -> Optional[str]:
        """Get content of a specific document"""
        try:
            service = self._build_service(access_token)
            
            # Get file metadata first
            file_metadata = service.files().get(fileId=document_id).execute()
            mime_type = file_metadata.get('mimeType', '')
            
            # Handle different file types
            if mime_type == 'application/vnd.google-apps.document':
                # Google Docs - export as plain text
                content = service.files().export(
                    fileId=document_id,
                    mimeType='text/plain'
                ).execute()
                return content.decode('utf-8')
                
            elif mime_type == 'text/plain':
                # Plain text file
                content = service.files().get_media(fileId=document_id).execute()
                return content.decode('utf-8')
                
            elif 'text/' in mime_type:
                # Other text files
                content = service.files().get_media(fileId=document_id).execute()
                return content.decode('utf-8')
                
            else:
                # Unsupported file type
                return f"Unsupported file type: {mime_type}"
                
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None

    def _is_pi_restricted(self, filename: str) -> bool:
        """Determine if a document contains PI information based on filename or content"""
        # Simple heuristic: check for keywords that indicate PI content
        pi_keywords = [
            'personal', 'private', 'confidential', 'sensitive',
            'employee', 'payroll', 'salary', 'ssn', 'social',
            'medical', 'health', 'patient', 'customer_data',
            'financials', 'bank', 'account', 'credit'
        ]
        
        filename_lower = filename.lower()
        return any(keyword in filename_lower for keyword in pi_keywords)

    async def search_documents(self, query: str, access_token: str, user_has_pi_access: bool = False) -> List[GoogleDriveDocument]:
        """Search documents based on query and user access level"""
        try:
            # First get all documents
            documents = await self.list_documents(access_token)
            
            # Filter based on user access level
            accessible_docs = []
            for doc in documents:
                if doc['is_pi_restricted'] and not user_has_pi_access:
                    continue  # Skip PI restricted documents for users without access
                
                # Get document content for search
                content = await self.get_document_content(doc['id'], access_token)
                if content and (query.lower() in doc['name'].lower() or query.lower() in content.lower()):
                    accessible_docs.append(GoogleDriveDocument(
                        id=doc['id'],
                        name=doc['name'],
                        content=content[:1000],  # Limit content length for response
                        is_pi_restricted=doc['is_pi_restricted'],
                        metadata=doc
                    ))
            
            return accessible_docs
            
        except Exception as error:
            print(f"Search error: {error}")
            return []

    async def get_service_account_token(self) -> str:
        """Get service account token for API access"""
        # This would typically use a service account key file
        # For now, return a placeholder - in production, implement proper service account auth
        return "service_account_token_placeholder"