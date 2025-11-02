# 🚀 RAG Workflow, Services et Choix Techniques

## 📋 WORKFLOW COMPLET DU RAG

### Flux Global : Question → Réponse avec RAG

```
1. UTILISATEUR pose une question
   ↓
2. PRÉPARATION : Charger base vectorielle (une fois au démarrage)
   - Charger extractions réglementaires (6 fichiers JSON)
   - Charger extractions 10-K (500 fichiers JSON, ou échantillon)
   - Charger Company Universe (1 fichier JSON)
   - Créer chunks avec métadonnées
   - Générer embeddings pour chaque chunk
   - Indexer dans base vectorielle
   ↓
3. RECHERCHE SÉMANTIQUE (quand question posée)
   - Générer embedding de la question
   - Rechercher top-K chunks similaires (similarité cosinus)
   - Filtrer/reranker si nécessaire
   - Récupérer chunks avec métadonnées
   ↓
4. CONSTRUCTION PROMPT RAG
   - Formater contexte : Concaténer chunks trouvés
   - Ajouter instructions pour Bedrock
   - Inclure question utilisateur
   ↓
5. GÉNÉRATION AVEC BEDROCK SONNET
   - Appel API Bedrock avec prompt RAG
   - Modèle : Claude Sonnet (qualité supérieure)
   - Réponse générée avec contexte
   ↓
6. AFFICHAGE RÉPONSE
   - Afficher réponse à l'utilisateur
   - Afficher sources utilisées (réglementation, entreprise, document)
```

---

## 🔧 SERVICES ET TECHNOLOGIES

### 1. Base Vectorielle (Vector Store)

