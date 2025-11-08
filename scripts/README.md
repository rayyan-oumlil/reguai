# 📁 Structure des Scripts - ReguAI

## 🗂️ Organisation par Fonctionnalité

Le dossier `scripts/` est organisé par fonctionnalité pour une meilleure maintenabilité :

```
scripts/
├── app.py                          # Application Streamlit principale
│
├── helpers/                        # Modules d'aide pour l'application
│   ├── dashboard_helper.py        # Fonctions pour le dashboard (KPIs, graphiques)
│   ├── document_analysis_helper.py # Gestion des documents et extractions
│   ├── aws_services_helper.py     # Intégration AWS (S3, Comprehend, Bedrock)
│   └── impact_helper.py           # Fonctions d'affichage pour l'analyse d'impact
│
├── processing/                     # Traitement de documents
│   └── process_regulatory_document.py  # Processeur principal de documents réglementaires
│
├── impact/                         # Analyse d'impact réglementaire
│   ├── impact_calculator.py      # Calculs d'impact (Tier 1, 2, 3)
│   ├── impact_orchestrator.py     # Orchestration de l'analyse d'impact
│   └── streamlit_impact_runner.py # Runner pour Streamlit
│
├── recommendations/                # Génération de recommandations
│   ├── recommendation_generator.py # Générateur de recommandations (Bedrock)
│   ├── signal_generator.py        # Génération de signaux de trading
│   └── generate_recommendations_per_directive.py  # Génération par directive
│
├── rag/                           # Système RAG (Retrieval Augmented Generation)
│   ├── config.py                  # Configuration RAG
│   ├── data_loader.py            # Chargement des données
│   ├── embeddings.py              # Embeddings Bedrock
│   ├── vector_store.py            # Stockage vectoriel FAISS
│   ├── rag_chain.py              # Chaîne LangChain
│   └── rag_helper.py             # Orchestrateur RAG
│
└── utils/                         # Scripts utilitaires
    ├── clear_rag_cache.py         # Nettoyage du cache RAG
    ├── reset_document_analysis.py # Réinitialisation des analyses
    └── test_aws_services_standalone.py  # Tests AWS
```

## 📋 Description des Modules

### 🎨 **helpers/** - Modules d'aide
Fonctions réutilisables pour l'interface Streamlit :
- **dashboard_helper.py** : KPIs, graphiques, visualisations du portefeuille
- **document_analysis_helper.py** : Gestion des uploads, extractions, cache
- **aws_services_helper.py** : Intégration AWS (S3 cache, Comprehend, Bedrock)
- **impact_helper.py** : Affichage des résultats d'impact

### ⚙️ **processing/** - Traitement
- **process_regulatory_document.py** : Processeur principal qui extrait les informations des documents réglementaires (HTML/XML/PDF) avec Bedrock, Textract, LegalBERT

### 📊 **impact/** - Analyse d'Impact
Calcul de l'impact réglementaire sur les entreprises S&P 500 :
- **impact_calculator.py** : Calculs Tier 1 (exposure), Tier 2 (valuation), Tier 3 (final risk)
- **impact_orchestrator.py** : Orchestration complète de l'analyse
- **streamlit_impact_runner.py** : Interface Streamlit pour l'analyse d'impact

### 💡 **recommendations/** - Recommandations
Génération de recommandations de trading basées sur l'analyse d'impact :
- **recommendation_generator.py** : Génération avec Claude Sonnet via Bedrock
- **signal_generator.py** : Génération de signaux de trading
- **generate_recommendations_per_directive.py** : Génération par directive

### 🤖 **rag/** - Système RAG
Retrieval Augmented Generation pour le chatbot :
- **config.py** : Configuration (modèles, chemins, paramètres)
- **data_loader.py** : Chargement des données (directives, 10-K, Company Universe)
- **embeddings.py** : Génération d'embeddings avec Cohere Embed v4
- **vector_store.py** : Stockage vectoriel FAISS pour recherche sémantique
- **rag_chain.py** : Chaîne LangChain avec Claude Sonnet
- **rag_helper.py** : Orchestrateur principal du système RAG

### 🛠️ **utils/** - Utilitaires
Scripts de maintenance et tests :
- **clear_rag_cache.py** : Nettoyage du cache RAG
- **reset_document_analysis.py** : Réinitialisation des analyses de documents
- **test_aws_services_standalone.py** : Tests des services AWS

## 🔄 Imports

Tous les imports ont été mis à jour pour utiliser la nouvelle structure :

```python
# Avant
from scripts.dashboard_helper import load_company_universe

# Après
from scripts.helpers.dashboard_helper import load_company_universe
```

## 📝 Notes

- **app.py** reste à la racine de `scripts/` (point d'entrée principal)
- Le dossier **rag/** conserve sa structure existante (déjà bien organisé)
- Chaque nouveau module doit être placé dans le dossier correspondant à sa fonctionnalité
- Les `__init__.py` permettent l'importation des modules comme packages Python

