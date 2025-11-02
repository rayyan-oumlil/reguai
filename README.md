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

### 1. Installer les dépendances

```bash
pip install -r requirements.txt
```

### 2. Lancer l'application Streamlit

```bash
python -m streamlit run scripts/app.py
```

L'application s'ouvrira automatiquement dans votre navigateur à l'adresse `http://localhost:8501`

### 3. Configuration AWS (Optionnel)

Pour utiliser les fonctionnalités Bedrock, configurez vos credentials AWS :

```bash
aws configure
```

Ou via variables d'environnement :
```bash
export AWS_ACCESS_KEY_ID=votre_clé
export AWS_SECRET_ACCESS_KEY=votre_secret
```

## 📁 Structure du Projet

```
Datathon2025/
├── scripts/
│   ├── app.py                      # Application Streamlit principale
│   ├── bedrock_utils.py            # Utilitaires pour Amazon Bedrock
│   └── enrich_with_yfinance.py     # Enrichissement des données avec yfinance
├── notebooks/
│   ├── intro/
│   │   ├── Introduction-Datathon.ipynb  # Introduction au projet
│   │   └── getting_started.ipynb        # Guide de démarrage
│   ├── extraction/
│   │   ├── extract_data_points_10k.ipynb      # Extraction depuis rapports 10-K
│   │   ├── extract_regulatory_files.ipynb      # Extraction depuis documents réglementaires
│   │   ├── enrich_with_yfinance.ipynb          # Enrichissement des données
│   │   ├── generate_company_universe.ipynb      # Génération de l'univers d'entreprises
│   │   └── generate_key_market_data.ipynb      # Génération des données de marché clés
│   └── utils/
│       └── run_streamlit_app.ipynb              # Utilitaires pour Streamlit
├── data/
│   ├── raw/
│   │   ├── directives/                      # Documents réglementaires bruts
│   │   ├── fillings/                         # Rapports 10-K bruts
│   │   ├── 2025-08-15_composition_sp500.csv  # Composition S&P 500
│   │   └── 2025-09-26_stocks-performance.csv  # Performance des actions
│   └── generated/
│       ├── extracted_data_points/            # Points de données extraits (439 fichiers JSON)
│       └── key_market_data/                  # Données de marché générées
├── doc/
│   ├── GUIDE_COMPLET_PROJET_DATATHON.md      # Guide complet du projet
│   ├── ANALYSE_SOLUTION_VS_REQUIREMENTS.md   # Analyse solution vs requirements
│   ├── RESUME_SERVICES_AWS.md                # Résumé des services AWS
│   ├── SERVICES_AWS_ET_MODELES.md            # Services AWS et modèles
│   └── USAGE_CSV_MARKET_DATA.md              # Utilisation des données CSV
├── directives/                               # Documents réglementaires (ancien emplacement)
├── fillings/                                 # Rapports 10-K (ancien emplacement)
├── dev/                                      # Fichiers de développement (logs AWS Glue)
├── requirements.txt                          # Dépendances Python
└── README.md                                 # Ce fichier
```

## 🔧 Technologies Utilisées

- **Streamlit** : Interface web
- **Plotly** : Visualisations interactives
- **Pandas** : Manipulation de données
- **Amazon Bedrock** : IA générative pour extraction structurée
- **boto3** : SDK AWS
- **sec-parser** : Parsing des rapports SEC (10-K)
- **instructor[bedrock]** : Extraction structurée avec Pydantic
- **BeautifulSoup4** : Parsing HTML/XML
- **yfinance** : Données financières depuis Yahoo Finance

## 📊 Données Disponibles

### Données Générées

- **439 fichiers JSON** de points de données extraits depuis les rapports 10-K
- **Données de marché** enrichies avec yfinance
- **Composition S&P 500** avec performances

### Documents Réglementaires

- Directives européennes (UE)
- Lois américaines (Inflation Reduction Act, etc.)
- Réglementations asiatiques (Chine, Japon)

## 🎓 Ressources et Documentation

- **Introduction** : `notebooks/intro/Introduction-Datathon.ipynb`
- **Guide complet** : `doc/GUIDE_COMPLET_PROJET_DATATHON.md`
- **Services AWS** : `doc/RESUME_SERVICES_AWS.md`
- Documentation Streamlit : https://docs.streamlit.io
- Amazon Bedrock : https://docs.aws.amazon.com/bedrock

## 📝 Notes de Développement

### Fonctionnalités Implémentées

1. **Extraction avec Bedrock** :
   - Extraction structurée depuis rapports 10-K
   - Extraction depuis documents réglementaires
   - Validation avec Pydantic

2. **Enrichissement des Données** :
   - Intégration yfinance pour données de marché
   - Génération de l'univers d'entreprises

3. **Application Streamlit** :
   - Dashboard interactif
   - Visualisations avec Plotly

### À Améliorer

1. **Analyse d'Impact** :
   - Croiser réglementations avec données 10-K
   - Calculer scores de risque

2. **Chatbot** :
   - Intégrer Bedrock pour réponses conversationnelles
   - Base de connaissances avec RAG

3. **Cache** :
   - Implémenter cache S3 pour les extractions
   - Réduire les coûts Bedrock

## 📧 Support

Pour toute question, consultez les fichiers de documentation dans le dossier `doc/` :
- `GUIDE_COMPLET_PROJET_DATATHON.md` : Guide complet du projet
- `ANALYSE_SOLUTION_VS_REQUIREMENTS.md` : Analyse solution vs requirements
- `RESUME_SERVICES_AWS.md` : Résumé des services AWS

---

**Bonne chance pour le Datathon ! 🚀**
