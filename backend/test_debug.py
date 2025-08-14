#!/usr/bin/env python3
"""
Quick debug script to test RAG functionality
"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

import asyncio
from app.rag.pipeline.retrieval_pipeline import RetrievalPipeline
from app.models.user import User, UserRole
from uuid import uuid4

async def test_rag():
    # Create a test pipeline
    pipeline = RetrievalPipeline()
    
    # Create a test user with PI access
    test_user = User(
        id=1,
        email="test@example.com",
        username="testuser",
        role=UserRole.PI_ACCESS,
        is_active=True
    )
    
    # Test 1: Without conversation context
    print("=== TEST 1: Query without conversation context ===")
    result1 = await pipeline.retrieve_and_answer(
        query="tell me about my investment and portfolio",
        user=test_user,
        session_id=uuid4(),
        conversation_context=None
    )
    print(f"Answer 1: {result1.answer}")
    print()
    
    # Test 2: With conversation context
    print("=== TEST 2: Query with conversation context ===")
    fake_context = "Previous conversation:\nUser: Hello\nAssistant: Hi! How can I help you?\n\n"
    result2 = await pipeline.retrieve_and_answer(
        query="tell me about my investment and portfolio",
        user=test_user,
        session_id=uuid4(),
        conversation_context=fake_context
    )
    print(f"Answer 2: {result2.answer}")

if __name__ == "__main__":
    asyncio.run(test_rag())
