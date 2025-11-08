# 🚀 ReguAI - Regulatory Intelligence Assistant

<img src="doc/Logo.png" alt="ReguAI Logo" width="200">

**Datathon PolyFinances 2025**

## 📋 Description

ReguAI est une application web interactive permettant d'analyser l'impact des réglementations sur le portefeuille S&P 500 en utilisant l'IA générative (Amazon Bedrock).

### 🎯 Vision

ReguAI transforme la complexité réglementaire en opportunité d'aide à la décision pour la gestion de portefeuilles d'actions. Notre système analyse automatiquement les réglementations, identifie les entreprises à risque, et génère des recommandations de trading basées sur l'IA.

## 🎯 Fonctionnalités

- **📊 Dashboard** : Vue globale du portefeuille S&P 500 avec visualisations interactives
- **📄 Analyse de Documents** : Extraction automatique d'informations depuis documents réglementaires
- **🤖 Chatbot Financier** : Interface conversationnelle pour poser des questions
- **📊 Analyse d'Impact** : Calcul de l'impact réglementaire sur les entreprises

## 🚀 Installation et Démarrage

### Prérequis

- Python 3.8+
- AWS Account (pour Bedrock, Textract, S3)
- Credentials AWS configurés

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

**Note** : L'installation peut prendre du temps car elle inclut PyTorch et LegalBERT (~1.5 GB).

### 2. Configuration AWS

**⚠️ IMPORTANT** : L'application nécessite des credentials AWS pour fonctionner (Bedrock est obligatoire pour l'extraction et le RAG).

#### Méthodes de Configuration

Le projet supporte plusieurs méthodes pour configurer les credentials AWS, mais **nous recommandons fortement le fichier `.env`** car le code charge explicitement ce fichier à chaque démarrage :

##### ✅ **Recommandé : Fichier `.env`**

Créez un fichier `.env` à la racine du projet :

```bash
# Obligatoire pour Bedrock (extraction et RAG)
AWS_ACCESS_KEY_ID=votre_access_key
AWS_SECRET_ACCESS_KEY=votre_secret_key
AWS_REGION=us-east-1

# Optionnel mais recommandé (pour cache S3)
S3_BUCKET_NAME=datathon-reguai
```

**Pourquoi recommander `.env` ?**

- Le code charge explicitement le `.env` à chaque démarrage de l'application
- Plus facile à gérer et à partager (sans exposer les credentials)
- Fonctionne de manière fiable avec Streamlit et les notebooks

##### Autres méthodes (fonctionnent mais moins recommandées)

1. **AWS CLI** (`aws configure`) :

   ```bash
   aws configure
   ```

   - Crée `~/.aws/credentials` et `~/.aws/config`
   - Boto3 détecte automatiquement ces fichiers
   - ⚠️ Peut ne pas fonctionner si le code force le rechargement du `.env`
2. **Variables d'environnement système** :

   ```bash
   export AWS_ACCESS_KEY_ID=votre_clé
   export AWS_SECRET_ACCESS_KEY=votre_secret
   export AWS_DEFAULT_REGION=us-east-1
   ```

   - Fonctionne mais moins pratique pour le développement
3. **SageMaker Studio** (si vous travaillez dans SageMaker) :

   - Détection automatique du bucket S3 depuis le projet
   - Les credentials sont gérées par le rôle IAM de SageMaker

#### Services AWS Requis

**Obligatoire** :

- **Amazon Bedrock** : Accès aux modèles Claude (Haiku, Sonnet) et Cohere (embeddings)
  - Permissions : `bedrock:InvokeModel`, `bedrock:ListFoundationModels`

**Optionnels** (améliorent les performances) :

- **Amazon S3** : Cache des extractions et stockage
  - Permissions : `s3:PutObject`, `s3:GetObject`, `s3:ListBucket`
- **Amazon Comprehend** : Pré-filtrage pour réduire les coûts Bedrock
  - Permissions : `comprehend:DetectEntities`, `comprehend:DetectSentiment`
- **Amazon Textract** : Extraction de texte depuis PDF scannés
  - Permissions : `textract:DetectDocumentText`, `textract:AnalyzeDocument`

