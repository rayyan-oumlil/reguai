# 🚀 ReguAI - Regulatory Intelligence Assistant

**Datathon PolyFinances 2025**

## 📋 Description

ReguAI est une application web interactive permettant d'analyser l'impact des réglementations sur le portefeuille S&P 500 en utilisant l'IA générative (Amazon Bedrock).

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

Configurez vos credentials AWS pour utiliser Bedrock, Textract et S3 :

```bash
aws configure
```

Ou via variables d'environnement :
```bash
export AWS_ACCESS_KEY_ID=votre_clé
export AWS_SECRET_ACCESS_KEY=votre_secret
export AWS_DEFAULT_REGION=us-east-1  # ou votre région
```

**Important** : Assurez-vous d'avoir accès à :
- Amazon Bedrock (Claude models)
- Amazon Textract
- Amazon S3 (optionnel)

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
python scripts/process_regulatory_document.py --file_path data/raw/directives/document.html --output_dir data/generated/extracted_directives/
```

### 4. Lancer l'application Streamlit

```bash
python -m streamlit run scripts/app.py
```

L'application s'ouvrira automatiquement dans votre navigateur à l'adresse `http://localhost:8501`

## 📁 Structure du Projet

```
Datathon2025/
├── scripts/
│   ├── app.py                              # Application Streamlit principale
│   ├── bedrock_utils.py                    # Utilitaires pour Amazon Bedrock
│   ├── enrich_with_yfinance.py             # Enrichissement des données avec yfinance
│   ├── process_regulatory_document.py      # Traitement de documents réglementaires (Bedrock + LegalBERT)
│   ├── generate_key_market_data.py         # Génération des données de marché consolidées
│   ├── s3_push.sh / s3_pull.sh / s3_organize.sh  # Scripts de gestion S3
│   └── README_REGULATORY_PROCESSOR.md      # Documentation du processeur réglementaire
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
├── dev/
│   └── glue/                                # Logs AWS Glue (développement)
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

## 🎓 Ressources et Documentation

- **Introduction** : `notebooks/intro/Introduction-Datathon.ipynb`
- **Guide complet** : `doc/GUIDE_COMPLET_PROJET_DATATHON.md`
- **Services AWS** : `doc/RESUME_SERVICES_AWS.md`
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

Pour toute question, consultez les fichiers de documentation dans le dossier `doc/` :
- `GUIDE_COMPLET_PROJET_DATATHON.md` : Guide complet du projet
- `ANALYSE_SOLUTION_VS_REQUIREMENTS.md` : Analyse solution vs requirements
- `RESUME_SERVICES_AWS.md` : Résumé des services AWS

---

**Bonne chance pour le Datathon ! 🚀**
