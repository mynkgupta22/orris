import logging
from typing import List, Dict
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PITagger:
    """Tag chunks with PI (Personally Identifiable) information based on folder structure only"""
    
    def __init__(self):
        logger.info("Initialized PI Tagger with folder-based classification")
    
    def tag_chunks(self, chunks: List[Dict]) -> List[Dict]:
        """Tag all chunks with PI information based on folder structure"""
        tagged_chunks = []
        
        pi_count = 0
        non_pi_count = 0
        
        for chunk in chunks:
            tagged_chunk = self.tag_single_chunk(chunk)
            tagged_chunks.append(tagged_chunk)
            
            if tagged_chunk['is_pi']:
                pi_count += 1
            else:
                non_pi_count += 1
        
        logger.info(f"Tagged {len(tagged_chunks)} chunks: {pi_count} PI, {non_pi_count} Non-PI")
        return tagged_chunks
    
    def tag_single_chunk(self, chunk: Dict) -> Dict:
        """Tag a single chunk with PI information based on folder structure"""
        # Apply folder-based classification
        chunk = self._apply_folder_based_classification(chunk)
        
        # Add security metadata
        chunk = self._add_security_metadata(chunk)
        
        # Validate the result
        if not self._validate_classification(chunk):
            raise ValueError(f"Invalid classification for chunk {chunk.get('chunk_id', 'unknown')}")
        
        return chunk
    
    def _apply_folder_based_classification(self, chunk: Dict) -> Dict:
        """Apply PI classification based on folder structure"""
        folder_type = chunk.get('folder_type')
        uid = chunk.get('uid')
        
        if folder_type == 'PI':
            # Files in PI/<uid>/ folders
            if not uid:
                logger.warning(f"PI folder chunk missing UID: {chunk.get('chunk_id', 'unknown')}")
                # Fail safe - if in PI folder but no UID, still mark as PI
            
            chunk['is_pi'] = True
            chunk['access_roles'] = ['pi']
            # Preserve the existing uid (should be set from file metadata)
            
        elif folder_type == 'NON_PI':
            # Files in NON PI/ folder
            chunk['is_pi'] = False
            chunk['access_roles'] = ['non_pi']
            chunk['uid'] = None  # Ensure no UID for non-PI
            
        else:
            # Unknown folder type - fail safe to PI for security
            logger.error(f"Unknown folder_type '{folder_type}' for chunk {chunk.get('chunk_id', 'unknown')} - defaulting to PI")
            chunk['is_pi'] = True
            chunk['access_roles'] = ['pi']
        
        return chunk
    
    def _add_security_metadata(self, chunk: Dict) -> Dict:
        """Add security-related metadata fields"""
        # Update timestamp
        chunk['ingested_at'] = datetime.now().isoformat()
        
        # Security level based on PI status
        chunk['security_level'] = 'HIGH' if chunk['is_pi'] else 'PUBLIC'
        
        # Authentication requirement
        chunk['requires_auth'] = chunk['is_pi']
        
        # Data classification
        chunk['data_classification'] = 'PERSONAL_DATA' if chunk['is_pi'] else 'PUBLIC_DATA'
        
        return chunk
    
    def _validate_classification(self, chunk: Dict) -> bool:
        """Validate that chunk classification is consistent and secure"""
        try:
            folder_type = chunk.get('folder_type')
            is_pi = chunk.get('is_pi')
            access_roles = chunk.get('access_roles', [])
            uid = chunk.get('uid')
            
            # Validate folder_type matches is_pi
            if folder_type == 'PI' and not is_pi:
                logger.error(f"Inconsistent: PI folder but is_pi=False for chunk {chunk.get('chunk_id')}")
                return False
            
            if folder_type == 'NON_PI' and is_pi:
                logger.error(f"Inconsistent: NON_PI folder but is_pi=True for chunk {chunk.get('chunk_id')}")
                return False
            
            # Validate access_roles match is_pi
            if is_pi and 'pi' not in access_roles:
                logger.error(f"Inconsistent: is_pi=True but 'pi' not in access_roles for chunk {chunk.get('chunk_id')}")
                return False
            
            if not is_pi and 'non_pi' not in access_roles:
                logger.error(f"Inconsistent: is_pi=False but 'non_pi' not in access_roles for chunk {chunk.get('chunk_id')}")
                return False
            
            # Validate UID consistency
            if folder_type == 'PI' and not uid:
                logger.warning(f"PI folder chunk missing UID: {chunk.get('chunk_id')} - this may be acceptable")
            
            if folder_type == 'NON_PI' and uid:
                logger.error(f"NON_PI folder chunk has UID: {chunk.get('chunk_id')}")
                return False
            
            # Validate required security fields
            required_security_fields = ['security_level', 'requires_auth', 'data_classification']
            for field in required_security_fields:
                if field not in chunk:
                    logger.error(f"Missing security field '{field}' for chunk {chunk.get('chunk_id')}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Validation error for chunk {chunk.get('chunk_id', 'unknown')}: {e}")
            return False

