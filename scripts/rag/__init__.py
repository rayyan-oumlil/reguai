"""
RAG Module - Retrieval Augmented Generation pour Chatbot
Utilise LangChain avec AWS Bedrock (embeddings + LLM) et FAISS pour vector store.
"""

from scripts.rag.rag_helper import (
    initialize_rag_system,
    chat_with_rag,
    search_rag_context,
    get_rag_stats
)

__all__ = [
    'initialize_rag_system',
    'chat_with_rag',
    'search_rag_context',
    'get_rag_stats'
]