#### FAISS ⭐ CHOIX FINAL (Meilleure Performance)
- ✅ **Très performant** (Facebook AI Research)
- ✅ **Optimisé pour recherche rapide** (meilleur que ChromaDB et autres)
- ✅ **In-memory, ultra-rapide** (recherche en millisecondes)
- ✅ Pas de dépendances externes une fois installé
- ✅ Compatible avec embeddings Bedrock (n'importe quel format vectoriel)
- ❌ Nécessite embeddings pré-calculés (mais on utilise Bedrock pour ça)
- 📦 `pip install faiss-cpu`

**Choix** : **FAISS pour meilleure performance** (recommandé)

#### Option 3 : ChromaDB (Fallback)
- ✅ Simple à utiliser
- ✅ Peut être in-memory ou persisté
- ✅ API Python simple
- ❌ Moins performant que FAISS
- 📦 `pip install chromadb`

---

### 2. Embeddings (Vectorisation du Texte)

#### Bedrock Embeddings API ⭐ SEUL CHOIX (AWS Native)
- ✅ Modèle : `amazon.titan-embed-text-v2` ou `amazon.titan-embed-text-v1`
- ✅ Intégration AWS native (cohérent avec projet)
- ✅ Qualité excellente
- ✅ Pas besoin d'installer modèle local
- ✅ Scalable automatiquement
- ⚠️ Coûts par requête (mais raisonnables : ~$0.0001/1000 tokens)
- ⚠️ Nécessite credentials AWS (déjà configuré)

**Choix** : Bedrock Embeddings uniquement (AWS natif, meilleure qualité)

---

### 3. Modèle de Génération

#### Bedrock Claude Sonnet ⭐ UTILISÉ
- ✅ Déjà configuré dans `chatbot_helper.py`
- ✅ Modèle : `us.anthropic.claude-3-5-sonnet-20241022-v2:0`
- ✅ Excellent pour réponses complexes
- ✅ Support contexte long (200K tokens)
- ✅ Utilise prompt RAG avec contexte

**Choix** : Garder Claude Sonnet (déjà en place)

---

### 4. Sources de Données

#### Données Disponibles :

1. **Extractions Réglementaires** (6 fichiers)
   - 📁 `data/generated/extracted_directives/*_extracted.json`
   - Structure : Titre, pays, secteurs, entités, mesures, dates
   - Format : JSON structuré

2. **Extractions 10-K** (500 fichiers)
   - 📁 `data/generated/extracted_data_points/*.json`
   - Structure : Géographie, segments, supply chain par entreprise
   - Format : JSON par entreprise/ticker

3. **Company Universe** (1 fichier)
   - 📁 `data/generated/company_universe/company_universe.json`
   - Structure : Toutes données consolidées (500 entreprises)
   - Format : JSON avec liste entreprises

**Choix** : Charger les 3 sources pour base de connaissances complète

---

## 🎯 CHOIX TECHNIQUES FINAUX

### Stack Technique RAG - AWS Native + Performance

| Composant | Choix | Raison |
|-----------|-------|--------|
| **Vector Store** | **FAISS** | **Meilleure performance** (recherche ultra-rapide, in-memory) |
| **Embeddings** | **Bedrock Titan uniquement** | **AWS natif**, excellente qualité, cohérent avec projet |
| **Génération** | Bedrock Claude Sonnet | Déjà configuré, excellente qualité |
| **Données** | Toutes (régulations + 10-K + Company Universe) | Base de connaissances complète |
| **Chunking** | 500-800 tokens par chunk | Optimisé pour performance et précision |
| **Framework** | **Aucun (code pur boto3)** | **Pas de LangChain**, utilisation directe AWS SDK (boto3) |
| **Approche** | **AWS Native** | **100% services Amazon**, pas de dépendances externes complexes |

---

## 📊 WORKFLOW DÉTAILLÉ PAR ÉTAPE

### Étape 1 : Initialisation (Une fois au démarrage Streamlit)

```python
# Dans app.py, page Chatbot
@st.cache_resource
def initialize_rag_system():
    """Initialise le système RAG (cache avec Streamlit)"""
    
    # 1. Charger données
    regulatory_data = load_regulatory_extractions()  # 6 fichiers
    tenk_data = load_10k_extractions()              # Échantillon ou tous
    company_universe = load_company_universe()       # 1 fichier
    
    # 2. Créer chunks
    chunks = []
    chunks.extend(chunk_regulatory_extractions(regulatory_data))
    chunks.extend(chunk_10k_extractions(tenk_data))
    chunks.extend(chunk_company_universe(company_universe))
    
    # 3. Générer embeddings (Bedrock uniquement)
    embeddings = generate_embeddings_bedrock(chunks)  # AWS Bedrock Titan
    
    # 4. Créer vector store
    vector_store = RAGVectorStore()
    vector_store.add_documents(chunks, embeddings)
    
    return vector_store
```

### Étape 2 : Recherche (Quand utilisateur pose question)

```python
def search_rag_context(user_query: str, vector_store: RAGVectorStore, top_k: int = 5):
    """Recherche chunks pertinents pour la question"""
    
    # 1. Générer embedding de la question
    query_embedding = generate_embedding(user_query)
    
    # 2. Recherche similarité cosinus
    results = vector_store.search(query_embedding, top_k=top_k)
    
    # 3. Formater résultats
    context_chunks = []
    for result in results:
        context_chunks.append({
            'text': result['chunk_text'],
            'metadata': result['metadata'],
            'similarity': result['score']
        })
    
    return context_chunks
```

### Étape 3 : Génération Prompt RAG

```python
def build_rag_prompt(user_query: str, context_chunks: List[Dict]) -> str:
    """Construit prompt avec contexte RAG"""
    
    # Formater contexte
    context_text = "\n\n".join([
        f"[{chunk['metadata']['type']}] {chunk['text']}"
        for chunk in context_chunks
    ])
    
    prompt = f"""Tu es un assistant financier expert en réglementation et analyse de portefeuilles S&P 500.

CONTEXTE (Base de connaissances extraite de nos documents):
{context_text}

QUESTION UTILISATEUR:
{user_query}

INSTRUCTIONS:
- Réponds UNIQUEMENT en utilisant les informations du contexte fourni ci-dessus
- Si l'information n'est pas dans le contexte, dis-le clairement ("Cette information n'est pas disponible dans nos documents")
- Cite tes sources : mentionne le type de document (réglementation, 10-K, Company Universe) et le nom/titre
- Sois précis avec chiffres, dates, noms d'entreprises (tickers)
- Formatte ta réponse de manière claire avec sections si nécessaire
- Utilise un ton professionnel mais accessible

Réponse:"""
    
    return prompt
```

### Étape 4 : Appel Bedrock avec RAG

```python
def chat_with_rag(user_query: str, vector_store: RAGVectorStore, 
                  conversation_history: List[Dict]) -> Dict:
    """Chat complet avec RAG"""
    
    # 1. Recherche contexte
    context_chunks = search_rag_context(user_query, vector_store, top_k=5)
    
    # 2. Construire prompt RAG
    rag_prompt = build_rag_prompt(user_query, context_chunks)
    
    # 3. Préparer messages pour Bedrock
    messages = conversation_history.copy()
    messages.append({"role": "user", "content": rag_prompt})
    
    # 4. Appel Bedrock
    response = chat_with_claude(
        messages=messages,
        model="us.anthropic.claude-3-5-sonnet-20241022-v2:0",
        max_tokens=4000
    )
    
    # 5. Extraire sources
    sources = [chunk['metadata'] for chunk in context_chunks]
    
    return {
        'response': response['response'],
        'sources': sources,
        'error': response.get('error')
    }
```

---

## ⚙️ CONFIGURATION ET PARAMÈTRES

### Paramètres à Configurer

```python
# Config RAG
RAG_CONFIG = {
    'chunk_size': 800,              # Tokens par chunk
    'chunk_overlap': 100,           # Overlap entre chunks
    'top_k': 5,                     # Nombre chunks à récupérer
    'similarity_threshold': 0.6,     # Score minimum similarité
    'embedding_model': 'bedrock',   # 'bedrock' ou 'sentence-transformers'
    'vector_store': 'chromadb',      # Type de vector store
    'max_context_tokens': 100000,   # Max tokens dans contexte RAG
}
```

### Chemins des Données

```python
DATA_PATHS = {
    'regulatory_extractions': 'data/generated/extracted_directives',
    'tenk_extractions': 'data/generated/extracted_data_points',
    'company_universe': 'data/generated/company_universe/company_universe.json',
    'vector_store_cache': 'data/generated/rag_vector_store',  # Cache pour ChromaDB
}
```

---

## 📦 DÉPENDANCES REQUISES

### Dans `requirements.txt`

```txt
# RAG Dependencies (AWS Native + Performance)
faiss-cpu>=1.7.4                  # Vector store (meilleure performance)
numpy>=1.24.0                      # Pour calculs similarité (déjà installé)
# boto3 déjà installé (AWS SDK)
# Pas besoin de LangChain ou autres frameworks
```

---

## ✅ CHECKLIST IMPLÉMENTATION

### Phase 1 : Structure Base
- [ ] Créer `scripts/rag_helper.py` avec structure de base
- [ ] Classe `RAGVectorStore`
- [ ] Fonctions de chargement données

### Phase 2 : Embeddings AWS
- [ ] Fonction génération embeddings (Bedrock Titan uniquement)
- [ ] Intégration boto3 pour Bedrock Embeddings API
- [ ] Tester génération embeddings
- [ ] Cache embeddings pour éviter appels répétés

### Phase 3 : Vector Store (FAISS)
- [ ] Intégration FAISS
- [ ] Fonction d'indexation (ajout embeddings)
- [ ] Fonction de recherche (similarité cosinus)
- [ ] Optimisation performance (index plat ou IVF)

### Phase 4 : RAG Complet
- [ ] Fonction `search_rag_context()`
- [ ] Fonction `build_rag_prompt()`
- [ ] Fonction `chat_with_rag()`

### Phase 5 : Intégration Streamlit
- [ ] Modifier `chatbot_helper.py`
- [ ] Modifier `app.py` (page Chatbot)
- [ ] Tester workflow complet

---

**Prochaine étape** : Créer `scripts/rag_helper.py` avec cette architecture ! 🚀

