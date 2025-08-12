import logging
import time
from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.http import models

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

# Removed HuggingFaceEmbeddings as it's replaced by our custom client
# from langchain_huggingface import HuggingFaceEmbeddings

from app.models.user import User
from app.rag.config.config import Config
from app.rag.pipeline.access_control import AccessController
from app.rag.api.retriever_schemas import DocumentChunk, RetrievedChunk

# --- Change Start: Import the custom embedding client ---
# (Assuming embed.py is located alongside this file or is accessible via this path)
from app.rag.core.embed import get_embedding_client 
# --- Change End ---

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGResponse(models.BaseModel):
    """Detailed response from RAG pipeline"""
    answer: str
    query: str
    session_id: UUID
    retrieved_chunks: List[RetrievedChunk]
    processing_time_ms: int
    image_base64: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
        }

SANITIZE_REGEXES: List[str] = [
    r"(?i)ignore (?:previous|all) instructions",
    r"(?i)system\s*prompt",
    r"(?i)you are now",
    r"(?i)act as",
]


class RetrievalPipeline:
    """Secure RAG retrieval pipeline with RBAC and LangChain components."""

    def __init__(self):
        self.qdrant_client = self._init_qdrant_client()
        self.collection_name = Config.QDRANT_COLLECTION_NAME
        self.access_controller = AccessController()

        # --- Change Start: Use the custom API-based embedding client ---
        # This ensures the same "BAAI/bge-large-en-v1.5" model is used via API
        self.embedding_client = get_embedding_client()
        logger.info(f"Initialized embedding client with model: {self.embedding_client.model_name}")
        # --- Change End ---

        # LLM
        self.chat = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)

    def _init_qdrant_client(self) -> QdrantClient:
        try:
            client = QdrantClient(host=Config.QDRANT_HOST, port=Config.QDRANT_PORT)
            logger.info(f"Connected to Qdrant at {Config.QDRANT_HOST}:{Config.QDRANT_PORT}")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    def _sanitize_query(self, query: str) -> str:
        """Basic regex-based sanitization to mitigate prompt injection."""
        sanitized = query
        for pattern in SANITIZE_REGEXES:
            sanitized = __import__("re").sub(pattern, "", sanitized)
        return sanitized.strip()

    async def retrieve_and_answer(
        self,
        query: str,
        user: User,
        session_id: Optional[UUID] = None,
        top_k_pre: int = 30,
        top_k_post: int = 7,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> RAGResponse:
        start_time = time.time()

        # --- Greeting Handler ---
        GREETINGS = {"hi", "hello", "hey", "heya", "yo", "greetings"}
        normalized_query = query.lower().strip("!?. ")
        if normalized_query in GREETINGS:
            return RAGResponse(
                answer="Hello! How can I help you today?",
                query=query,
                session_id=session_id,
                retrieved_chunks=[],
                processing_time_ms=int((time.time() - start_time) * 1000),
                image_base64=None
            )
        # --- End Greeting Handler ---
        
        audit_id = f"audit-{int(start_time * 1000)}-{user.id}"

        logger.info(
            f"Processing query for user {user.id} (role: {user.role.value}): {query[:100]}..."
        )

        try:
            # 1) Sanitize query
            sanitized_query = self._sanitize_query(query)

            # 2) RBAC pre-filter for Qdrant
            access_filter: models.Filter = self.access_controller.build_access_filter(user)

            # --- Change Start: Embed query using the custom API client ---
            # encode_texts returns a batch, so we take the first result [0]
            query_vector = self.embedding_client.encode_texts([sanitized_query])[0]
            # --- Change End ---

            search_results = self.qdrant_client.search(
                collection_name=self.collection_name,
                query_vector=("text", query_vector), # Using named vector "text"
                limit=top_k_pre,
                with_payload=True,
                with_vectors=False,
                query_filter=access_filter,
            )
    

            # 4) Convert to RetrievedChunk and enforce defense-in-depth checks
            candidate_chunks: List[RetrievedChunk] = []
            for result in search_results:              
                payload = result.payload or {}
                if self.access_controller.validate_chunk_access(user, payload):
                    candidate_chunks.append(
                        RetrievedChunk(
                            id=str(result.id),
                            text=payload.get("text", ""),
                            score=float(result.score),
                            payload=payload,
                        )
                    )
        
            # 5) Select post-k
            final_chunks = sorted(candidate_chunks, key=lambda x: x.score, reverse=True)[:top_k_post]

          
            # 6) Build context and call LLM (user message only contains user query)
            image_base64 = None # Default to no image
            
            if not final_chunks:
                answer = (
                    "I couldn't find an answer to your question in the available documents."
                )
                source_id = None
            else:
                context_parts = []
                for i, ch in enumerate(final_chunks, 1):
                    print("@@@@@@@@@@@@")
                    print(ch.text)
                    print("@@@@@@@@@@@@@@")
                    snippet = ch.text[:800] + "..." if len(ch.text) > 800 else ch.text
                    # Include the chunk ID for citation
                    context_parts.append(
                        f"Document ID: {ch.id}\nSource: {ch.payload.get('source_doc_name', 'Unknown')}, Page: {ch.payload.get('source_page', 'N/A')}\nContent:\n{snippet}"
                    )

                context_text = "\n\n---\n\n".join(context_parts)

        

                system_text = """
                You are a secure assistant. Your task is to answer the user's question based ONLY on the provided context.
                You must respond in a JSON format with two keys: "answer" and "source_id".
                - "answer": A concise, helpful response to the user's question, synthesized from the context. If the context is insufficient, say "I couldn't find the answer to your question in the provided documents." If the user's query is a simple greeting, provide a friendly greeting in response.
                - "source_id": The 'Document ID' of the single most relevant document you used to formulate your answer. If no single document was relevant, or if the context was insufficient, return null.
                Do not add any commentary or explanation outside of the JSON structure.
                """

                user_text = f"Question: {sanitized_query}\n\nContext:\n{context_text}"

                # Add this test right before your LLM call to verify the issue
                def test_llm_response(self, context_text, sanitized_query):
                    """Test function to debug LLM response issues"""
                    
                    # Test 1: Simple test without JSON mode
                    simple_chat = ChatOpenAI(model="gpt-4o-mini", temperature=0.1)
                    simple_response = simple_chat.invoke([
                        HumanMessage(content=f"Given this context about investment portfolios: {context_text[:500]}... Can you find any investment information? Just say yes or no and briefly what you found.")
                    ])
                    logger.info(f"Simple test response: {simple_response.content}")
                    
                    # Test 2: Test with your exact prompt but no JSON mode
                    regular_response = simple_chat.invoke([
                        SystemMessage(content="""You are a secure assistant. Answer the user's question based on the provided context. If you find investment portfolio information, use it to provide a helpful answer."""),
                        HumanMessage(content=f"Question: {sanitized_query}\n\nContext:\n{context_text}")
                    ])
                    logger.info(f"Regular response: {regular_response.content}")
                    
                    # Test 3: Your original approach
                    json_chat_model = self.chat.with_structured_output(
                        method="json_mode",
                        include_raw=False
                    )
                    
                    json_response = json_chat_model.invoke([
                        SystemMessage(content="You are a helpful assistant. Respond in JSON format with 'answer' and 'source_id' keys. Use the provided context to answer questions."),
                        HumanMessage(content=f"Question: {sanitized_query}\n\nContext:\n{context_text}")
                    ])
                    logger.info(f"JSON mode response: {json_response}")
                    
                    return simple_response.content
                    test_result = self.test_llm_response(context_text, sanitized_query)

# Call this test function before your main LLM call:
# test_result = self.test_llm_response(context_text,  ̰sanitized_query)
                


                
                # Configure the model to return JSON
                json_chat_model = self.chat.with_structured_output(
                    method="json_mode",
                    include_raw=False
                )
                
                llm_resp = json_chat_model.invoke([
                    SystemMessage(content=system_text),
                    HumanMessage(content=user_text),
                ])
                # print("************************")
                # print(system_text)

                # print(user_text)
                # print("************************")
                answer = llm_resp.get("answer", "I couldn't process the response.")
                source_id = llm_resp.get("source_id")

                # Extract image_base64 only if the cited source is an image
                if source_id:
                    for chunk in final_chunks:
                        if chunk.id == source_id and chunk.payload.get("is_image"):
                            image_base64 = chunk.payload.get("image_base64")
                            break
            
            processing_time = int((time.time() - start_time) * 1000)

            # 7) Build audit log
            logger.info(
                {
                    "audit_id": audit_id,
                    "user_id": str(user.id),
                    "user_role": user.role.value,
                    "query": sanitized_query,
                    "num_chunks_returned": len(final_chunks),
                    "chunks_accessed": [c for c in final_chunks],
                    "processing_time_ms": processing_time,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                }
            )

            # 8) Build detailed response
            return RAGResponse(
                answer=answer,
                query=sanitized_query,
                session_id=session_id,
                retrieved_chunks=final_chunks,
                processing_time_ms=processing_time,
                image_base64=image_base64  # Add the conditionally extracted base64
            )

        except Exception as e:
            logger.error(f"Query processing failed for user {user.id}: {e}")
            # Return a RAGResponse with the error message
            return RAGResponse(
                answer=(
                    "I encountered an error while processing your query. Please try again later."
                ),
                query=query,
                session_id=session_id,
                retrieved_chunks=[],
                processing_time_ms=int((time.time() - start_time) * 1000)
            )

    def get_service_status(self) -> Dict:
        try:
            collection_info = self.qdrant_client.get_collection(self.collection_name)
            # --- Change Start: Update status to reflect the correct embedding client details ---
            embedding_dim = self.embedding_client.dimension
            # --- Change End ---
            return {
                "status": "healthy",
                "collection_name": self.collection_name,
                "total_vectors": collection_info.vectors_count,
                "collection_status": collection_info.status,
                "embedding_dimension": embedding_dim,
                "qdrant_host": Config.QDRANT_HOST,
            }
        except Exception as e:
            logger.error(f"Failed to get service status: {e}")
            return {"status": "unhealthy", "error": str(e)}