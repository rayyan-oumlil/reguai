"""
Configuration pour le système RAG
Définit les chemins de données, paramètres de chunking, et configuration LangChain
"""

from pathlib import Path
import os

# ============================================
# Chemins des Données
# ============================================

BASE_DIR = Path(__file__).parent.parent.parent

# Chemins vers les données générées
DATA_PATHS = {
    'regulatory_extractions': BASE_DIR / 'data' / 'generated' / 'extracted_directives',
    'tenk_extractions': BASE_DIR / 'data' / 'generated' / 'extracted_data_points',
    'company_universe': BASE_DIR / 'data' / 'generated' / 'company_universe' / 'company_universe.json',
    'vector_store_cache': BASE_DIR / 'data' / 'generated' / 'rag_cache' / 'vector_store',  # Cache FAISS
}

# Créer dossier cache si nécessaire
DATA_PATHS['vector_store_cache'].parent.mkdir(parents=True, exist_ok=True)

# ============================================
# Configuration RAG
# ============================================

RAG_CONFIG = {
    # Chunking
    'chunk_size': 800,              # Tokens par chunk (équilibré pour contexte)
    'chunk_overlap': 100,            # Overlap entre chunks pour continuité
    'separators': ["\n\n", "\n", ". ", " ", ""],  # Séparateurs pour chunking
    
    # Recherche
    'top_k': 8,                      # Nombre de chunks à récupérer (augmenté pour plus de contexte)
    'similarity_threshold': 0.5,     # Score minimum de similarité (réduit pour plus de flexibilité)
    
    # Embeddings
    # Modèle disponible dans votre compte Bedrock
    'embedding_model': 'global.cohere.embed-v4:0',  # Cohere Embed v4 (disponible dans votre compte)
    'embedding_dimension': 1024,     # Dimension des embeddings Cohere v4
    
    # LLM
    # Utiliser le même modèle que dans extract_data_points_10k.ipynb
    'llm_model': 'global.anthropic.claude-sonnet-4-5-20250929-v1:0',  # Claude Sonnet (même que extraction)
    'max_tokens': 4000,              # Max tokens dans la réponse
    'temperature': 0.1,              # Température (basse = plus factuel)
    
    # AWS
    'aws_region': os.environ.get('AWS_REGION', 'us-west-2'),
    
    # Performance
    'max_context_tokens': 100000,    # Max tokens dans contexte RAG
    'batch_size': 10,                # Taille batch pour embeddings
}

# ============================================
# Patterns de Chunking par Type de Données
# ============================================

CHUNKING_PATTERNS = {
    'regulation': {
        'preferred_separator': '\n\n',  # Paragraphes réglementaires
        'max_chunk_size': 800,
    },
    '10k': {
        'preferred_separator': '\n',     # Lignes pour données 10-K
        'max_chunk_size': 600,
    },
    'company_universe': {
        'preferred_separator': '\n',     # Lignes pour données entreprise
        'max_chunk_size': 500,
    }
}