#### Différences Fonctionnelles

**Mode SANS AWS (ou mal configuré)** :

- ✅ Dashboard (visualisation des données existantes)
- ✅ Visualisation des extractions déjà effectuées
- ❌ Analyse de nouveaux documents réglementaires
- ❌ Chatbot RAG
- ❌ Analyse d'impact réglementaire
- ❌ Génération de recommandations

**Mode AVEC AWS (credentials configurés)** :

- ✅ Toutes les fonctionnalités ci-dessus
- ✅ Analyse de documents réglementaires (Bedrock)
- ✅ Chatbot RAG avec base de connaissances
- ✅ Analyse d'impact réglementaire
- ✅ Génération de recommandations

**Mode AVEC S3 Bucket configuré** (en plus) :

- ✅ Cache S3 pour éviter les re-extractions
- ✅ Sauvegarde des documents sur S3
- ✅ Partage des extractions entre utilisateurs

#### Vérification de la Configuration

Pour tester si AWS est bien configuré, lancez l'application et vérifiez :

- Si vous voyez un message "✅ AWS credentials detected" dans les logs
- Si les fonctionnalités d'analyse sont disponibles (pas en mode "visualisation uniquement")

Voir `README_AWS_SETUP.md` pour plus de détails sur la configuration avancée.

### 3. Générer les données (si nécessaire)

Si vous devez régénérer les données de marché :

```bash
python scripts/generate_key_market_data.py
```

Pour générer le Company Universe consolidé (fusion Market Data + Data Points 10-K) :

```bash
# Utiliser le notebook
jupyter notebook notebooks/extraction/generate_company_universe.ipynb
```

Pour traiter un document réglementaire :

```bash
python scripts/processing/process_regulatory_document.py --file_path data/raw/directives/document.html --output_dir data/generated/extracted_directives/
```

### 4. Lancer l'application Streamlit

```bash
python -m streamlit run scripts/app.py
```

L'application s'ouvrira automatiquement dans votre navigateur à l'adresse `http://localhost:8501`

## 📁 Structure du Projet

