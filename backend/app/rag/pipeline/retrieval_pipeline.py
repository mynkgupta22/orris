import logging
import time
from typing import List, Dict, Optional
from uuid import UUID
from datetime import datetime

from qdrant_client import QdrantClient
from qdrant_client.http import models

from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage


from app.models.user import User
from app.rag.config.config import Config
from app.rag.pipeline.access_control import AccessController
from app.rag.api.retriever_schemas import DocumentChunk, QueryResponse, AuditLog


from app.rag.core.embed import get_embedding_client 

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
            if Config.QDRANT_URL:
                # Use the full URL if provided
                client = QdrantClient(
                    url=Config.QDRANT_URL,
                    api_key=Config.QDRANT_API_KEY
                )
                logger.info(f"Connected to Qdrant at {Config.QDRANT_URL}")
            else:
                # Use host/port configuration
                client = QdrantClient(
                    host=Config.QDRANT_HOST, 
                    port=Config.QDRANT_PORT,
                    https=getattr(Config, 'QDRANT_USE_SSL', False),
                    api_key=Config.QDRANT_API_KEY
                )
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
    ) -> QueryResponse:
        start_time = time.time()
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

            # 4) Convert to DocumentChunk and enforce defense-in-depth checks
            candidate_chunks: List[DocumentChunk] = []
            for result in search_results:
                payload = result.payload or {}
                if self.access_controller.validate_chunk_access(user, payload):
                    candidate_chunks.append(
                        DocumentChunk(
                            id=str(result.id),
                            text=payload.get("text", ""),
                            score=float(result.score),
                            source_doc_name=str(payload.get("source_doc_name", "")),
                            source_doc_id=str(payload.get("source_doc_id", "")),
                            doc_type=str(payload.get("doc_type", "")),
                            source_page=int(payload.get("source_page") or 0),
                            chunk_index=int(payload.get("chunk_index") or 0),
                            is_pi=bool(payload.get("is_pi", False)),
                            uid=payload.get("uid"),
                            created_at=str(payload.get("created_at", "")),
                            doc_url=str(payload.get("doc_url", "")),
                        )
                    )

            # 5) Select post-k
            final_chunks = sorted(candidate_chunks, key=lambda x: x.score, reverse=True)[:top_k_post]

            # 6) Extract image_base64 from the most similar chunk (first one)
            image_base64 = None
            if final_chunks:
                # Get image_base64 from the most similar chunk's metadata if available
                first_chunk_id = final_chunks[0].id
                try:
                    chunk_result = self.qdrant_client.retrieve(
                        collection_name=self.collection_name,
                        ids=[first_chunk_id],
                        with_payload=True
                    )
                    if chunk_result and chunk_result[0].payload:
                        image_base64 = chunk_result[0].payload.get("image_base64")
                except Exception as e:
                    logger.warning(f"Failed to retrieve image_base64 from chunk {first_chunk_id}: {e}")

            # 7) Build context and call LLM (user message only contains user query)
            if not final_chunks:
                answer = (
                    "I don't have access to any relevant documents to answer your question."
                )
            else:
                context_parts = []
                for i, ch in enumerate(final_chunks, 1):
                    snippet = ch.text[:800] + "..." if len(ch.text) > 800 else ch.text
                    context_parts.append(
                        f"Document {i} (Source: {ch.source_doc_name}, Page: {ch.source_page}):\n{snippet}"
                    )
                   

                context_text = "\n\n---\n\n".join(context_parts)

                prompt = f"""
                            A chat between a curious human and an artificial intelligence assistant.
                            The assistant gives helpful, detailed, and polite answers to the user's question based ONLY on the provided context.

                            ### CONTEXT:
                            {context_text}

                            ### INSTRUCTION:
                            {sanitized_query}

                            ### RESPONSE:
                        """

                try:
                    import replicate
                    
                    model_id = "tomasmcm/fin-llama-33b:d60d4e27c69c809632b91635c9319a6422f5d90e668d1abeb2d8c2dd758bb8ea"
                    
                    # The replicate.run() function returns a generator for streaming output.
                    # We join the parts to get the full string response.
                    output_generator = replicate.run(
                        model_id,
                        input={
                            "prompt": prompt,
                            "max_new_tokens": 1024, # Adjust as needed
                            "temperature": 0.1,      # Adjust as needed
                        }
                    )
                    answer = "".join([str(part) for part in output_generator])
                    logger.info("Successfully received response from Replicate.")

                except Exception as e:
                    logger.error(f"Failed to get response from Replicate API: {e}")
                    answer = "I apologize, but I encountered an error while generating a response. Please try again."
            

                # system_text = """
                #                 You are a secure assistant that answers questions based on the provided context.

                #                 CORE RULES:
                #                 1. Answer questions using ONLY the information from the provided context documents
                #                 2. If the context contains relevant information, you MUST provide a comprehensive answer based on that information
                #                 3. Only respond with "Insufficient information in the provided context." if the context truly lacks the information needed to answer the question
                #                 4. Present answers in a structured and well-formatted manner
                #                 5. For greetings and polite conversational openers (e.g., "hi", "hello", "good morning", "how are you"), you may respond freely in a friendly tone.
                #                 6. Conversation history is provided for context but should never prevent you from answering when sufficient context is available

                #                 IMPORTANT: If the context documents contain information relevant to the current question, you must use that information to provide a complete answer, regardless of any conversation history.
                #             """

                # user_text = f"Question: {sanitized_query}\n\nContext:\n{context_text}"
                
                # llm_resp = self.chat.invoke([
                #     SystemMessage(content=system_text),
                #     HumanMessage(content=user_text),
                # ])
                # answer = getattr(llm_resp, "content", "") or ""

            processing_time = int((time.time() - start_time) * 1000)

            # 7) Build audit log (TODO: persist to DB)
            # TODO: Persist audit with sanitized_query, user info, chunk IDs, timing, client info
            logger.info(
                {
                    "audit_id": audit_id,
                    "user_id": str(user.id),
                    "user_role": user.role.value,
                    "query": sanitized_query,
                    "num_chunks_returned": len(final_chunks),
                    "chunks_accessed": [c.uid for c in final_chunks],
                    "processing_time_ms": processing_time,
                    "ip_address": ip_address,
                    "user_agent": user_agent,
                }
            )

            # 8) Build minimal response
            return QueryResponse(
                answer=answer,
                query=sanitized_query,
                session_id=session_id,
                image_base64=image_base64,
            )

        except Exception as e:
            logger.error(f"Query processing failed for user {user.id}: {e}")
            return QueryResponse(
                answer=(
                    "I encountered an error while processing your query. Please try again later."
                ),
                query=query,
                session_id=session_id,
                image_base64=None,
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