def validate_chunk_metadata(chunk: Dict) -> bool:
    """Validate that chunk has all required metadata fields"""
    required_fields = [
        # Core identification
        'chunk_id', 'text', 'source_doc_id', 'source_doc_name',
        
        # Source information
        'folder_type', 'owner_email', 'uploaded_by', 'doc_type',
        'created_at', 'ingested_at',
        
        # PI classification
        'is_pi', 'access_roles', 'uid',
        
        # Document structure
        'chunk_index', 'source_page', 'language', 'token_count',
        'is_table', 'is_image', 'doc_url',
        
        # Security metadata
        'security_level', 'requires_auth', 'data_classification'
    ]
    
    missing_fields = []
    for field in required_fields:
        if field not in chunk:
            missing_fields.append(field)
    
    if missing_fields:
        logger.error(f"Chunk {chunk.get('chunk_id', 'unknown')} missing fields: {missing_fields}")
        return False
    
    # Validate critical field types
    if not isinstance(chunk['is_pi'], bool):
        logger.error(f"Chunk {chunk['chunk_id']}: is_pi must be boolean, got {type(chunk['is_pi'])}")
        return False
    
    if not isinstance(chunk['access_roles'], list):
        logger.error(f"Chunk {chunk['chunk_id']}: access_roles must be list, got {type(chunk['access_roles'])}")
        return False
    
    if chunk['folder_type'] not in ['PI', 'NON_PI']:
        logger.error(f"Chunk {chunk['chunk_id']}: invalid folder_type '{chunk['folder_type']}'")
        return False
    
    return True

def get_classification_summary(chunks: List[Dict]) -> Dict:
    """Get summary of chunk classifications"""
    summary = {
        'total_chunks': len(chunks),
        'pi_chunks': 0,
        'non_pi_chunks': 0,
        'pi_uids': set(),
        'validation_errors': 0
    }
    
    for chunk in chunks:
        if chunk.get('is_pi'):
            summary['pi_chunks'] += 1
            if chunk.get('uid'):
                summary['pi_uids'].add(chunk['uid'])
        else:
            summary['non_pi_chunks'] += 1
        
        if not validate_chunk_metadata(chunk):
            summary['validation_errors'] += 1
    
    summary['pi_uids'] = list(summary['pi_uids'])  # Convert set to list
    return summary

# Test function
def test_pi_tagging():
    """Test PI tagging with sample chunks"""
    tagger = PITagger()
    
    # Create test chunks with different folder types
    test_chunks = [
        {
            'chunk_id': 'test_non_pi_1',
            'text': 'This is a general company policy document.',
            'source_doc_id': 'doc_1',
            'source_doc_name': 'policies.pdf',
            'folder_type': 'NON_PI',
            'owner_email': 'admin@company.com',
            'uploaded_by': 'ingest_service',
            'doc_type': 'pdf',
            'created_at': '2024-01-01T00:00:00Z',
            'chunk_index': 0,
            'source_page': 1,
            'language': 'en',
            'token_count': 10,
            'is_table': False,
            'is_image': False,
            'doc_url': 'https://drive.google.com/file/d/doc_1/view',
            'uid': None  # NON_PI should have no UID
        },
        {
            'chunk_id': 'test_pi_1',
            'text': 'Personal information for user a20.',
            'source_doc_id': 'doc_2',
            'source_doc_name': 'user_data.pdf',
            'folder_type': 'PI',
            'owner_email': 'user@company.com',
            'uploaded_by': 'ingest_service',
            'doc_type': 'pdf',
            'created_at': '2024-01-01T00:00:00Z',
            'chunk_index': 0,
            'source_page': 1,
            'language': 'en',
            'token_count': 8,
            'is_table': False,
            'is_image': False,
            'doc_url': 'https://drive.google.com/file/d/doc_2/view',
            'uid': 'a20'  # PI should have UID
        },
        {
            'chunk_id': 'test_pi_2',
            'text': 'Another document for user a21.',
            'source_doc_id': 'doc_3',
            'source_doc_name': 'profile.docx',
            'folder_type': 'PI',
            'owner_email': 'user2@company.com',
            'uploaded_by': 'ingest_service',
            'doc_type': 'docx',
            'created_at': '2024-01-02T00:00:00Z',
            'chunk_index': 0,
            'source_page': 1,
            'language': 'en',
            'token_count': 6,
            'is_table': False,
            'is_image': False,
            'doc_url': 'https://drive.google.com/file/d/doc_3/view',
            'uid': 'a21'
        }
    ]
    
    print("PI Tagging Test - Folder-Based Classification")
    print("=" * 50)
    
    # Tag chunks
    tagged_chunks = tagger.tag_chunks(test_chunks)
    
    # Display results
    for chunk in tagged_chunks:
        print(f"\nChunk: {chunk['chunk_id']}")
        print(f"  Folder Type: {chunk['folder_type']}")
        print(f"  Is PI: {chunk['is_pi']}")
        print(f"  Access Roles: {chunk['access_roles']}")
        print(f"  UID: {chunk.get('uid', 'None')}")
        print(f"  Security Level: {chunk['security_level']}")
        print(f"  Requires Auth: {chunk['requires_auth']}")
        
        # Validate
        is_valid = validate_chunk_metadata(chunk)
        print(f"  Valid: {is_valid}")
    
    # Get summary
    summary = get_classification_summary(tagged_chunks)
    print(f"\nSummary:")
    print(f"  Total: {summary['total_chunks']}")
    print(f"  PI: {summary['pi_chunks']}")
    print(f"  Non-PI: {summary['non_pi_chunks']}")
    print(f"  UIDs: {summary['pi_uids']}")
    print(f"  Validation Errors: {summary['validation_errors']}")
    
    return tagged_chunks

if __name__ == "__main__":
    test_pi_tagging()