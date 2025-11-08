# Module RAG

RAG avec LangChain, AWS Bedrock et FAISS.

## Utilisation

```python
from scripts.rag import initialize_rag_system, chat_with_rag

# Initialiser
result = initialize_rag_system(use_cache=True, tenk_limit=100)

# Chat
response = chat_with_rag("Quel est l'impact de l'EU AI Act sur Apple ?")
```

## Configuration

Modifier `config.py` pour ajuster les paramètres (chunk_size, top_k, modèles Bedrock).

## Cache

Vector store sauvegardé dans `data/generated/rag_cache/vector_store/`

