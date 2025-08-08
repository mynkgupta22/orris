import logging
import time
import uuid
from typing import List, Dict, Optional
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.http import models
import openai
import os

from app.models.user import User
from app.rag.config import Config
from app.rag.access_control import AccessController
from app.rag.retriever_schemas import DocumentChunk, QueryResponse, AuditLog

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RetrieverService:
    """Secure RAG retriever service with role-based access control"""
    
    def __init__(self):
        self.qdrant_client = self._init_qdrant_client()
        self._init_openai()
        self.collection_name = Config.QDRANT_COLLECTION_NAME
        self.access_controller = AccessController()
        
    def _init_qdrant_client(self) -> QdrantClient:
        """Initialize Qdrant client"""
        try:
            client = QdrantClient(
                host=Config.QDRANT_HOST,
                port=Config.QDRANT_PORT
            )
            logger.info(f"Connected to Qdrant at {Config.QDRANT_HOST}:{Config.QDRANT_PORT}")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise
    
    
    def _init_openai(self):
        """Initialize OpenAI API for embeddings and LLM calls"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key or api_key == 'your-openai-api-key':
                raise ValueError("OpenAI API key not configured")
            
            openai.api_key = api_key
            logger.info("OpenAI API configured successfully")
        except Exception as e:
            logger.error(f"Failed to configure OpenAI: {e}")
            raise
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI"""
        try:
            # Truncate text if too long
            max_length = 8000  # OpenAI limit
            if len(text) > max_length:
                text = text[:max_length]
            
            response = openai.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise
    
    def call_llm(self, prompt: str, max_tokens: int = 512) -> str:
        """Call LLM to generate answer"""
        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that answers questions based on provided documents. Always cite the document sources when possible."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=0.1
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            # Return error response instead of raising
            return "I apologize, but I'm unable to generate a response at this time due to a technical issue."
    
    async def retrieve_and_answer(
        self, 
        query: str, 
        user: User,
        top_k_pre: int = 30,
        top_k_post: int = 7,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> QueryResponse:
        """Main retrieval and answer generation pipeline"""
        
        start_time = time.time()
        audit_id = f"audit-{int(start_time * 1000)}-{user.id}"
        
        logger.info(f"Processing query for user {user.id} (role: {user.role.value}): {query[:100]}...")
        
        try:
            # 1. Generate query embedding
            query_vector = self.generate_embedding(query)
            
            # 2. Build access control filter
            access_filter = self.access_controller.build_access_filter(user)
            
            # 3. Perform vector search
            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                limit=top_k_pre,
                with_payload=True,
                with_vectors=False,
                query_filter=access_filter
            )
            
            # 4. Convert to our format and apply additional access validation
            candidate_chunks = []
            for result in search_results:
                payload = result.payload or {}
                
                # Double-check access (defense in depth)
                if self.access_controller.validate_chunk_access(user, payload):
                    chunk = DocumentChunk(
                        id=str(result.id),
                        text=payload.get('text', ''),
                        score=result.score,
                        source_doc_name=payload.get('source_doc_name', ''),
                        source_doc_id=payload.get('source_doc_id', ''),
                        doc_type=payload.get('doc_type', ''),
                        source_page=payload.get('source_page', 0),
                        chunk_index=payload.get('chunk_index', 0),
                        is_pi=payload.get('is_pi', False),
                        uid=payload.get('uid'),
                        created_at=payload.get('created_at', ''),
                        doc_url=payload.get('doc_url', '')
                    )
                    candidate_chunks.append(chunk)
            
            # 5. Re-rank and select top results (by score for now)
            final_chunks = sorted(candidate_chunks, key=lambda x: x.score, reverse=True)[:top_k_post]
            
            # 6. Build context for LLM
            if not final_chunks:
                answer = "I don't have access to any relevant documents to answer your question."
                context_text = ""
            else:
                context_parts = []
                for i, chunk in enumerate(final_chunks, 1):
                    snippet = chunk.text[:800] + "..." if len(chunk.text) > 800 else chunk.text
                    context_parts.append(
                        f"Document {i} (Source: {chunk.source_doc_name}, Page: {chunk.source_page}):\n{snippet}\n"
                    )
                
                context_text = "\n---\n".join(context_parts)
                
                # 7. Create secure prompt
                prompt = self._build_secure_prompt(query, context_text, user)
                
                # 8. Generate answer
                answer = self.call_llm(prompt)
            
            processing_time = int((time.time() - start_time) * 1000)
            
            # 9. Create audit log
            audit_log = AuditLog(
                audit_id=audit_id,
                user_id=str(user.id),
                user_role=user.role.value,
                query=query,
                num_chunks_returned=len(final_chunks),
                chunks_accessed=[chunk.id for chunk in final_chunks],
                processing_time_ms=processing_time,
                timestamp=datetime.now(),
                ip_address=ip_address,
                user_agent=user_agent
            )
            
            # Log audit (in production, store this in database)
            logger.info(f"AUDIT: {audit_log.model_dump()}")
            
            # 10. Build response
            response = QueryResponse(
                answer=answer,
                used_chunks=final_chunks,
                query=query,
                user_id=str(user.id),
                user_role=user.role.value,
                audit_id=audit_id,
                processing_time_ms=processing_time,
                total_chunks_found=len(search_results)
            )
            
            logger.info(f"Query completed for user {user.id}: {len(final_chunks)} chunks, {processing_time}ms")
            return response
            
        except Exception as e:
            logger.error(f"Query processing failed for user {user.id}: {e}")
            # Return error response instead of raising
            error_response = QueryResponse(
                answer="I apologize, but I encountered an error while processing your query. Please try again later.",
                used_chunks=[],
                query=query,
                user_id=str(user.id),
                user_role=user.role.value,
                audit_id=audit_id,
                processing_time_ms=int((time.time() - start_time) * 1000),
                total_chunks_found=0
            )
            return error_response
    
    def _build_secure_prompt(self, query: str, context: str, user: User) -> str:
        """Build a secure prompt that prevents data leakage"""
        
        role_description = {
            "signed_up": "a general user with access to public documents only",
            "non_pi_access": "a user with access to non-personal documents",
            "pi_access": "a user with access to your personal documents and public documents"
        }.get(user.role.value, "a user")
        
        prompt = f"""You are a secure AI assistant helping {role_description}.

CRITICAL SECURITY INSTRUCTIONS:
- Use ONLY the provided documents below to answer questions
- NEVER make up or infer personal information not explicitly stated
- If you don't have enough information, say "I don't have enough information to answer that"
- Always cite document sources when providing information
- Be respectful of privacy and data security

User Query: {query}

Available Documents:
{context}

Please provide a helpful and accurate answer based only on the information in the documents above."""

        return prompt
    
    def get_service_status(self) -> Dict:
        """Get service status and statistics"""
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            return {
                "status": "healthy",
                "collection_name": self.collection_name,
                "total_vectors": collection_info.vectors_count,
                "collection_status": collection_info.status,
                "embedding_dimension": Config.EMBEDDING_DIMENSION,
                "qdrant_host": Config.QDRANT_HOST
            }
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

# Test function
async def test_retriever_service():
    """Test the retriever service"""
    from app.models.user import User, UserRole, UserStatus
    
    # Mock user for testing
    test_user = User()
    test_user.id = 123
    test_user.role = UserRole.NON_PI_ACCESS
    test_user.status = UserStatus.ACTIVE
    test_user.email = "test@example.com"
    
    try:
        Config.validate()
        retriever = RetrieverService()
        
        print("Retriever Service Test")
        print("=" * 30)
        
        # Test service status
        status = retriever.get_service_status()
        print(f"Service Status: {status}")
        
        # Test query
        response = await retriever.retrieve_and_answer(
            query="What is artificial intelligence?",
            user=test_user,
            top_k_pre=10,
            top_k_post=3
        )
        
        print(f"\nQuery Response:")
        print(f"Answer: {response.answer[:200]}...")
        print(f"Chunks found: {response.total_chunks_found}")
        print(f"Chunks used: {len(response.used_chunks)}")
        print(f"Processing time: {response.processing_time_ms}ms")
        
        return True
        
    except Exception as e:
        print(f"Test failed: {e}")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_retriever_service())