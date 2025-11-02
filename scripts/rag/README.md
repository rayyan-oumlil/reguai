# 📚 Module RAG - Retrieval Augmented Generation

Module complet pour RAG avec LangChain, AWS Bedrock et FAISS.

## 📁 Structure

```
scripts/rag/
├── __init__.py          # Exports principaux
├── config.py            # Configuration (chemins, paramètres)
├── data_loader.py       # Chargement et formatage des données
├── embeddings.py        # Gestion embeddings Bedrock
├── vector_store.py      # Vector store FAISS avec LangChain
├── rag_chain.py        # Chain RAG LangChain
├── rag_helper.py       # Helper principal pour Streamlit
└── README.md           # Ce fichier
```

## 🚀 Utilisation

### Initialisation

```python
from scripts.rag import initialize_rag_system

# Initialiser le système (une fois)
result = initialize_rag_system(
    use_cache=True,      # Utiliser cache si disponible
    tenk_limit=100       # Limiter fichiers 10-K pour MVP
)

if result['success']:
    print(result['message'])
else:
    print(f"Erreur: {result['error']}")
```

### Chat avec RAG

```python
from scripts.rag import chat_with_rag

# Poser une question
response = chat_with_rag(
    query="Quel est l'impact de l'EU AI Act sur Apple ?",
    return_sources=True
)

if response['error']:
    print(f"Erreur: {response['error']}")
else:
    print(f"Réponse: {response['answer']}")
    print(f"Sources: {response['sources']}")
```

### Recherche seule (sans génération)

```python
from scripts.rag import search_rag_context

# Rechercher contexte pertinent
documents = search_rag_context("EU AI Act", top_k=5)

for doc in documents:
    print(f"[{doc.metadata['type']}] {doc.page_content[:200]}...")
```

## 🔧 Configuration

Modifier `config.py` pour ajuster :
- `chunk_size`: Taille des chunks (défaut: 800 tokens)
- `top_k`: Nombre de résultats (défaut: 5)
- `embedding_model`: Modèle Bedrock (défaut: `amazon.titan-embed-text-v2`)
- `llm_model`: Modèle LLM (défaut: Claude Sonnet)

## 📊 Flux de Données

```
1. Chargement données
   ├─ Extractions réglementaires (6 fichiers)
   ├─ Extractions 10-K (100 fichiers pour MVP)
   └─ Company Universe (1 fichier)

2. Formatage en Documents LangChain
   └─ Conversion JSON → texte → Document avec métadonnées

3. Génération embeddings (Bedrock Titan)
   └─ Création vecteurs pour chaque document

4. Indexation FAISS
   └─ Vector store avec recherche rapide

5. RAG Chain (LangChain)
   ├─ Recherche similarité
   ├─ Construction prompt avec contexte
   └─ Génération réponse (Bedrock Claude Sonnet)
```

## 💾 Cache

Le vector store est automatiquement sauvegardé dans :
`data/generated/rag_cache/vector_store/`

Au prochain démarrage, le système charge depuis le cache (beaucoup plus rapide).

## 🛠️ Dépendances

- `langchain>=0.1.0`
- `langchain-aws>=0.1.0`
- `langchain-community>=0.0.20`
- `faiss-cpu>=1.7.4`
- `boto3` (déjà installé)

## 📝 Notes

- Le système utilise un singleton : une seule instance initialisée
- Les embeddings sont générés via Bedrock (nécessite credentials AWS)
- Pour MVP, on limite à 100 fichiers 10-K (peut être augmenté)
- Le cache évite de régénérer les embeddings à chaque fois