```
ReguAI/
├── scripts/
│   ├── app.py                              # Application Streamlit principale
│   │
│   ├── helpers/                            # Modules d'aide pour l'application
│   │   ├── dashboard_helper.py            # Fonctions pour le dashboard (KPIs, graphiques)
│   │   ├── document_analysis_helper.py    # Gestion des documents et extractions
│   │   ├── aws_services_helper.py        # Intégration AWS (S3, Comprehend, Bedrock)
│   │   └── impact_helper.py              # Fonctions d'affichage pour l'analyse d'impact
│   │
│   ├── processing/                         # Traitement de documents
│   │   └── process_regulatory_document.py # Processeur principal de documents réglementaires
│   │
│   ├── impact/                             # Analyse d'impact réglementaire
│   │   ├── impact_calculator.py           # Calculs d'impact (Tier 1, 2, 3)
│   │   ├── impact_orchestrator.py         # Orchestration de l'analyse d'impact
│   │   └── streamlit_impact_runner.py     # Runner pour Streamlit
│   │
│   ├── recommendations/                    # Génération de recommandations
│   │   ├── recommendation_generator.py   # Générateur de recommandations (Bedrock)
│   │   ├── signal_generator.py            # Génération de signaux de trading
│   │   └── generate_recommendations_per_directive.py
│   │
│   ├── rag/                                # Système RAG (Retrieval Augmented Generation)
│   │   ├── config.py                      # Configuration RAG
│   │   ├── data_loader.py                # Chargement des données
│   │   ├── embeddings.py                  # Embeddings Bedrock
│   │   ├── vector_store.py                # Stockage vectoriel FAISS
│   │   ├── rag_chain.py                  # Chaîne LangChain
│   │   └── rag_helper.py                 # Orchestrateur RAG
│   │
│   └── utils/                              # Scripts utilitaires
│       ├── clear_rag_cache.py            # Nettoyage du cache RAG
│       └── reset_document_analysis.py     # Réinitialisation des analyses
├── notebooks/
│   ├── intro/
│   │   ├── Introduction-Datathon.ipynb     # Introduction au projet
│   │   └── getting_started.ipynb           # Guide de démarrage
│   ├── extraction/
│   │   ├── extract_data_points_10k.ipynb     # Extraction depuis rapports 10-K
│   │   ├── extract_regulatory_files.ipynb   # Extraction depuis documents réglementaires
│   │   ├── extract_key_market_data.ipynb     # Extraction des données de marché
│   │   └── generate_company_universe.ipynb   # 🌍 Génération Company Universe (fusion Market Data + Data Points)
│   └── utils/
│       └── run_streamlit_app.ipynb          # Utilitaires pour Streamlit
├── data/
│   ├── raw/
│   │   ├── directives/                      # Documents réglementaires bruts (HTML/XML/PDF)
│   │   ├── fillings/                        # Rapports 10-K bruts (par ticker)
│   │   ├── 2025-08-15_composition_sp500.csv # Composition S&P 500
│   │   ├── 2025-09-26_stocks-performance.csv # Performance des actions
│   │   └── jeu_de_donnees.zip               # Archive de données
│   └── generated/
│       ├── company_universe/
│       │   └── company_universe.json        # 🌍 UNIVERSE: Consolidation complète (500 entreprises)
│       ├── extracted_data_points/           # Points de données extraits (500+ fichiers JSON)
│       ├── extracted_directives/            # Documents réglementaires extraits (7 fichiers JSON)
│       └── key_market_data/
│           └── all_market_data.json         # Données de marché consolidées
├── doc/
│   ├── GUIDE_COMPLET_PROJET_DATATHON.md     # Guide complet du projet
│   ├── ANALYSE_SOLUTION_VS_REQUIREMENTS.md  # Analyse solution vs requirements
│   ├── REGULATORY_CHUNKING_UPDATE.md        # Mise à jour sur le chunking réglementaire
│   ├── RESUME_SERVICES_AWS.md               # Résumé des services AWS
│   ├── SERVICES_AWS_ET_MODELES.md           # Services AWS et modèles
│   └── USAGE_CSV_MARKET_DATA.md             # Utilisation des données CSV
├── requirements.txt                          # Dépendances Python
└── README.md                                 # Ce fichier
```

## 🔧 Technologies Utilisées

### Interface et Visualisation

- **Streamlit** : Interface web interactive
- **Plotly** : Visualisations interactives et graphiques

### Traitement de Données

- **Pandas** : Manipulation et analyse de données
- **NumPy** : Calculs numériques

### IA et NLP

- **Amazon Bedrock** : IA générative (Claude) pour extraction structurée
- **LegalBERT** (nlpaueb/legal-bert-base-uncased) : Classification de documents juridiques
- **Transformers (Hugging Face)** : Modèles NLP
- **PyTorch** : Backend pour modèles de deep learning

### AWS Services

- **boto3** : SDK AWS
- **Amazon Textract** : Extraction de texte depuis PDF/images
- **Amazon S3** : Stockage des données

### Parsing et Extraction

- **sec-parser** : Parsing des rapports SEC (10-K)
- **instructor[bedrock]** : Extraction structurée avec Pydantic
- **BeautifulSoup4** : Parsing HTML/XML
- **lxml** : Parseur XML efficace

### APIs Externes

- **yfinance** : Données financières depuis Yahoo Finance
- **tavily-python** : Recherche web

### Validation

- **Pydantic** : Validation et structuration de données

## 📊 Données Disponibles

### Données Générées

- **🌍 Company Universe consolidé** : `data/generated/company_universe/company_universe.json`

  - **500 entreprises** avec données complètes fusionnées
  - **Market Data** : Métriques financières, secteurs, ratios (P/E, marges, etc.)
  - **Data Points 10-K** : Géographie, segments, supply chain, opérations
  - Structure unifiée pour analyse complète des entreprises
- **500+ fichiers JSON** de points de données extraits depuis les rapports 10-K (`data/generated/extracted_data_points/`)
- **7 documents réglementaires extraits** avec informations structurées (`data/generated/extracted_directives/`)
- **Données de marché consolidées** : `data/generated/key_market_data/all_market_data.json`
- **Composition S&P 500** avec performances enrichies via yfinance

