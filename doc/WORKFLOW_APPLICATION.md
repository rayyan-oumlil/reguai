# 🔄 Workflow Application ReguAI - Services Utilisés

## 📊 Workflow Complet de l'Application

### 1️⃣ PAGE DASHBOARD

```
Utilisateur ouvre Dashboard
    ↓
Streamlit charge company_universe.json
    ↓
[OPTIONNEL] Vérifie S3 (si bucket configuré)
    ├─ Amazon S3 → Récupère company_universe.json
    └─ Sinon → Fichier local
    ↓
Pandas transforme JSON → DataFrames
    ↓
Plotly génère visualisations interactives
    ↓
Streamlit affiche Dashboard
```

**Services utilisés** :
- ✅ **Streamlit** - Interface
- ✅ **Pandas** - Traitement données
- ✅ **Plotly** - Visualisations
- 🔶 **Amazon S3** (optionnel) - Stockage company_universe.json

---

### 2️⃣ PAGE ANALYSE DE DOCUMENTS

```
Utilisateur upload document (PDF/HTML/XML/TXT)
    ↓
Vérification cache
    ├─ [AVEC AWS] Amazon S3 → Vérifie cache S3
    │   └─ Si trouvé → Retour résultat (cache)
    └─ [LOCAL] Fichier local → Vérifie cache local
        └─ Si trouvé → Retour résultat (cache)
    ↓
[SI NOUVEAU DOCUMENT]
    ↓
Extraction texte selon format
    ├─ PDF → Amazon Textract (boto3.client('textract'))
    ├─ HTML/XML → BeautifulSoup4
    └─ TXT → Lecture directe
    ↓
Classification avec LegalBERT
    ├─ Transformers → Charge modèle nlpaueb/legal-bert-base-uncased
    ├─ PyTorch → Génère embeddings
    └─ Amazon Bedrock → Classification contextuelle (Claude Sonnet)
    ↓
[OPTIONNEL] Pré-filtrage
    └─ Amazon Comprehend → Détection entités (si AWS activé)
    ↓
Extraction structurée
    └─ Amazon Bedrock (Claude Sonnet)
        └─ Extraction JSON structuré (entités, dates, mesures, etc.)
    ↓
Sauvegarde cache
    ├─ [AVEC AWS] Amazon S3 → Sauvegarde résultat
    └─ [LOCAL] Fichier local → Sauvegarde résultat
    ↓
Streamlit affiche résultats extraits
```

**Services utilisés** :
- ✅ **Streamlit** - Interface upload/affichage
- ✅ **BeautifulSoup4** - Parsing HTML/XML
- ✅ **Transformers + PyTorch** - LegalBERT
- ✅ **Amazon Textract** - Extraction PDF
- ✅ **Amazon Bedrock** (Claude Sonnet) - Extraction structurée
- 🔶 **Amazon S3** (optionnel) - Cache
- 🔶 **Amazon Comprehend** (optionnel) - Pré-filtrage

---

### 3️⃣ PAGE CHATBOT

```
Utilisateur pose question
    ↓
Streamlit envoie question
    ↓
Amazon Bedrock (Claude Sonnet)
    └─ Génère réponse conversationnelle
    ↓
Streamlit affiche réponse
```

**Services utilisés** :
- ✅ **Streamlit** - Interface chat
- ✅ **Amazon Bedrock** (Claude Sonnet) - Génération réponse

---

## 🔄 Flux Détaillé : Analyse de Document (Cas Complet AWS)

