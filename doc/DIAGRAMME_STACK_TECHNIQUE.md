# 🏗️ Diagramme de la Stack Technique - ReguAI

**Datathon PolyFinances 2025**

Ce document présente une vue complète de la stack technique utilisée dans ReguAI, organisée par processus et fonctionnalité.

---

## 📋 Table des Matières

1. [Vue d'Ensemble Globale](#vue-densemble-globale)
2. [Processus 1 : Dashboard](#processus-1--dashboard)
3. [Processus 2 : Analyse de Documents Réglementaires](#processus-2--analyse-de-documents-réglementaires)
4. [Processus 3 : Extraction de Données 10-K](#processus-3--extraction-de-données-10-k)
5. [Processus 4 : Chatbot RAG](#processus-4--chatbot-rag)
6. [Processus 5 : Analyse d'Impact (3-Tiers)](#processus-5--analyse-dimpact-3-tiers)
7. [Processus 6 : Génération de Recommandations](#processus-6--génération-de-recommandations)
8. [Récapitulatif Complet](#récapitulatif-complet)

---

## 🎯 Vue d'Ensemble Globale

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          REGUAI - ARCHITECTURE GLOBALE                   │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   INTERFACE     │    │   PROCESSING    │    │   STORAGE       │
│   Streamlit     │───▶│   AWS Services  │───▶│   S3 / Local    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   VISUALIZATION │    │   AI MODELS     │    │   DATA          │
│   Plotly        │    │   Bedrock       │    │   JSON/CSV      │
└─────────────────┘    │   LegalBERT     │    └─────────────────┘
                       │   FinBERT       │
                       └─────────────────┘
```

---

## 📊 Processus 1 : Dashboard

### Stack Technique

```
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSUS : DASHBOARD                        │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  UTILISATEUR │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ STREAMLIT (app.py → dashboard_helper.py)                     │
│ - Interface utilisateur                                       │
│ - Navigation multi-pages                                     │
│ - Gestion de l'état                                           │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ CHARGEMENT DONNÉES                                            │
│ ├─ Company Universe (JSON)                                    │
│ │  └─ data/generated/company_universe/company_universe.json │
│ ├─ [Optionnel] Amazon S3                                      │
│ │  └─ s3://bucket/company_universe.json                      │
│ └─ [Fallback] Fichier local                                   │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ PANDAS                                                        │
│ - Transformation JSON → DataFrames                            │
│ - Agrégations et calculs                                      │
│ - Filtrage et tri                                             │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ PLOTLY                                                        │
│ - Treemap sectoriel                                           │
│ - Graphiques de composition                                   │
│ - Tableaux interactifs                                        │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ STREAMLIT - AFFICHAGE                                         │
│ - KPIs (métriques principales)                                 │
│ - Visualisations interactives                                  │
│ - Tableaux de données                                         │
└──────────────────────────────────────────────────────────────┘
```

### Technologies et Outils

| Catégorie | Technologie | Version | Usage |
|-----------|------------|---------|-------|
| **Interface** | Streamlit | >= 1.28.0 | Application web interactive |
| **Données** | Pandas | >= 2.0.0 | Manipulation de données |
| **Visualisation** | Plotly | >= 5.17.0 | Graphiques interactifs |
| **Stockage** | Amazon S3 | (via boto3) | Stockage optionnel |
| **Format** | JSON | - | Format de données |

---

## 📄 Processus 2 : Analyse de Documents Réglementaires

### Stack Technique

```
┌─────────────────────────────────────────────────────────────────┐
│         PROCESSUS : ANALYSE DE DOCUMENTS RÉGLEMENTAIRES         │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  UTILISATEUR │ Upload document (PDF/HTML/XML/TXT)
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ STREAMLIT (document_analysis_helper.py)                      │
│ - Gestion upload de fichiers                                  │
│ - Interface utilisateur                                       │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ VÉRIFICATION CACHE                                            │
│ ├─ [AVEC AWS] Amazon S3                                       │
│ │  └─ Vérifie cache S3                                        │
│ ├─ [LOCAL] Fichier local                                      │
│ │  └─ data/generated/extracted_directives/                    │
│ └─ Si cache trouvé → Retour résultat ✅                       │
└──────┬───────────────────────────────────────────────────────┘
       │ (si nouveau document)
       ▼
┌──────────────────────────────────────────────────────────────┐
│ EXTRACTION TEXTE SELON FORMAT                                 │
│ ├─ PDF                                                        │
│ │  └─ Amazon Textract (boto3.client('textract'))             │
│ │     └─ Extraction OCR depuis images/PDF                      │
│ ├─ HTML/XML                                                   │
│ │  └─ BeautifulSoup4 >= 4.12.0                                │
│ │     └─ Parsing HTML/XML                                     │
│ └─ TXT                                                        │
│    └─ Lecture directe                                          │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ CLASSIFICATION LEGALBERT                                      │
│ ├─ Transformers >= 4.21.0                                     │
│ │  └─ Charge modèle : nlpaueb/legal-bert-base-uncased         │
│ ├─ PyTorch >= 2.0.0                                           │
│ │  └─ Backend pour transformers                               │
│ └─ Génère embeddings pour classification                      │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ [OPTIONNEL] PRÉ-FILTRAGE                                      │
│ Amazon Comprehend (boto3.client('comprehend'))               │
│ ├─ Détection d'entités (organisations, lieux, dates)          │
│ └─ Détection de phrases clés                                 │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ EXTRACTION STRUCTURÉE                                         │
│ Amazon Bedrock (boto3.client('bedrock-runtime'))              │
│ ├─ Modèle : Claude Sonnet 4.5                                 │
│ │  global.anthropic.claude-sonnet-4-5-20250929-v1:0         │
│ ├─ Instructor[bedrock] >= 1.0.0                               │
│ │  └─ Extraction structurée avec Pydantic                   │
│ └─ Pydantic >= 2.0.0                                          │
│    └─ Validation et structuration des données                 │
│                                                                │
│ Extrait :                                                     │
│ - Titre, date, pays                                           │
│ - Secteurs affectés                                           │
│ - Entités mentionnées                                         │
│ - Mesures (taxes, restrictions)                                │
│ - Seuils monétaires                                           │
│ - Exigences clés                                              │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ SAUVEGARDE CACHE                                              │
│ ├─ [AVEC AWS] Amazon S3                                       │
│ │  └─ Sauvegarde résultat                                     │
│ └─ [LOCAL] Fichier local                                      │
│    └─ data/generated/extracted_directives/*_extracted.json   │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ STREAMLIT - AFFICHAGE RÉSULTATS                               │
│ - Métadonnées document                                        │
│ - Entités extraites                                           │
│ - Visualisations (tableaux)                                    │
└──────────────────────────────────────────────────────────────┘
```

### Technologies et Outils

| Catégorie | Technologie | Version | Usage |
|-----------|------------|---------|-------|
| **Interface** | Streamlit | >= 1.28.0 | Interface upload/affichage |
| **Parsing** | BeautifulSoup4 | >= 4.12.0 | Parsing HTML/XML |
| **Parsing** | lxml | >= 4.9.0 | Parseur XML efficace |
| **OCR** | Amazon Textract | (via boto3) | Extraction texte depuis PDF |
| **NLP** | Transformers | >= 4.21.0 | Framework pour LegalBERT |
| **NLP** | PyTorch | >= 2.0.0 | Backend pour transformers |
| **Modèle NLP** | LegalBERT | nlpaueb/legal-bert-base-uncased | Classification documents juridiques |
| **IA Générative** | Amazon Bedrock | (via boto3) | Extraction structurée |
| **Modèle LLM** | Claude Sonnet 4.5 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 | Génération et extraction |
| **Extraction** | Instructor[bedrock] | >= 1.0.0 | Extraction structurée avec Pydantic |
| **Validation** | Pydantic | >= 2.0.0 | Validation de données |
| **NLP AWS** | Amazon Comprehend | (via boto3) | Détection entités/phrases (optionnel) |
| **Stockage** | Amazon S3 | (via boto3) | Cache optionnel |
| **Format** | JSON | - | Format de sortie |

---

## 📈 Processus 3 : Extraction de Données 10-K

### Stack Technique

```
┌─────────────────────────────────────────────────────────────────┐
│              PROCESSUS : EXTRACTION DE DONNÉES 10-K              │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  RAPPORT 10-K│ (fichier HTML/XML)
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ SEC-PARSER >= 0.25.0                                          │
│ - Parsing spécialisé pour rapports SEC                       │
│ - Extraction de structure (sections, tableaux)               │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ PRÉ-TRAITEMENT                                                │
│ - Nettoyage du texte                                          │
│ - Identification des sections                                 │
│ - Extraction des tableaux                                     │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ EXTRACTION STRUCTURÉE                                         │
│ Amazon Bedrock                                                │
│ ├─ Modèle : Claude Sonnet 4.5                                 │
│ │  global.anthropic.claude-sonnet-4-5-20250929-v1:0         │
│ ├─ Instructor[bedrock] >= 1.0.0                               │
│ └─ Pydantic >= 2.0.0                                          │
│                                                                │
│ Extrait :                                                     │
│ - Géographie (pays/zones d'opérations)                        │
│ - Segments d'affaires                                         │
│ - Chaîne d'approvisionnement                                  │
│ - Dépendances critiques                                       │
│ - Risques réglementaires mentionnés                           │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ SAUVEGARDE                                                    │
│ data/generated/extracted_data_points/{ticker}_data.json       │
└──────────────────────────────────────────────────────────────┘
```

### Technologies et Outils

| Catégorie | Technologie | Version | Usage |
|-----------|------------|---------|-------|
| **Parsing SEC** | sec-parser | >= 0.25.0 | Parsing rapports SEC (10-K) |
| **IA Générative** | Amazon Bedrock | (via boto3) | Extraction structurée |
| **Modèle LLM** | Claude Sonnet 4.5 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 | Extraction |
| **Extraction** | Instructor[bedrock] | >= 1.0.0 | Extraction structurée |
| **Validation** | Pydantic | >= 2.0.0 | Validation de données |
| **Format** | JSON | - | Format de sortie |

---

## 🤖 Processus 4 : Chatbot RAG

### Stack Technique

```
┌─────────────────────────────────────────────────────────────────┐
│                      PROCESSUS : CHATBOT RAG                     │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│  UTILISATEUR │ Pose une question
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ STREAMLIT (chatbot_helper.py)                                 │
│ - Interface conversationnelle                                  │
│ - Historique de conversation                                   │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ [PREMIÈRE FOIS] INITIALISATION BASE RAG                        │
│ scripts/rag/                                                   │
│ ├─ data_loader.py                                              │
│ │  └─ Charge sources :                                         │
│ │     - Extractions réglementaires (6 fichiers)                │
│ │     - Extractions 10-K (500 fichiers)                        │
│ │     - Company Universe (1 fichier)                           │
│ ├─ Formatage en Documents LangChain                            │
│ │  └─ Conversion JSON → texte + métadonnées                    │
│ └─ Chunking                                                    │
│    └─ Divise en chunks 800 tokens (overlap 100)                │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ GÉNÉRATION EMBEDDINGS                                         │
│ Amazon Bedrock                                                │
│ ├─ Modèle : Cohere Embed v4                                   │
│ │  global.cohere.embed-v4:0                                   │
│ ├─ Dimension : 1024                                           │
│ └─ LangChain AWS >= 0.1.0                                     │
│    └─ Intégration Bedrock dans LangChain                      │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ INDEXATION VECTOR STORE                                        │
│ FAISS-CPU >= 1.7.4                                             │
│ ├─ Stockage des vecteurs embeddings                           │
│ ├─ Recherche par similarité cosinus                            │
│ └─ Cache : data/generated/rag_cache/vector_store/             │
│    ├─ index.faiss                                              │
│    └─ index.pkl                                                │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ QUESTION UTILISATEUR                                           │
│ Génération embedding de la question                           │
│ └─ Amazon Bedrock (Cohere Embed v4)                           │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ RECHERCHE VECTORIELLE                                         │
│ FAISS                                                          │
│ ├─ Recherche similarité cosinus                                │
│ ├─ Top K = 8 chunks pertinents                                │
│ └─ Retourne chunks + métadonnées (source, type)              │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ CONSTRUCTION PROMPT ENRICHI                                   │
│ LangChain >= 0.1.0                                             │
│ ├─ Question utilisateur                                       │
│ ├─ Contexte RAG (top 8 chunks)                                │
│ ├─ Instructions système                                        │
│ └─ Historique conversation (si multi-tours)                    │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ GÉNÉRATION RÉPONSE                                            │
│ Amazon Bedrock                                                │
│ ├─ Modèle : Claude Sonnet 4.5                                 │
│ │  global.anthropic.claude-sonnet-4-5-20250929-v1:0         │
│ ├─ LangChain AWS >= 0.1.0                                     │
│ │  └─ Integration Bedrock dans LangChain                      │
│ ├─ Temperature : 0.1 (factuel)                               │
│ └─ Max tokens : 4000                                          │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ FORMATAGE RÉPONSE                                             │
│ ├─ Réponse principale                                         │
│ ├─ Citations sources (chunks RAG)                              │
│ └─ Métadonnées                                                │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ STREAMLIT - AFFICHAGE                                         │
│ - Réponse conversationnelle                                   │
│ - Sources citées                                               │
│ - Métadonnées contextuelles                                   │
└──────────────────────────────────────────────────────────────┘
```

### Technologies et Outils

| Catégorie | Technologie | Version | Usage |
|-----------|------------|---------|-------|
| **Interface** | Streamlit | >= 1.28.0 | Interface chat |
| **RAG Framework** | LangChain | >= 0.1.0 | Orchestration RAG |
| **RAG AWS** | LangChain AWS | >= 0.1.0 | Intégration AWS Bedrock |
| **Vector Store** | FAISS-CPU | >= 1.7.4 | Stockage et recherche vectorielle |
| **Embeddings** | Amazon Bedrock | (via boto3) | Génération embeddings |
| **Modèle Embeddings** | Cohere Embed v4 | global.cohere.embed-v4:0 | Embeddings 1024D |
| **IA Générative** | Amazon Bedrock | (via boto3) | Génération réponse |
| **Modèle LLM** | Claude Sonnet 4.5 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 | Génération réponse |
| **Community** | LangChain Community | >= 0.0.20 | Vector stores additionnels |

---

## 📊 Processus 5 : Analyse d'Impact (3-Tiers)

### Architecture 3-Tiers

```
┌─────────────────────────────────────────────────────────────────┐
│            PROCESSUS : ANALYSE D'IMPACT (3-TIERS)                │
└─────────────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════╗
║                      TIER 1 : MATCHING PAIRS                     ║
╚═══════════════════════════════════════════════════════════════════╝

┌──────────────┐         ┌──────────────┐
│ RÉGULATIONS  │         │  COMPANIES   │
│ (JSON)       │         │  (JSON)      │
└──────┬───────┘         └──────┬───────┘
       │                       │
       └───────────┬───────────┘
                   │
                   ▼
┌──────────────────────────────────────────────────────────────┐
│ IMPACT ORCHESTRATOR (impact_calculator.py)                   │
│ └─ Coordonne le processus                                     │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ AMAZON COMPREHEND                                             │
│ └─ Détection entités et phrases clés                          │
│    - Organisations                                            │
│    - Lieux (pays/zones)                                       │
│    - Dates                                                    │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ MATCHING PAIRS ENGINE                                         │
│ └─ Calcule scores d'exposition (0-100)                        │
│    ├─ Matching par pays/zones (max 25 pts)                    │
│    ├─ Matching par secteur (max 30 pts)                       │
│    ├─ Matching par nom - fuzzy (max 20 pts)                   │
│    ├─ Matching par dépendances (max 10 pts)                   │
│    ├─ Matching par segments (max 10 pts)                      │
│    └─ Matching par risques réglementaires (max 5 pts)          │
│                                                                │
│ Outils :                                                      │
│ - difflib.SequenceMatcher (fuzzy matching)                    │
│ - Pandas (manipulation données)                               │
│ - Python standard library                                     │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ OUTPUT : MATCHING PAIRS                                       │
│ └─ data/generated/impact_analysis/matching_pairs.json         │
│    - Paires regulation-company                                │
│    - Scores d'exposition                                       │
│    - Détails de matching                                      │
└──────────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════╗
║                  TIER 2 : QUANT ENGINE (SI --quant-engine)      ║
╚═══════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────┐
│ QUANT ENGINE                                                 │
│ └─ Traitement multi-sources                                 │
└──────┬───────────────────────────────────────────────────────┘
       │
       ├───────────────────────────────────────────────────────┐
       │                                                         │
       ▼                                                         ▼
┌─────────────────────────┐              ┌─────────────────────────┐
│ FINANCIAL DATA PROCESSOR │              │ REGULATORY DATA         │
│ Company Universe DB →   │              │ PROCESSOR               │
│                          │              │ Regulation →            │
│ Calculs financiers :     │              │                         │
│ - Liquidity Ratio        │              │ Calculs réglementaires: │
│ - Profitability Ratio    │              │ - Financial Severity    │
│ - Cash Conversion        │              │ - Operational Severity  │
│ - Financial Health Score │              │ - Compliance Complexity │
│                          │              │ - Overall Severity      │
│ [FUTUR] SageMaker        │              │                         │
│ FinBERT (optionnel)      │              │ [FUTUR] SageMaker       │
└─────────────────────────┘              │ LegalBERT (optionnel)    │
                                         └─────────────────────────┘
       │                                                         │
       └───────────────────┬─────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────┐
│ MARKET DATA ENRICHER                                          │
│ Yahoo Finance API (yfinance >= 0.2.0)                        │
│ └─ Données de marché temps réel :                            │
│    - Prix actuel et market cap                               │
│    - Volatilité annualisée                                    │
│    - Évolution prix (30 jours)                                │
│    - Volume et tendance                                       │
│    - Beta et niveau de risque                                │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ QUANTITATIVE IMPACT SCORE (0-100)                             │
│ └─ Combinaison :                                             │
│    - Vulnérabilité financière (40%)                           │
│    - Sévérité réglementaire (60%)                             │
└──────────────────────────────────────────────────────────────┘

╔═══════════════════════════════════════════════════════════════════╗
║                  TIER 3 : DCF VALUATION (SI TIER 2)              ║
╚═══════════════════════════════════════════════════════════════════╝

┌──────────────────────────────────────────────────────────────┐
│ TIER 3.1 : CASH FLOW IMPACT                                   │
│ └─ Calcul impact sur Free Cash Flow                          │
│    - Annual FCF Impact                                        │
│    - FCF Impact per Share                                     │
│    - FCF Impact Percentage                                    │
│    - Scénarios : Conservative/Base/Aggressive                │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ TIER 3.2 : RISK PREMIUM ADJUSTMENT                            │
│ └─ Ajustement taux d'actualisation (CAPM)                    │
│    - Base Discount Rate (CAPM)                                │
│    - Regulatory Risk Premium (0-3%)                           │
│    - Adjusted Discount Rate                                   │
│    - Discount Rate Change (basis points)                      │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ TIER 3.3 : DCF VALUATION                                      │
│ └─ Impact sur valorisation                                   │
│    - NPV Cash Flow Impact                                     │
│    - NPV Terminal Value                                       │
│    - Total Valuation Impact                                   │
│    - Price Impact Percentage                                  │
│    - Modèle : Gordon Growth (perpetuity 3%)                   │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ FINAL RISK SCORER                                             │
│ └─ Score de risque synthétique final (0-100)                  │
│    Composants pondérés :                                     │
│    - Exposure Score (30%)                                     │
│    - Quantitative Impact (40%)                                │
│    - Price Impact (30%)                                       │
│    - Portfolio Weight Multiplier                              │
│                                                                │
│ Classification :                                              │
│ - Critical (≥75)                                             │
│ - High (60-74)                                                │
│ - Moderate (40-59)                                            │
│ - Low (20-39)                                                 │
│ - Minimal (<20)                                               │
└──────────────────────────────────────────────────────────────┘
```

### Technologies et Outils

| Tier | Catégorie | Technologie | Version | Usage |
|------|-----------|------------|---------|-------|
| **Tier 1** | **NLP AWS** | Amazon Comprehend | (via boto3) | Détection entités/phrases |
| **Tier 1** | **Matching** | difflib | (Python stdlib) | Fuzzy matching |
| **Tier 1** | **Données** | Pandas | >= 2.0.0 | Manipulation données |
| **Tier 2** | **API Externe** | yfinance | >= 0.2.0 | Données marché temps réel |
| **Tier 2** | **ML [Futur]** | SageMaker FinBERT | (à intégrer) | Analyse financière |
| **Tier 2** | **ML [Futur]** | SageMaker LegalBERT | (à intégrer) | Analyse réglementaire |
| **Tier 3** | **Calculs** | Python standard | - | Calculs financiers DCF |

---

## 💡 Processus 6 : Génération de Recommandations

### Stack Technique

```
┌─────────────────────────────────────────────────────────────────┐
│          PROCESSUS : GÉNÉRATION DE RECOMMANDATIONS               │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐
│ ANALYSE      │ Matching pairs + impact analysis
│ D'IMPACT     │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ RECOMMENDATION GENERATOR                                       │
│ scripts/recommendation_generator.py                           │
│ └─ Prend en entrée :                                          │
│    - Matching pairs                                            │
│    - Scores d'impact                                           │
│    - Données entreprises                                       │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ AMAZON BEDROCK                                                │
│ ├─ Modèle : Claude Sonnet 4.5                                 │
│ │  global.anthropic.claude-sonnet-4-5-20250929-v1:0         │
│ │  (fallback: us.anthropic.claude-3-5-sonnet-20241022-v2:0) │
│ └─ Génération recommandations :                               │
│    - Actions : BUY / HOLD / SELL                              │
│    - Justifications détaillées                                │
│    - Impact réglementaire                                     │
│    - Recommandations sectorielles                             │
│    - Réallocation suggérée                                    │
└──────┬───────────────────────────────────────────────────────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│ SAUVEGARDE                                                    │
│ data/generated/recommendations/recommendations.json          │
│ └─ Format structuré avec :                                   │
│    - Entreprises et actions                                   │
│    - Scores et justifications                                │
│    - Recommandations agrégées                                │
└──────────────────────────────────────────────────────────────┘
```

### Technologies et Outils

| Catégorie | Technologie | Version | Usage |
|-----------|------------|---------|-------|
| **IA Générative** | Amazon Bedrock | (via boto3) | Génération recommandations |
| **Modèle LLM** | Claude Sonnet 4.5 | global.anthropic.claude-sonnet-4-5-20250929-v1:0 | Génération |
| **Format** | JSON | - | Format de sortie |

---

## 📋 Récapitulatif Complet

### Services AWS Utilisés

| Service AWS | Usage | Modèles/Endpoints |
|------------|-------|-------------------|
| **Amazon Bedrock** | IA générative (extraction, RAG, recommandations) | Claude Sonnet 4.5, Cohere Embed v4 |
| **Amazon Textract** | Extraction texte depuis PDF | OCR standard |
| **Amazon Comprehend** | Détection entités et phrases clés | NLP pré-entraîné |
| **Amazon S3** | Stockage et cache (optionnel) | Buckets S3 |

### Modèles IA et NLP

| Modèle | Provider | Usage | Dimension/Version |
|--------|----------|-------|------------------|
| **Claude Sonnet 4.5** | Anthropic (via Bedrock) | Extraction, RAG, Recommandations | global.anthropic.claude-sonnet-4-5-20250929-v1:0 |
| **Cohere Embed v4** | Cohere (via Bedrock) | Embeddings pour RAG | global.cohere.embed-v4:0 (1024D) |
| **LegalBERT** | Hugging Face | Classification documents juridiques | nlpaueb/legal-bert-base-uncased |
| **FinBERT** | SageMaker (futur) | Analyse financière | À intégrer |
| **LegalBERT (SageMaker)** | SageMaker (futur) | Analyse réglementaire | À intégrer |

### Bibliothèques Python Principales

| Bibliothèque | Version | Usage Principal |
|--------------|---------|-----------------|
| **Streamlit** | >= 1.28.0 | Interface web |
| **Pandas** | >= 2.0.0 | Manipulation données |
| **Plotly** | >= 5.17.0 | Visualisations |
| **LangChain** | >= 0.1.0 | Orchestration RAG |
| **FAISS-CPU** | >= 1.7.4 | Vector store |
| **Transformers** | >= 4.21.0 | LegalBERT |
| **PyTorch** | >= 2.0.0 | Backend ML |
| **BeautifulSoup4** | >= 4.12.0 | Parsing HTML/XML |
| **sec-parser** | >= 0.25.0 | Parsing rapports SEC |
| **boto3** | >= 1.28.0 | SDK AWS |
| **yfinance** | >= 0.2.0 | Données marché |
| **Instructor[bedrock]** | >= 1.0.0 | Extraction structurée |
| **Pydantic** | >= 2.0.0 | Validation données |