### Documents Réglementaires Disponibles

- **Europe** :
  - Directive (UE) 2019/2161 du Parlement européen et du Conseil
  - Règlement (EU) 2024/1689 du Parlement européen et du Conseil
- **États-Unis** :
  - H.R.5376 - Inflation Reduction Act of 2022
  - PLAW-119publ21 (loi fédérale)
- **Asie** :
  - 中华人民共和国能源法 (Loi sur l'énergie - Chine)
  - 人工知能関連技術の研究開発及び活用の推進に関する法律 (Loi sur l'IA - Japon)

## 🚀 Guide de Démarrage Rapide

### Analyser un Document Réglementaire

1. **Lancer l'app** : `streamlit run scripts/app.py`
2. **Aller dans "📄 Analyse de Documents"**
3. **Uploader un fichier** (HTML, XML, PDF, TXT)
4. **Cliquer "🔍 Analyser avec Bedrock"**
5. **Attendre 1-3 minutes** pour l'extraction
6. **Voir les résultats** dans l'expander

### Utiliser le Chatbot RAG

1. **Aller dans "🤖 Chatbot Financier"**
2. **Poser une question** (ex: "Quel est l'impact de l'EU AI Act sur Apple ?")
3. **Le système** recherche dans la base de connaissances (extractions réglementaires + 10-K + Company Universe)
4. **Réponse contextuelle** avec sources citées

### Analyser l'Impact Réglementaire

1. **Aller dans "📊 Analyse d'Impact"**
2. **Sélectionner une réglementation** dans la liste
3. **Voir les entreprises affectées** avec scores d'impact
4. **Consulter les recommandations** de trading

### Fonctionnalités Avancées

- **Filtrage par statut** : 
  - **"Tous"** : Affiche tous les documents
  - **"Analysés"** : Affiche uniquement les documents analysés (avec statut `analyzed` ou `analyzed_3tier`)
  - **"Non analysés"** : Affiche uniquement les documents non analysés
- **Statuts des documents** :
  - **✅ Analysé (3-Tier)** : Document analysé avec extraction complète + analyse d'impact
  - **✅ Analysé** : Document analysé avec extraction complète (pas encore d'analyse d'impact)
  - **⏳ Non analysé** : Document brut non encore analysé
- **Gestion intelligente des documents** :
  - Les documents analysés affichent uniquement la version analysée (pas le fichier brut)
  - Les fichiers bruts n'apparaissent que s'ils n'ont pas encore été analysés
  - Pas de doublons : un document analysé = une seule entrée dans la liste
- **Bouton Actualiser** : Force le rafraîchissement de la liste des documents
- **Supprimer extractions** : Bouton 🗑️ pour supprimer un résultat d'extraction et ré-analyser
- **Auto-rename** : Les documents sont renommés automatiquement selon le contenu extrait

## 🎨 Identité Visuelle

Le logo **ReguAI** représente l'intelligence artificielle appliquée à la réglementation :
- **Cerveau stylisé** : Hémisphère gauche avec plis naturels, hémisphère droit avec pattern de circuit board/réseau neuronal
- **Symbole** : Fusion entre intelligence humaine et technologie IA
- **Couleurs** : Vert émeraude (#10b981) pour l'innovation et la confiance

Le logo est disponible dans `doc/Logo.png` et est affiché dans le menu de l'application Streamlit.

## 📊 État du Projet

**Statut** : ✅ Application complète et fonctionnelle

**Fonctionnalités implémentées** :
- ✅ Dashboard avec visualisations interactives
- ✅ Extraction automatique de documents réglementaires (Bedrock)
- ✅ Chatbot RAG avec base de connaissances complète
- ✅ Analyse d'impact réglementaire sur portefeuille S&P 500
- ✅ Génération de recommandations de trading
- ✅ Interface moderne et intuitive

## 🎓 Ressources

- **Introduction** : `notebooks/intro/Introduction-Datathon.ipynb`
- **Structure des scripts** : `scripts/README.md`
- Documentation Streamlit : https://docs.streamlit.io
- Amazon Bedrock : https://docs.aws.amazon.com/bedrock

## 📝 Notes de Développement

### Architecture

Le projet suit une architecture modulaire :

- **Notebooks** : Pour exploration et extraction initiale
- **Scripts** : Pour traitement automatisé et application
- **Data Pipeline** : Raw → Generated (extraction + enrichissement)

### Scripts Disponibles

1. **`generate_key_market_data.py`** :

   - Fusionne composition S&P 500 + performance + yfinance
   - Filtre par entreprises avec 10-K disponibles
   - Génère `all_market_data.json`
2. **`generate_company_universe.ipynb`** :

   - Fusionne Key Market Data + Data Points 10-K
   - Crée un fichier consolidé avec toutes les données entreprises
   - Génère `company_universe.json` (500 entreprises complètes)
   - Structure : Market Data (financier) + Data Points (géographie, segments, supply chain)
3. **`process_regulatory_document.py`** :

   - Traitement complet de documents réglementaires
   - Utilise Textract (PDF), BeautifulSoup (HTML/XML)
   - Classification avec LegalBERT
   - Extraction structurée avec Bedrock
   - Compatible Lambda AWS
4. **`enrich_with_yfinance.py`** :

   - Enrichissement des données avec yfinance
   - Métriques financières en temps réel

### À Améliorer / À Implémenter

1. **Analyse d'Impact** :

   - ⏳ Croiser réglementations avec données 10-K extraites
   - ⏳ Calculer scores de risque réglementaire
   - ⏳ Matcher entités mentionnées dans réglementations avec entreprises S&P 500
2. **Chatbot** :

   - ⏳ Intégrer Bedrock pour réponses conversationnelles
   - ⏳ Base de connaissances avec RAG (Retrieval Augmented Generation)
   - ⏳ Context window avec extractions réglementaires et 10-K
3. **Cache et Optimisation** :

   - ⏳ Implémenter cache S3 pour les extractions Bedrock
   - ⏳ Réduire les coûts avec caching intelligent
   - ⏳ Batch processing pour plusieurs documents
4. **Intégration S3** :

   - Scripts `s3_push.sh`, `s3_pull.sh`, `s3_organize.sh` disponibles
   - À intégrer dans le pipeline complet

## 📧 Support

Pour toute question, consultez :
- Le README principal (ce fichier) pour les instructions de base
- Les notebooks dans `notebooks/intro/` pour les exemples
- `scripts/README.md` pour la structure du code

## 📚 Ressources de Présentation

### Documents de Présentation Disponibles

Les documents suivants sont disponibles pour découvrir et comprendre le projet ReguAI :

- **📹 Vidéo de démonstration** : `doc/TEAM-35_video_datathon_2025.mov`
  - Présentation complète du projet et des fonctionnalités
  - Démonstration interactive de l'application
  
- **📊 One-pager** : `doc/TEAM-35_onepager.pdf`
  - Résumé exécutif du projet
  - Vue d'ensemble rapide des fonctionnalités et de la valeur ajoutée
  
- **📄 Document technique** : Disponible séparément (non inclus dans le repository)
  - Documentation technique complète
  - Architecture détaillée et spécifications techniques

### Exemple d'Utilisation ReguAI

**Scénario type** : Un gestionnaire de portefeuille veut analyser l'impact de l'EU AI Act sur son portefeuille S&P 500.

1. **Upload du document** : Le gestionnaire upload le document réglementaire via l'interface
2. **Extraction automatique** : ReguAI extrait les informations clés (secteurs affectés, pays, exigences)
3. **Analyse d'impact** : Le système croise les données avec les rapports 10-K des entreprises
4. **Recommandations** : ReguAI génère des signaux de trading (BUY/SELL/HOLD) avec scores de confiance
5. **Visualisation** : Dashboard interactif avec graphiques et métriques

**Résultat** : Le gestionnaire obtient en quelques minutes une analyse complète de l'impact réglementaire avec recommandations actionnables.

---

**Bonne chance pour le Datathon ! 🚀**

**ReguAI** - *Transforming Regulatory Complexity into Strategic Portfolio Decisions*
