import logging
from typing import Dict, List, Optional
from qdrant_client.http import models
from app.models.user import User, UserRole

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AccessController:
    """Handles access control for RAG queries based on user roles and PI classification"""
    
    @staticmethod
    def build_access_filter(user: User) -> models.Filter:
        """Build Qdrant filter based on user role and permissions"""
        
        user_id = str(user.id)
        role = user.role
        
        logger.info(f"Building access filter for user {user_id} with role {role}")
        
        if role == UserRole.PI_ACCESS:
            # PI_ACCESS users can access:
            # 1. All non-PI documents 
            # 2. PI documents that belong to them (uid matches their user_id)
            return models.Filter(
                should=[
                    # Non-PI documents
                    models.FieldCondition(
                        key="is_pi",
                        match=models.MatchValue(value=False)
                    ),
                    # PI documents belonging to this user
                    models.Filter(
                        must=[
                            models.FieldCondition(
                                key="is_pi",
                                match=models.MatchValue(value=True)
                            ),
                            models.FieldCondition(
                                key="uid",
                                match=models.MatchValue(value=user_id)
                            )
                        ]
                    )
                ]
            )
            
        elif role == UserRole.NON_PI_ACCESS:
            # NON_PI_ACCESS users can only access non-PI documents
            return models.Filter(
                must=[
                    models.FieldCondition(
                        key="is_pi",
                        match=models.MatchValue(value=False)
                    )
                ]
            )
            
        elif role == UserRole.SIGNED_UP:
            # SIGNED_UP users can only access non-PI documents  
            return models.Filter(
                must=[
                    models.FieldCondition(
                        key="is_pi",
                        match=models.MatchValue(value=False)
                    )
                ]
            )
            
        else:
            # Default: deny access to everything for unknown roles
            logger.warning(f"Unknown role {role} for user {user_id}, denying access")
            return models.Filter(
                must=[
                    models.FieldCondition(
                        key="__nonexistent__",
                        match=models.MatchValue(value="__deny_all__")
                    )
                ]
            )
    
    @staticmethod
    def validate_chunk_access(user: User, chunk_payload: Dict) -> bool:
        """Validate if user can access a specific chunk based on its metadata"""
        
        is_pi = chunk_payload.get('is_pi', False)
        chunk_uid = chunk_payload.get('uid')
        user_id = str(user.id)
        
        if not is_pi:
            # Non-PI documents are accessible to all authenticated users
            return True
        
        # PI document - check user role and ownership
        if user.role == UserRole.PI_ACCESS:
            # PI_ACCESS users can only access their own PI documents
            return chunk_uid == user_id
        
        # NON_PI_ACCESS and SIGNED_UP users cannot access PI documents
        return False
    
    @staticmethod
    def filter_chunks_by_access(user: User, chunks: List[Dict]) -> List[Dict]:
        """Filter chunks list based on user access permissions"""
        
        accessible_chunks = []
        
        for chunk in chunks:
            payload = chunk.get('payload', {})
            if AccessController.validate_chunk_access(user, payload):
                accessible_chunks.append(chunk)
            else:
                logger.warning(
                    f"Access denied for user {user.id} to chunk {chunk.get('id', 'unknown')}"
                )
        
        logger.info(
            f"Filtered {len(chunks)} chunks to {len(accessible_chunks)} "
            f"accessible chunks for user {user.id}"
        )
        
        return accessible_chunks
    
    @staticmethod
    def get_user_access_summary(user: User) -> Dict[str, any]:
        """Get a summary of what the user can access"""
        
        summary = {
            'user_id': user.id,
            'role': user.role.value,
            'can_access_non_pi': True,  # All authenticated users can access non-PI
            'can_access_pi': user.role == UserRole.PI_ACCESS,
            'pi_access_scope': 'own_documents_only' if user.role == UserRole.PI_ACCESS else 'none'
        }
        
        return summary

def test_access_control():
    """Test access control functionality"""
    from app.models.user import User, UserRole, UserStatus
    
    # Mock users for testing
    pi_user = User()
    pi_user.id = 123
    pi_user.role = UserRole.PI_ACCESS
    pi_user.status = UserStatus.ACTIVE
    
    non_pi_user = User()
    non_pi_user.id = 456  
    non_pi_user.role = UserRole.NON_PI_ACCESS
    non_pi_user.status = UserStatus.ACTIVE
    
    signed_up_user = User()
    signed_up_user.id = 789
    signed_up_user.role = UserRole.SIGNED_UP
    signed_up_user.status = UserStatus.ACTIVE
    
    controller = AccessController()
    
    print("Access Control Test")
    print("=" * 30)
    
    # Test access summaries
    for user in [pi_user, non_pi_user, signed_up_user]:
        summary = controller.get_user_access_summary(user)
        print(f"\nUser {user.id} ({user.role.value}):")
        print(f"  Can access non-PI: {summary['can_access_non_pi']}")
        print(f"  Can access PI: {summary['can_access_pi']}")
        print(f"  PI scope: {summary['pi_access_scope']}")
    
    # Test chunk access validation
    test_chunks = [
        {'id': 'chunk_1', 'payload': {'is_pi': False, 'text': 'Public document'}},
        {'id': 'chunk_2', 'payload': {'is_pi': True, 'uid': '123', 'text': 'PI doc for user 123'}},
        {'id': 'chunk_3', 'payload': {'is_pi': True, 'uid': '456', 'text': 'PI doc for user 456'}},
    ]
    
    print(f"\nChunk Access Test:")
    for user in [pi_user, non_pi_user]:
        accessible = controller.filter_chunks_by_access(user, test_chunks)
        print(f"User {user.id} can access {len(accessible)}/{len(test_chunks)} chunks")

if __name__ == "__main__":
    test_access_control()