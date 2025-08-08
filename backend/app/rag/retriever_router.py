from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Dict
import logging

from app.core.dependencies import get_current_active_user
from app.models.user import User, UserRole
from app.rag.retriever_service import RetrieverService
from app.rag.retriever_schemas import QueryRequest, QueryResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/rag", tags=["RAG Retriever"])

# Initialize retriever service
retriever_service = RetrieverService()

@router.post("/query", response_model=QueryResponse)
async def query_documents(
    request: QueryRequest,
    current_user: User = Depends(get_current_active_user),
    http_request: Request = None
) -> QueryResponse:
    """
    Query documents using RAG with role-based access control
    
    - **SIGNED_UP**: Access to public documents only
    - **NON_PI_ACCESS**: Access to non-personal information documents
    - **PI_ACCESS**: Access to personal documents + non-PI documents
    """
    
    # Get client information for audit logging
    client_ip = http_request.client.host if http_request and http_request.client else "unknown"
    user_agent = http_request.headers.get("user-agent", "unknown") if http_request else "unknown"
    
    logger.info(
        f"RAG query from user {current_user.id} ({current_user.role.value}): "
        f"'{request.query[:100]}...'"
    )
    
    try:
        # Process the query with the retriever service
        response = await retriever_service.retrieve_and_answer(
            query=request.query,
            user=current_user,
            top_k_pre=request.top_k_pre,
            top_k_post=request.top_k_post,
            ip_address=client_ip,
            user_agent=user_agent
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Query processing failed for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to process your query. Please try again later."
        )

@router.get("/status")
async def get_retriever_status(
    current_user: User = Depends(get_current_active_user)
) -> Dict:
    """
    Get RAG retriever service status
    
    Requires authentication but available to all user roles.
    """
    
    try:
        status = retriever_service.get_service_status()
        
        # Add user-specific access information
        status["user_access"] = {
            "user_id": current_user.id,
            "role": current_user.role.value,
            "can_access_pi": current_user.role == UserRole.PI_ACCESS,
            "can_access_non_pi": current_user.role in [UserRole.NON_PI_ACCESS, UserRole.PI_ACCESS] or current_user.role == UserRole.SIGNED_UP
        }
        
        return status
        
    except Exception as e:
        logger.error(f"Failed to get retriever status: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get service status"
        )

@router.get("/access-summary")
async def get_user_access_summary(
    current_user: User = Depends(get_current_active_user)
) -> Dict:
    """
    Get summary of what documents the current user can access
    """
    
    from app.rag.access_control import AccessController
    
    try:
        access_controller = AccessController()
        summary = access_controller.get_user_access_summary(current_user)
        
        # Add role descriptions for frontend
        role_descriptions = {
            "signed_up": "Basic access to public documents only",
            "non_pi_access": "Access to all non-personal information documents", 
            "pi_access": "Full access to your personal documents and public documents"
        }
        
        summary["role_description"] = role_descriptions.get(
            current_user.role.value, 
            "Unknown role"
        )
        
        summary["access_rules"] = {
            "public_documents": "✅ Can access",
            "non_pi_documents": "✅ Can access" if current_user.role != UserRole.SIGNED_UP else "❌ No access",
            "personal_pi_documents": "✅ Can access your own" if current_user.role == UserRole.PI_ACCESS else "❌ No access",
            "other_users_pi_documents": "❌ Never accessible"
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to get access summary for user {current_user.id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Failed to get access summary"
        )

# Health check endpoint (no auth required)
@router.get("/health")
async def health_check():
    """
    Health check endpoint for the RAG service
    """
    try:
        # Basic connectivity test
        status = retriever_service.get_service_status()
        
        if status.get("status") == "healthy":
            return {"status": "healthy", "service": "rag-retriever"}
        else:
            raise HTTPException(
                status_code=503,
                detail="Service unhealthy"
            )
            
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Service unavailable: {str(e)}"
        )