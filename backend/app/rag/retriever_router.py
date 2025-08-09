from fastapi import APIRouter, Depends, HTTPException, Request
import logging

from app.core.dependencies import get_current_active_user
from app.models.user import User
try:
    from app.rag.retrieval_pipeline import RetrievalPipeline as RetrieverService
except Exception:
    # Fallback to legacy name to avoid import errors during deploy
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

# Removed status, access-summary, and health endpoints as requested