```
┌─────────────────────────────────────────────────────────┐
│ 1. UTILISATEUR                                           │
│    Upload document (PDF/HTML/XML)                        │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 2. STREAMLIT                                             │
│    - document_analysis_helper.py                        │
│    - Vérifie cache S3                                    │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 3. AMAZON S3 (si bucket configuré)                      │
│    - Vérifie cache: s3://bucket/extracted_directives/    │
│    - Si existe → Retour cache ✅                         │
└────────────────┬────────────────────────────────────────┘
                 │ (si nouveau)
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 4. EXTRACTION TEXTE                                      │
│    ┌────────────────────────────────────┐               │
│    │ PDF → Amazon Textract              │               │
│    │ HTML/XML → BeautifulSoup4          │               │
│    │ TXT → Lecture directe               │               │
│    └────────────────────────────────────┘               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 5. CLASSIFICATION                                        │
│    ┌────────────────────────────────────┐               │
│    │ LegalBERT (Transformers + PyTorch) │               │
│    │ → Génère embeddings                │               │
│    └────────────────────────────────────┘               │
│    ↓                                                     │
│    Amazon Bedrock (Claude Sonnet)                        │
│    → Classification contextuelle                         │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 6. [OPTIONNEL] PRÉ-FILTRAGE                              │
│    Amazon Comprehend                                     │
│    → Détecte entités (organisations, lieux, dates)      │
│    → Réduit texte avant Bedrock                          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 7. EXTRACTION STRUCTURÉE                                │
│    Amazon Bedrock (Claude Sonnet)                        │
│    → Extrait:                                           │
│      - Entités (entreprises, secteurs, pays)            │
│      - Dates (publication, application)                  │
│      - Mesures (taxes, restrictions)                     │
│      - Montants et seuils                                │
│    → Retourne JSON structuré                            │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 8. SAUVEGARDE CACHE                                     │
│    ┌────────────────────────────────────┐               │
│    │ Amazon S3 → Sauvegarde résultat    │               │
│    │ Fichier local → Sauvegarde backup  │               │
│    └────────────────────────────────────┘               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 9. STREAMLIT                                             │
│    Affiche résultats structurés                         │
│    - Métadonnées document                                │
│    - Entités extraites                                   │
│    - Visualisations (tableaux)                           │
└──────────────────────────────────────────────────────────┘
```

---

## 📋 Récapitulatif Services par Fonctionnalité

### Dashboard
- **Streamlit** ✅
- **Pandas** ✅
- **Plotly** ✅
- **Amazon S3** 🔶 (optionnel)

### Analyse de Documents
- **Streamlit** ✅
- **BeautifulSoup4** ✅
- **Transformers + PyTorch** ✅ (LegalBERT)
- **Amazon Textract** ✅ (PDF)
- **Amazon Bedrock** ✅ (Claude Sonnet)
- **Amazon S3** 🔶 (cache optionnel)
- **Amazon Comprehend** 🔶 (pré-filtrage optionnel)

### Chatbot (Actuel)
- **Streamlit** ✅
- **Amazon Bedrock** ✅ (Claude Sonnet)

---

## 🔄 Flux Détaillé : Chatbot RAG (Implémenté à 100%)

```
┌─────────────────────────────────────────────────────────┐
│ 1. UTILISATEUR                                           │
│    Pose question dans interface chat                    │
│    Ex: "Quel est l'impact sur Apple de la loi chinoise?"│
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 2. STREAMLIT                                             │
│    - chatbot_helper.py                                  │
│    - Reçoit question utilisateur                        │
│    - Vérifie si base RAG initialisée                    │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 3. VÉRIFICATION BASE RAG                                │
│    ┌────────────────────────────────────┐               │
│    │ Si première utilisation:           │               │
│    │ → Initialisation RAG nécessaire    │               │
│    │                                     │               │
│    │ Si déjà initialisée:                │               │
│    │ → Passe à recherche vectorielle    │               │
│    └────────────────────────────────────┘               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 4. [SI PREMIÈRE FOIS] INITIALISATION BASE RAG            │
│    ┌────────────────────────────────────┐               │
│    │ Charger sources depuis S3/local:   │               │
│    │ - 6 extractions réglementaires      │               │
│    │   (data/generated/extracted_directives/)            │
│    │ - 500 extractions 10-K             │               │
│    │   (data/generated/extracted_data_points/)           │
│    │ - Company Universe                 │               │
│    │   (data/generated/company_universe/)                │
│    └────────────────────────────────────┘               │
│    ↓                                                     │
│    ┌────────────────────────────────────┐               │
│    │ Préprocessing:                     │               │
│    │ - Convertir JSON → texte            │               │
│    │ - Nettoyer et structurer           │               │
│    │ - Ajouter métadonnées              │               │
│    └────────────────────────────────────┘               │
│    ↓                                                     │
│    ┌────────────────────────────────────┐               │
│    │ Chunking:                          │               │
│    │ - Diviser en chunks 500-1000 tokens│               │
│    │ - Chevauchement 100 tokens         │               │
│    │ - Métadonnées par chunk            │               │
│    └────────────────────────────────────┘               │
│    ↓                                                     │
│    ┌────────────────────────────────────┐               │
│    │ Génération Embeddings:             │               │
│    │ Amazon Bedrock Titan Embeddings    │               │
│    │ → Vecteurs 1024 dimensions         │               │
│    └────────────────────────────────────┘               │
│    ↓                                                     │
│    ┌────────────────────────────────────┐               │
│    │ Indexation:                        │               │
│    │ Amazon OpenSearch Serverless       │               │
│    │ → Stocke vecteurs + métadonnées    │               │
│    └────────────────────────────────────┘               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 5. GÉNÉRATION EMBEDDING DE LA QUESTION                  │
│    Amazon Bedrock (Titan Embeddings)                    │
│    → Convertit question en vecteur 1024D                │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 6. RECHERCHE VECTORIELLE                                │
│    Amazon OpenSearch Serverless                         │
│    → Recherche sémantique (similarité cosinus)          │
│    → Récupère top K=5 chunks pertinents                 │
│    → Retourne chunks + métadonnées (source, type)       │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 7. VÉRIFICATION CONTEXTE                                │
│    ┌────────────────────────────────────┐               │
│    │ Si chunks trouvés:                │               │
│    │ → Construire prompt avec contexte  │               │
│    │                                     │               │
│    │ Si aucun chunk pertinent:          │               │
│    │ → Générer réponse sans contexte    │               │
│    └────────────────────────────────────┘               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 8. ENRICHISSEMENT TEMPS RÉEL (si nécessaire)           │
│    ┌────────────────────────────────────┐               │
│    │ Si question nécessite données     │               │
│    │ marché récentes:                   │               │
│    │ → Yahoo Finance (yfinance)        │               │
│    │   - Prix actuels actions          │               │
│    │   - Volatilité (Beta)              │               │
│    │   - Volume trading                 │               │
│    │   - Market cap temps réel          │               │
│    └────────────────────────────────────┘               │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 9. CONSTRUCTION PROMPT ENRICHI                          │
│    Prompt =                                             │
│    - Question utilisateur                               │
│    - Contexte RAG (chunks pertinents)                  │
│    - Données marché (yfinance si applicable)          │
│    - Instructions système                               │
│    - Historique conversation (si multi-tours)          │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 10. GÉNÉRATION RÉPONSE                                  │
│     Amazon Bedrock (Claude Sonnet)                      │
│     → Analyse contexte RAG                              │
│     → Combine avec données yfinance si applicable      │
│     → Génère réponse contextuelle                       │
│     → Inclut citations sources (chunks utilisés)       │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 11. FORMATAGE RÉPONSE                                    │
│     - Réponse principale                                │
│     - Citations sources (chunks RAG)                     │
│     - Métadonnées (réglementation, entreprise, etc.)    │
│     - Données marché (si yfinance utilisé)             │
└────────────────┬────────────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────────────┐
│ 12. STREAMLIT                                            │
│     Affiche réponse complète:                          │
│     - Réponse conversationnelle                        │
│     - Sources citées (avec liens)                       │
│     - Métadonnées contextuelles                        │
│     - Graphiques données marché (si applicable)        │
└──────────────────────────────────────────────────────────┘
```

**Services utilisés** :
- ✅ **Streamlit** - Interface chat
- ✅ **Amazon Bedrock** (Titan Embeddings) - Embeddings question et documents
- ✅ **Amazon Bedrock** (Claude Sonnet) - Génération réponse
- ✅ **Amazon OpenSearch Serverless** - Base vectorielle et recherche
- ✅ **Amazon S3** - Stockage documents sources
- ✅ **Yahoo Finance** (yfinance) - Enrichissement données marché temps réel
- ✅ **LangChain** - Orchestration RAG


### Stack Technique Chatbot RAG (Futur)

**Services AWS** :
- ✅ **Amazon Bedrock** (Claude Sonnet) - Génération réponse
- ✅ **Amazon Bedrock** (Titan Embeddings) - Génération embeddings
- ✅ **Amazon OpenSearch Serverless** - Base vectorielle et recherche
- ✅ **Amazon S3** - Stockage documents sources

**Technologies** :
- ✅ **Streamlit** - Interface chat
- ✅ **LangChain** - Orchestration RAG
- ✅ **ChromaDB** (optionnel local) - Alternative à OpenSearch
- ✅ **boto3** - SDK AWS

---

**Légende** :
- ✅ **Utilisé activement** dans le code
- 🔶 **Optionnel** - Utilisé si AWS configuré
- 🚀 **Futur** - À implémenter (Chatbot RAG)

