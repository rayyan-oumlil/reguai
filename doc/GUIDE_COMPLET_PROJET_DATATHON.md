# 🚀 Guide Complet - ReguAI - Datathon PolyFinances 2025

**ReguAI** - Regulatory Intelligence Assistant  
*Transforming Regulatory Complexity into Strategic Portfolio Decisions*

---

## 📋 Table des Matières

1. [Vue d'Ensemble du Projet](#vue-densemble-du-projet)
2. [Structure Complète du Projet](#structure-complète-du-projet)
3. [Architecture et Fonctionnalités](#architecture-et-fonctionnalités)
4. [Services AWS et Optimisation](#services-aws-et-optimisation)
5. [Stratégie Données : Datasets vs APIs](#stratégie-données-datasets-vs-apis)
6. [Flux de Fonctionnement Complet](#flux-de-fonctionnement-complet)
7. [Résultat Final Attendu](#résultat-final-attendu)
8. [Exemples de Code Réutilisables](#exemples-de-code-réutilisables)

---

## 🎯 Vue d'Ensemble du Projet

### Objectif Principal

**Transformer la complexité réglementaire en opportunité d'aide à la décision** pour la gestion de portefeuilles d'actions (S&P 500).

### Concept de la Solution

ReguAI fonctionne comme un **analyste financier IA** qui:

1. **Lit automatiquement** n'importe quel document réglementaire (loi, directive, règlement)
2. **Extrait les informations clés**:
   - Quelles entreprises/secteurs sont concernés ?
   - Quels pays/zones géographiques ?
   - Quelles mesures sont imposées ? (taxes, restrictions, subventions, etc.)
   - Dates d'application
   - Impacts financiers potentiels
3. **Croise avec les données entreprises**:
   - Rapports 10-K pour voir où elles opèrent
   - Chaînes d'approvisionnement
   - Modèles économiques
4. **Calcule l'impact** sur le portefeuille S&P 500:
   - Score de risque par entreprise
   - Impact financier estimé (% de perte, baisse de marge, etc.)
   - Concentrations de risque (par secteur, pays)
5. **Génère des recommandations**:
   - Quelles actions réduire/augmenter ?
   - Rotation sectorielle suggérée
   - Réallocation géographique

### Flux de Travail Simplifié

**Flux** : Nouveau document réglementaire → Extraction IA (Bedrock + NLP) → Entités extraites → Croisement avec données → Calcul impact → Recommandations → Visualisation

---

## 📂 Structure Complète du Projet

### ✅ Données Déjà Disponibles

**⚠️ IMPORTANT** : Les données sont déjà téléchargées ! Le notebook `Introduction-Datathon.ipynb` a déjà extrait 1010 fichiers. Vous n'avez **PAS besoin** de ré-exécuter les notebooks de téléchargement.

### 📊 Fichiers CSV - Données du S&P 500

#### `2025-08-15_composition_sp500.csv`
**Contenu**: Composition du S&P 500 au 15 août 2025
- **Colonnes**: 
  - `#` : Rang
  - `Company` : Nom de l'entreprise
  - `Symbol` : Ticker (AAPL, MSFT, etc.)
  - `Weight` : Poids dans l'indice S&P 500 (ex: 0.0597 = 5.97%)
    - ⚠️ **Format européen** : Utilise la virgule comme séparateur décimal (ex: "0,0765")
    - À convertir en float : `.str.replace(',', '.').astype(float)`
  - `Price` : Prix de l'action à cette date
- **Nombre de lignes**: ~500 entreprises
- **Utilisation clé**: Composition officielle et poids dans l'indice (source de vérité)

#### `2025-09-26_stocks-performance.csv`
**Contenu**: Métriques de performance des actions au 26 septembre 2025
- **Colonnes**:
  - `Symbol` : Ticker
  - `Company Name` : Nom complet
  - `Market Cap` : Capitalisation boursière
  - `Revenue` : Chiffre d'affaires
  - `Op. Income` : Revenu opérationnel
  - `Net Income` : Revenu net
  - `EPS` : Earnings Per Share (Bénéfice par action)
  - `FCF` : Free Cash Flow (Flux de trésorerie libre)
- **Nombre de lignes**: ~500 entreprises
- **Utilisation**: Analyser la santé financière de chaque entreprise

**💡 Note sur les dates différentes** : 
- Composition : 15 août 2025
- Performance : 26 septembre 2025
- **C'est normal !** Les deux snapshots permettent d'analyser l'évolution entre deux dates.

---

### 📜 Dossier `directives/` - Documents Réglementaires

**6 documents législatifs/réglementaires** de différentes juridictions:

#### 🇪🇺 Union Européenne

1. **`DIRECTIVE (UE) 20192161 DU PARLEMENT EUROPÉEN ET DU CONSEIL.html`**
   - **Date**: 27 novembre 2019
   - **Sujet**: Protection des consommateurs et modernisation des règles UE
   - **Impact potentiel**: Entreprises B2C, e-commerce, services consommateurs

2. **`REGULATION (EU) 20241689 OF THE EUROPEAN PARLIAMENT AND OF THE COUNCIL.html`**
   - **Date**: 12 juillet 2024
   - **Sujet**: **EU AI Act** - Réglementation de l'intelligence artificielle
   - **Impact potentiel**: Entreprises tech utilisant l'IA (Meta, Google, Microsoft, etc.)

#### 🇺🇸 États-Unis

3. **`H.R.5376 - Inflation Reduction Act of 2022.xml`**
   - **Date**: 16 août 2022
   - **Sujet**: Réduction de l'inflation, énergie verte, médicaments
   - **Impact potentiel**: 
     - Secteur énergie (solaire, éolien, batteries)
     - Industrie pharmaceutique
     - Automobile électrique

#### 🇨🇳 Chine

4. **`中华人民共和国能源法__中国政府网.html`**
   - **Nom**: Loi sur l'énergie de la République populaire de Chine
   - **Date**: 9 novembre 2024
   - **Sujet**: Sécurité énergétique, neutralité carbone, transformation verte
   - **Impact potentiel**: 
     - Entreprises énergétiques
     - Fabricants de batteries (CATL, BYD)
     - Supply chain chinoise (Apple, Tesla, etc.)

#### 🇯🇵 Japon

5. **`人工知能関連技術の研究開発及び活用の推進に関する法律.html`**
   - **Nom**: Loi sur la promotion de l'IA au Japon
   - **Sujet**: Recherche, développement et utilisation de l'IA
   - **Impact potentiel**: Entreprises tech, partenaires japonais

#### 📋 Documentation

6. **`README.md`** : Explications détaillées de chaque document

---

### 📄 Dossier `fillings/` - Rapports 10-K des Entreprises

**Structure**: Un dossier par ticker S&P 500 (ex: `AAPL/`, `MSFT/`, `NVDA/`)

**Contenu**: Rapports annuels 10-K de 2024 déposés à la SEC

**Exemples**:
- `fillings/AAPL/2024-11-01-10k-AAPL.html`
- `fillings/MSFT/2025-07-30-10k-MSFT.html`
- `fillings/NVDA/...` (et ~500 autres entreprises)

**Ce que contiennent les 10-K**:
- Activités détaillées de l'entreprise
- Risques réglementaires
- Situation financière
- **Dépendances géographiques** (où l'entreprise opère)
- **Chaînes d'approvisionnement** (fournisseurs, partenaires)
- Expositions réglementaires par pays

**Utilisation clé**: 
- Croiser avec les réglementations pour identifier les entreprises à risque
- Exemple: Si une réglementation UE impacte les semi-conducteurs, identifier quelles entreprises du S&P 500 sont exposées en regardant leurs 10-K

---

### 📚 Dossier `doc/` - Documentation du Datathon

**10 fichiers PDF**:
- `Datathon-Case-Officiel-FR.pdf` : Énoncé complet du défi
- `Fiche du participant.pdf` : Informations pour participants
- `Horaire.pdf` : Horaires du datathon
- `Outils.pdf` : Documentation des outils
- `TEAM-01_doc_tech.pdf`, `TEAM-01_onepager.pdf` : Exemples équipes précédentes
- `TEAM-02_doc_tech.pdf`, `TEAM-02_onepager.pdf`
- `TEAM-03_doc_tech.pdf`, `TEAM-03_onepager.pdf`

---

### 📓 Notebooks Jupyter

#### `Introduction-Datathon.ipynb` - Guide du Datathon avec Exemples

**Contenu détaillé**:

1. **Introduction au défi** (Cellules markdown)
   - Contexte: réglementation complexe et sanctions économiques
   - Objectif: transformer complexité réglementaire en aide à la décision
   - Livrables attendus

2. **Téléchargement des données** (Cellule 8)
   - Télécharge et extrait le jeu_de_donnees.zip (1010 fichiers)
   - **⚠️ Note**: Les données sont déjà téléchargées, pas besoin de ré-exécuter

3. **Prévisualisation des données** (Cellules 10-11)
   - Charge et affiche les premières lignes des CSV

4. **Exemples Amazon Bedrock** (Cellules 13, 15, 17)
   - Cellule 13: Exemple simple avec Claude Sonnet
   - Cellule 15: Liste tous les modèles Bedrock disponibles
   - Cellule 17: Liste des profils d'inférence globaux (type `global.*`)

5. **Extraction de données structurées** (Cellules 19-20)
   - Cellule 19: Installation de `instructor[bedrock]`
   - Cellule 20: Extraction de données 10-K avec Pydantic BaseModel et Claude Haiku
   - Montre comment extraire: nom entreprise, ticker, numéro SEC, dates, adresse, etc.

6. **Agents Strands** (Cellules 23-24)
   - Cellule 23: Installation `strands-agents strands-agents-tools`
   - Cellule 24: Exemple d'agent conversationnel
   - Permet d'interagir avec les données de manière conversationnelle

#### `getting_started.ipynb` - Guide Technique SageMaker

**Contenu détaillé**:

1. **Configuration du projet SageMaker** (Cellules 1-4)
   - Accès à: project.iam_role, project.s3.root, project.connection()

2. **Python local** (Cellule 6)
   - Exemple basique avec pandas
   - Pré-configuré pour ML et analytics

3. **Apache Spark** (Cellules 7-19)
   - Cellule 10: Configuration Spark (workers, type)
   - Cellule 12: Transfert de données vers Spark
   - Cellule 14: Exemple PySpark (écriture de table)
   - Cellule 18: Exemple SparkSQL
   - Support PySpark, ScalaSpark, SparkSQL

4. **SQL: Athena, Redshift** (Cellules 20-27)
   - Cellule 21: Requête Athena
   - Cellule 23: Requête Redshift
   - Cellules 25-27: Connexion Redshift depuis Spark

5. **Visualisation** (Cellules 28-31)
   - Affichage automatique des DataFrames
   - Magic `%display` pour forcer l'affichage
   - Support de `pygwalker`, `dataprep`, `ydata`

6. **Ajout de bibliothèques** (Cellule 32)
   - Via interface JupyterLab (icône bibliothèque)
   - Sources: PyPi, Conda, Maven, S3, local

7. **Amazon Q** (Cellule 33)
   - Code completion (barre de statut)
   - Chat assistant (icône gauche)
   - Support Python, PySpark, SQL

**⚠️ Points importants**:
- Les cell magics (`%%pyspark`, `%%sql`, `%%local`) ne fonctionnent qu'en JupyterLab
- L'environnement est déjà configuré avec Python, Spark, SQL
- Accès direct à S3 via `project.s3.root`

---

## 🏗️ Architecture et Fonctionnalités

### Architecture Globale

```
┌─────────────────────────────────────────────────────────────┐
│                    UTILISATEUR FINAL                         │
│              (Analyste Financier / Gestionnaire)             │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              STREAMLIT INTERFACE (Frontend)                  │
│  ┌──────────────┬───────────────┬───────────────────┐     │
│  │  Dashboard    │  Financial    │   Document        │     │
│  │  (KPIs &      │  Chatbot      │   Analysis       │     │
│  │   Visuals)    │  (Q&A)        │   (Upload)       │     │
│  └──────────────┴───────────────┴───────────────────┘     │
└────────────────────┬─────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              BACKEND API (Python / FastAPI)                  │
│           Orchestration et Logique Métier                     │
└────────────────────┬─────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┬──────────────┐
        ▼            ▼            ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
│ Bedrock  │  │   S3     │  │ Lambda   │  │Comprehend│
│   (IA)   │  │(Storage)  │ │(Workflow)│ │  (NLP)   │
└──────────┘  └──────────┘  └──────────┘  └──────────┘
     │            │              │              │
     └────────────┴──────────────┴──────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              SOURCES DE DONNÉES                              │
│  • Rapports 10-K (S3)                                        │
│  • Composition S&P 500 (CSV)                                 │
│  • Yahoo Finance (API)                                       │
│  • Tavily API (Recherche Web)                               │
└─────────────────────────────────────────────────────────────┘
```

---

### 📊 Architecture de Flux de Données (Proposition Équipe)

Cette architecture montre comment les différentes sources de données sont traitées et intégrées dans une base de données centrale.

```
┌─────────────────────────────────────────────────────────────────────┐
│                     SOURCES DE DONNÉES                               │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────┐│
│  │ Regulatory        │  │ Stock data        │  │ 10K filings    ││
│  │ documents         │  │ (composition /    │  │ (x 500)        ││
│  │                   │  │  performance)     │  │                 ││
│  └────────┬──────────┘  └────────┬──────────┘  └────────┬───────┘│
│           │                      │                       │         │
└───────────┼──────────────────────┼───────────────────────┼─────────┘
            │                      │                       │
            ▼                      ▼                       ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ Legal Data        │  │ Key Market Data  │  │ Data Points      │
│ Extraction       │  │                  │  │                  │
│                  │  │                  │  │                  │
│ Outils:          │  │ - Market Cap     │  │ Outils:          │
│ - Textract +     │  │ - Stock price    │  │ - Sec-parser +   │
│   Bedrock        │  │ - Weight         │  │   Bedrock +      │
│ - Legal Bert     │  │ - EPS            │  │   Finbert        │
│ - Claude 4       │  │ - P/E            │  │ - Claude 4       │
│                  │  │ - ...            │  │                  │
│ Extrait:         │  │                  │  │ Extrait:         │
│ - Issuing        │  │                  │  │ - name, type     │
│   jurisdiction   │  │                  │  │ - geography       │
│ - Regulated      │  │                  │  │ - company NA/EU  │
│   entities       │  │                  │  │ - Segments       │
│ - Companies      │  │                  │  │ - supply chain   │
│ - Sectors        │  │                  │  │ - ...            │
│ - Countries      │  │                  │  │                  │
│ - Key dates      │  │                  │  │                  │
│ - ...            │  │                  │  │                  │
└────────┬─────────┘  └────────┬──────────┘  └────────┬─────────┘
         │                     │                       │
         │ "writes"           │ "enriches"            │ "writes"
         │                     │                       │
         └─────────────────────┴───────────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │  Company Universe    │
                    │                      │
                    │  1. DB-table        │
                    │  2. Regulation table │
                    └──────────────────────┘
```

#### 🔍 Explication Détaillée du Flux

**1. Sources de Données (3 Sources Principales)**
- **Regulatory Documents** : Documents réglementaires (UE, US, Chine, Japon, etc.)
- **Stock Data** : Données de marché (composition S&P 500, performance)
- **10K Filings** : ~500 rapports annuels des entreprises

**2. Extraction et Traitement**

##### A. Legal Data Extraction (Depuis Regulatory Documents)
**Outils utilisés** :
- **Amazon Textract** : Extraction de texte depuis PDF/Images
- **Amazon Bedrock** : Analyse et extraction structurée (Claude 4)
- **Legal BERT** : Modèle spécialisé pour documents juridiques

**Données extraites** :
- Issuing jurisdiction (juridiction émettrice)
- Regulated entities (entités réglementées)
- Companies (entreprises mentionnées)
- Sectors (secteurs concernés)
- Countries (pays concernés)
- Key dates (dates importantes)

**Stockage** : Écrit dans la base de données → `regulation table`

---

##### B. Key Market Data (Depuis Stock Data CSV)
**Source** : 
- `2025-08-15_composition_sp500.csv`
- `2025-09-26_stocks-performance.csv`

**Données extraites** :
- Market Cap (Capitalisation boursière)
- Stock price (Prix de l'action)
- Weight (Poids dans l'indice S&P 500)
- EPS (Earnings Per Share)
- P/E (Price-to-Earnings ratio)
- Autres métriques financières

**Stockage** : Enrichit la base de données → `DB-table`

---

##### C. Data Points (Depuis 10K Filings)
**Outils utilisés** :
- **Sec-parser** : Parsing spécialisé des rapports SEC
- **Amazon Bedrock** : Extraction structurée (Claude 4)
- **FinBERT** : Modèle spécialisé pour données financières

**Données extraites** :
- Name, type (Nom, type d'entreprise)
- Geography (Géographie des opérations)
- Company NA/EU (Présence Amérique du Nord/UE)
- Segments (Segments d'affaires)
- Supply chain (Chaînes d'approvisionnement)
- Autres informations clés

**Stockage** : Écrit dans la base de données → `DB-table`

---

**3. Company Universe (Base de Données Centrale)**

**Structure** :
- **DB-table** : Table principale contenant toutes les informations sur les entreprises
  - Données de marché (depuis Stock Data)
  - Données 10-K (depuis Data Points)
  - Métadonnées et enrichissements

- **Regulation table** : Table dédiée aux réglementations
  - Informations extraites depuis Regulatory Documents
  - Liens avec les entreprises concernées
  - Dates et mesures

**Relations** :
- Les entreprises dans `DB-table` peuvent être liées aux réglementations dans `regulation table`
- Jointures possibles pour analyser l'impact réglementaire

**Utilisation** :
- Requêtes SQL/NoSQL pour analyser l'impact
- Base de données pour le chatbot (RAG)
- Source pour les visualisations et recommandations

---

#### 💡 Avantages de cette Architecture

1. **Séparation des Préoccupations**
   - Chaque type de données est traité avec les outils optimaux
   - Extraction séparée facilite la maintenance

2. **Scalabilité**
   - Chaque pipeline peut être traité en parallèle
   - Facile d'ajouter de nouvelles sources de données

3. **Réutilisabilité**
   - Les données extraites sont stockées une fois
   - Réutilisation pour différentes analyses

4. **Traçabilité**
   - On sait exactement d'où vient chaque donnée
   - Facilité de debug et de mise à jour

5. **Performance**
   - Base de données centralisée pour requêtes rapides
   - Indexation optimale pour recherches

---

#### 🔧 Implémentation Technique

**Structure Company Universe** : Ticker, nom, market cap, prix, poids, ratios, géographie, segments, supply chain, expositions réglementaires.

**Structure Regulation Table** : ID réglementation, juridiction, dates, entités réglementées, entreprises/secteurs/pays concernés, mesures clés, données extraites.

---

### 🔧 Fonctionnalités Clés

#### 1. 📊 Dashboard - Agrégation et Visualisation de Données

**Inspiré de :** Finly, AlexIA

##### Fonctionnalités :
- **Vue Globale du Portefeuille S&P 500**
  - Composition actuelle avec poids de chaque entreprise
  - Métriques de performance (Market Cap, Revenue, EPS, FCF)
  - Score de risque global du portefeuille
  - Impact financier estimé des réglementations

- **Visualisations Interactives**
  - **Graphiques en barres** : Top 10 entreprises à risque
  - **Heatmap sectorielle** : Impact par secteur × zone géographique
  - **Carte du monde** : Concentration géographique du risque
  - **Graphiques en cascade** : Impact sur valorisation du portefeuille
  - **Graphiques comparatifs** : Avant/Après réglementation

- **KPIs en Temps Réel**
  - Nombre d'entreprises affectées
  - Impact financier estimé (%)
  - Score de risque moyen
  - Secteurs les plus exposés

**Service AWS utilisé** : S3 (stockage des données), Bedrock (génération de métriques)

---

#### 2. 🤖 Financial Chatbot - Analyse en Temps Réel et Insights

**Inspiré de :** Finly, AlexIA

##### Fonctionnalités :
- **Base de Connaissances**
  - Rapports 10-K des entreprises
  - Documents réglementaires analysés
  - Historique des analyses précédentes
  - Données financières du marché

- **Capacités Conversationnelles**
  - Questions sur les entreprises : *"Quel est l'impact sur Apple de la nouvelle loi énergétique chinoise ?"*
  - Questions sectorielles : *"Quels secteurs sont le plus exposés à l'EU AI Act ?"*
  - Questions comparatives : *"Compare l'impact de deux réglementations"*
  - Explications de recommandations : *"Pourquoi recommander de réduire Nvidia ?"*

- **Recherche Web en Temps Réel** (via Tavily API)
  - Actualités récentes sur les entreprises
  - Analyses de marché complémentaires
  - Vérification de faits

**Service AWS utilisé** : 
- **Bedrock** (IA générative pour les réponses)
- **OpenSearch** (recherche dans la base de connaissances)
- **S3** (stockage des connaissances)

**Technologies** :
- **LangChain** : Framework pour orchestrer les LLM
- **ChromaDB** : Base de données vectorielle pour RAG (Retrieval Augmented Generation)

---

#### 3. 📄 Document Analysis - Extraction Rapide d'Insights

**Inspiré de :** Finly, RMBP 17

##### Fonctionnalités :
- **Upload Flexible de Documents**
  - Support de multiples formats : PDF, HTML, XML, TXT, DOCX
  - Détection automatique du type de document
  - Traitement par lots possible

- **Extraction Structurée Automatique**
  - **Entités** : Entreprises, secteurs, pays mentionnés
  - **Type de réglementation** : Loi, directive, règlement, projet de loi
  - **Dates** : Publication, entrée en vigueur, période de transition
  - **Mesures imposées** : Taxes, restrictions, subventions, sanctions
  - **Zones géographiques** : Pays et régions concernés
  - **Montants chiffrés** : Budgets, seuils, pourcentages

- **Analyse Comparative**
  - Comparaison avec réglementations précédentes
  - Identification des changements majeurs
  - Détection de contradictions potentielles

**Service AWS utilisé** :
- **Amazon Bedrock** avec `instructor` + `Pydantic` : Extraction structurée
- **Amazon Comprehend** : Pré-filtrage et identification d'entités (optimisation coûts)
- **S3** : Stockage des documents originaux et résultats extraits

**Architecture d'extraction** :
```
Document réglementaire
    ↓
Amazon Comprehend (pré-filtrage rapide)
    ↓
Bedrock + Instructor (extraction structurée)
    ↓
Pydantic Models (validation et structuration)
    ↓
JSON structuré (cache dans S3)
```

---

#### 4. 🔍 Analyse d'Impact Réglementaire

##### Processus d'Analyse :

**Étape 1 : Extraction des Informations**
- Analyse du document réglementaire (voir section 3)
- Extraction des entreprises, secteurs, pays concernés
- Identification des mesures et dates d'application

**Étape 2 : Enrichissement avec Données 10-K**
- Pour chaque entreprise concernée :
  - Extraction des chaînes d'approvisionnement (fournisseurs, partenaires)
  - Identification des zones géographiques d'opérations
  - Analyse des risques réglementaires mentionnés
  - Modèle économique de l'entreprise

**Étape 3 : Croisement avec Données de Marché**
- Composition actuelle du S&P 500 (poids, prix)
- Métriques de performance (revenus, marges, cash flow)
- Données en temps réel via Yahoo Finance si nécessaire

**Étape 4 : Calcul d'Impact**
- **Score de risque** (0-100) par entreprise
  - Basé sur l'exposition géographique
  - Basé sur la dépendance aux secteurs concernés
  - Basé sur la sensibilité aux mesures imposées
- **Impact financier estimé** (%)
  - Perte estimée de revenus
  - Baisse de marge opérationnelle
  - Impact sur valorisation boursière

**Étape 5 : Agrégation et Visualisation**
- **Par entreprise** : Score individuel et impact
- **Par secteur** : Concentration du risque sectoriel
- **Par zone géographique** : Distribution géographique du risque
- **Portefeuille global** : Impact agrégé sur le S&P 500

**Service AWS utilisé** :
- **Bedrock** : Analyse et raisonnement sur l'impact
- **Lambda** : Calculs d'impact en parallèle
- **S3** : Cache des extractions 10-K
- **DynamoDB** (optionnel) : Stockage des résultats intermédiaires

---

#### 5. 💡 Génération de Recommandations Stratégiques

**Inspiré de :** AlexIA, Finly

##### Types de Recommandations :

**A. Réallocation d'Actifs**
- **Actions à réduire** : Entreprises hautement exposées
  - Exemple : "Réduire Nvidia (NVDA) de 7.65% → 5% (exposition Chine)"
  - Justification détaillée fournie
- **Actions à augmenter** : Entreprises moins exposées ou bénéficiaires
  - Exemple : "Augmenter ExxonMobil (XOM) de 0.79% → 1.5% (moins exposé)"
- **Actions à ajouter** : Nouvelles opportunités identifiées
  - Entreprises qui pourraient bénéficier de la réglementation

**B. Rotation Sectorielle**
- **Secteurs à surpondérer** : Moins exposés aux risques réglementaires
- **Secteurs à sous-pondérer** : Très exposés aux nouvelles réglementations
- **Impact sur diversification** : Maintien de la diversification du portefeuille

**C. Réallocation Géographique**
- **Zones à réduire** : Régions géographiques à risque
- **Zones à augmenter** : Régions moins affectées
- **Exemple** : "Réduire exposition Asie-Pacifique de 15% → 10%"

**D. Ajustements Basés sur le Poids**
- Les recommandations tiennent compte du **poids actuel** dans le S&P 500
- Propositions réalistes et actionnables
- Calcul automatique des nouveaux poids

**Service AWS utilisé** :
- **Bedrock** : Génération de recommandations justifiées en langage naturel
- **Lambda** : Calculs de réallocation optimale

---

## ☁️ Services AWS et Optimisation

### Services Principaux

#### 1. **Amazon Bedrock** - Cœur de l'IA Générative

**Utilisation** :
- **Extraction structurée** : Avec `instructor[bedrock]` et Pydantic
- **Analyse d'impact** : Raisonnement sur l'exposition des entreprises
- **Génération de recommandations** : Propositions stratégiques
- **Chatbot** : Réponses conversationnelles

**Modèles recommandés** :
- **Claude Haiku** : Extraction rapide et peu coûteuse
- **Claude Sonnet** : Analyse complexe et génération de recommandations
- **Claude Opus** (si disponible) : Analyses très approfondies

**Optimisation coûts** :
- Cache des extractions dans S3 (réduction 90%+ des appels)
- Traitement par lots
- Pré-filtrage avec Comprehend avant Bedrock

---

#### 2. **Amazon S3** - Stockage Centralisé

**Structure recommandée** :
```
s3://datathon-reguai/
├── raw/
│   ├── regulations/          # Documents réglementaires originaux
│   └── fillings/             # Rapports 10-K originaux
├── processed/
│   ├── extractions/          # Résultats Bedrock (cache)
│   │   ├── reg_2024_07_12_ai_act.json
│   │   └── reg_2024_11_09_energy_law.json
│   └── company_data/         # Extractions 10-K structurées
│       ├── AAPL_extracted.json
│       └── MSFT_extracted.json
├── cache/
│   └── analysis_results/     # Résultats d'analyse complets
└── knowledge_base/
    └── embeddings/            # Vecteurs pour RAG (si OpenSearch)
```

**Bénéfices** :
- Réutilisation des données
- Historique des analyses
- Audit trail complet

---

#### 3. **AWS Lambda** - Orchestration Serverless

**Utilisation** :
- **Déclenchement automatique** : Quand un nouveau document est uploadé dans S3
- **Traitement parallèle** : Analyse de plusieurs entreprises en simultané
- **Workflow d'orchestration** : Coordination des appels Bedrock, Comprehend, etc.

**Fonctions Lambda** :
1. `extract_regulation` : Extraction d'un document réglementaire
2. `analyze_company_impact` : Analyse d'impact pour une entreprise
3. `generate_recommendations` : Génération de recommandations
4. `update_dashboard_data` : Mise à jour des KPIs

---

#### 4. **Amazon Comprehend** - Pré-filtrage Intelligent

**Utilisation** :
- **Détection d'entités** : Identification rapide des organisations, lieux, dates
- **Analyse de sentiment** : Évaluation du ton du document (si pertinent)
- **Classification de texte** : Détection du type de document

**Bénéfices** :
- **Réduction des coûts** : Comprehend ($0.0001/1000 caractères) vs Bedrock ($0.003/1000 tokens)
- **Pré-filtrage** : Identifier les parties pertinentes avant d'envoyer à Bedrock
- **Optimisation** : Réduction de 70-80% des tokens envoyés à Bedrock

---

#### 5. **Amazon OpenSearch Serverless** - Recherche Sémantique

**Utilisation** :
- **Base de connaissances** : Indexation des documents réglementaires et 10-K
- **Recherche vectorielle** : Pour le chatbot (RAG)
- **Recherche textuelle avancée** : Trouver rapidement les informations pertinentes

**Architecture RAG** :
```
Question utilisateur
    ↓
Recherche dans OpenSearch (vecteurs similaires)
    ↓
Récupération de contextes pertinents
    ↓
Enrichissement du prompt Bedrock avec contexte
    ↓
Réponse générée par Bedrock
```

**Technologies complémentaires** :
- **LangChain** : Orchestration du flux RAG
- **ChromaDB** : Alternative légère pour base vectorielle locale

---

#### 6. **Amazon DynamoDB** - Cache et Métadonnées

**Utilisation** :
- **Cache des résultats** : Stockage rapide des extractions fréquentes
- **Métadonnées** : Informations sur les documents (date, type, statut)
- **Sessions utilisateur** : Suivi des analyses en cours

---

### Optimisations et Bonnes Pratiques

#### 1. **Cache Intelligent**

**Stratégie de cache** : Vérifier cache S3 avant appel Bedrock, sauvegarder résultats en cache pour réutilisation.

**Bénéfices** :
- Réduction de 90%+ des appels Bedrock
- Réponse instantanée pour documents déjà analysés
- Économies importantes de coûts

---

#### 2. **Traitement Sélectif des 10-K**

**Traitement sélectif** : Ne traiter que les entreprises concernées par la réglementation (20-50 entreprises) plutôt que tous les 500.

**Bénéfices** :
- Traitement 10-25x plus rapide
- Coûts réduits proportionnellement
- Réponse plus rapide

---

#### 3. **Batch Processing**

**Batch Processing** : Utiliser ThreadPoolExecutor pour traiter plusieurs documents en parallèle (max_workers=5).

**Bénéfices** :
- Traitement parallèle
- Meilleure utilisation des ressources

---

## 📊 Stratégie Données : Datasets vs APIs

### ❓ Pourquoi Fournir des Datasets Statiques ?

#### 🎯 Raisons du Datathon

1. **Conditions Égales pour Tous**
   - Tous les participants travaillent sur **exactement les mêmes données**
   - Pas d'avantage pour ceux qui ont accès à des APIs premium
   - Évaluation équitable par le jury

2. **Reproductibilité**
   - Les résultats peuvent être **reproduits exactement** par le jury
   - Pas de variation due aux changements de données en temps réel
   - Comparaison directe entre équipes

3. **Stabilité Technique**
   - Pas de problèmes de connexion API pendant les 36 heures
   - Pas de limites de rate (quotas API dépassés)
   - Pas de pannes d'API externes
   - Données garanties disponibles

4. **Données Nettoyées et Structurées**
   - Les CSV sont déjà **formatés et nettoyés**
   - Les rapports 10-K sont **standardisés** (format HTML/XML)
   - **Pas de temps perdu** en nettoyage de données

5. **Base de Référence Solide**
   - Composition S&P 500 officielle à une date précise
   - Métriques financières cohérentes et vérifiées
   - Documents réglementaires authentiques

---

### 🚀 Pourquoi Utiliser des APIs Malgré les Datasets ?

#### 💡 Avantages des APIs (Mentionnés dans le Datathon)

Le notebook `Introduction-Datathon.ipynb` mentionne explicitement :
> *"Vous pouvez également utiliser des sources externes (Yahoo Finance, SEC, etc.)"*

Les APIs permettent de :

1. **Démontrer la Scalabilité Réelle**
   - Votre solution fonctionne avec des données en temps réel
   - Pas seulement des snapshots historiques
   - Adaptabilité aux nouvelles données

2. **Enrichir les Analyses**
   - Actualités récentes sur les entreprises (Tavily, News APIs)
   - Données de marché mises à jour (Yahoo Finance)
   - Informations complémentaires (SEC API pour nouveaux rapports)

3. **Montrer l'Intégration Production**
   - Une solution réelle utiliserait des APIs
   - Démontre que vous pensez "production-ready"
   - Impression positive sur le jury

4. **Flexibilité et Adaptabilité**
   - Traiter de nouveaux documents réglementaires (dimanche matin)
   - Adapter aux changements de composition S&P 500
   - Fonctionner avec données futures

---

### 🎯 Stratégie Recommandée : Approche Hybride

#### ✅ Utiliser les Datasets comme **Base de Référence**

Les datasets fournis doivent être votre **source de vérité principale** :

**Chargement des données de base (OBLIGATOIRE)** : Charger composition_sp500.csv et stocks-performance.csv. Convertir les poids avec format européen (virgule → point). Utiliser comme référence principale pour tickers et poids officiels.

**Pourquoi ?**
- ✅ Composition officielle S&P 500 validée
- ✅ Poids dans l'indice précis et vérifiés
- ✅ Métriques financières cohérentes

---

#### 🚀 Utiliser les APIs pour **Enrichir et Compléter**

Les APIs servent à **ajouter de la valeur**, pas remplacer les datasets :

##### 1. **Yahoo Finance** - Données de Marché Complémentaires

**Yahoo Finance** : Utiliser pour enrichir avec prix actuels, 52-week high/low, beta. Ne pas remplacer la composition ou les poids du CSV officiel.

**Cas d'Usage** :
- ✅ Prix actuels (le CSV a prix au 15 août, API donne prix actuel)
- ✅ Volatilité (Beta) pour calcul de risque
- ✅ Volume de trading
- ❌ **Ne pas remplacer** la composition ou les poids du CSV

---

##### 2. **Tavily API / News APIs** - Actualités et Contexte

**Tavily API** : Rechercher actualités récentes sur entreprise + réglementation pour enrichir l'analyse d'impact avec contexte récent.

**Cas d'Usage** :
- ✅ Actualités récentes sur l'entreprise et la réglementation
- ✅ Analyser le sentiment du marché
- ✅ Vérifier des faits mentionnés dans les documents
- ✅ Contexte supplémentaire pour justifications

---

##### 3. **SEC API** - Nouveaux Rapports (Optionnel)

**SEC API** : Accéder à des rapports 10-K plus récents que ceux fournis pour comparer évolution des risques réglementaires.

**Cas d'Usage** :
- ✅ Accéder à des 10-K plus récents que ceux fournis
- ✅ Comparer évolution des risques réglementaires
- ✅ Vérifier si nouvelles informations disponibles

**Note** : Les 10-K fournis dans `fillings/` sont déjà complets et récents (2024). Ceci est optionnel.

---

### 📋 Stratégie Concrète pour le Datathon

#### Workflow Recommandé

```
┌─────────────────────────────────────────────────────────┐
│  1. CHARGER DATASETS DE BASE (Source de vérité)        │
│     - composition_sp500.csv                             │
│     - stocks-performance.csv                            │
│     - fillings/ (10-K)                                  │
│     - directives/ (réglementations)                     │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  2. ANALYSER AVEC BEDROCK (Basé sur datasets)           │
│     - Extraire informations réglementaires              │
│     - Analyser 10-K des entreprises concernées        │
│     - Calculer impact basé sur données CSV            │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  3. ENRICHIR AVEC APIs (Optionnel mais recommandé)     │
│     - Yahoo Finance: Prix actuels, volatilité           │
│     - Tavily: Actualités récentes                      │
│     - News APIs: Sentiment marché                      │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│  4. GÉNÉRER RECOMMANDATIONS (Combiné)                  │
│     - Basé sur données CSV (composition, poids)       │
│     - Enrichi avec contexte API (actualités)           │
└─────────────────────────────────────────────────────────┘
```

---

### 📊 Résumé : Quand Utiliser Quoi ?

| Type de Donnée | Source | Quand l'Utiliser |
|---------------|--------|-----------------|
| **Composition S&P 500** | CSV | ✅ TOUJOURS (source de vérité) |
| **Poids dans l'indice** | CSV | ✅ TOUJOURS (officiel) |
| **Métriques financières** | CSV | ✅ PRIORITAIRE (cohérentes) |
| **Rapports 10-K** | fillings/ | ✅ PRIORITAIRE (déjà fournis) |
| **Documents réglementaires** | directives/ | ✅ PRIORITAIRE (documents du cas) |
| **Prix actuel des actions** | Yahoo Finance API | ⭐ ENRICHISSEMENT |
| **Actualités récentes** | Tavily/News APIs | ⭐ CONTEXTE |
| **Volatilité (Beta)** | Yahoo Finance API | ⭐ CALCUL DE RISQUE |
| **Données de marché temps réel** | Yahoo Finance API | ⭐ VISUALISATIONS ACTUELLES |

---

## 🔄 Flux de Fonctionnement Complet

### Scénario : Analyse d'un Nouveau Document Réglementaire

**Étape 1 : Upload**
```
Utilisateur upload document via Streamlit
    ↓
Document stocké dans S3 (raw/regulations/)
    ↓
Génération hash MD5 du document
    ↓
Vérification cache (déjà analysé ?)
```

**Étape 2 : Pré-traitement**
```
Si nouveau document:
    ↓
Amazon Comprehend (détection entités rapide)
    ↓
Identification: organisations, lieux, dates
    ↓
Filtrage: parties pertinentes du document
```

**Étape 3 : Extraction Structurée**
```
Bedrock + Instructor + Pydantic
    ↓
Extraction:
- Entités (entreprises, secteurs, pays)
- Type de réglementation
- Dates (publication, application)
- Mesures imposées
    ↓
JSON structuré sauvegardé dans S3 (processed/extractions/)
```

**Étape 4 : Identification des Entreprises Concernées**
```
Entités extraites
    ↓
Matching avec liste S&P 500 (tickers)
    ↓
Filtrage: seulement entreprises du S&P 500
    ↓
Liste de 20-50 entreprises à analyser
```

**Étape 5 : Analyse des 10-K (Si Nécessaire)**
```
Pour chaque entreprise concernée:
    ↓
Vérifier cache (10-K déjà extrait ?)
    ↓
Si non → Bedrock extraction:
- Chaînes d'approvisionnement
- Zones géographiques d'opérations
- Dépendances critiques
    ↓
Extraction stockée en cache (S3)
```

**Étape 6 : Calcul d'Impact**
```
Croisement:
- Informations réglementaires
- Exposition entreprise (10-K)
- Performance actuelle (CSV)
- Poids dans S&P 500
    ↓
Lambda (calculs en parallèle)
    ↓
Score de risque + Impact financier par entreprise
```

**Étape 7 : Enrichissement avec APIs (Optionnel)**
```
Pour entreprises à haut risque:
    ↓
Yahoo Finance: Prix actuels, volatilité
    ↓
Tavily: Actualités récentes
    ↓
Enrichissement du contexte d'analyse
```

**Étape 8 : Génération de Recommandations**
```
Agrégation par:
- Secteur
- Zone géographique
    ↓
Bedrock (génération recommandations)
    ↓
Justifications pour chaque recommandation
    ↓
Réallocation optimale suggérée
```

**Étape 9 : Visualisation et Présentation**
```
Résultats compilés
    ↓
Génération graphiques (Plotly)
    ↓
Mise à jour Dashboard Streamlit
    ↓
Affichage à l'utilisateur
```

---

## 🎨 Résultat Final Attendu

### 🌐 Interface Web Interactive

Votre solution doit être un **dashboard web** accessible en ligne avec:

#### 1. **Page d'Upload**
- Zone de dépôt de documents réglementaires
- Support de multiples formats (PDF, HTML, XML, texte)
- Indication que l'outil s'adapte à n'importe quel format

#### 2. **Résultats d'Extraction**
Afficher clairement ce qui a été extrait:
- **Entités identifiées**:
  - Entreprises mentionnées
  - Secteurs concernés (Tech, Énergie, Finance, etc.)
  - Pays/zones géographiques
- **Mesures extraites**:
  - Types de réglementation (taxe, restriction, subvention, etc.)
  - Dates d'application
  - Détails des mesures

#### 3. **Analyse d'Impact sur le Portefeuille**

##### Vue globale
- **Score de risque global** du portefeuille S&P 500
- **Impact financier estimé** (ex: -2.3% de valeur totale)
- **Alertes** pour les entreprises les plus exposées

##### Vue par entreprise
- **Tableau/liste** des entreprises du S&P 500 avec:
  - Score de risque (0-100 ou A-F)
  - Impact estimé (% de perte potentielle)
  - Raison de l'exposition (ex: "Opérations en Chine affectées par nouvelle réglementation énergétique")
  - Visualisation graphique (barres, heatmap)

##### Vue par secteur
- **Graphique secteurs** touchés
- Identification des secteurs les plus à risque
- Distribution du risque par secteur

##### Vue géographique
- **Carte du monde** ou graphique montrant:
  - Zones géographiques concernées
  - Concentration du risque par pays/région
  - Entreprises exposées par zone

#### 4. **Recommandations Actionnables**

##### Réallocation suggérée
- **Tableau comparatif**:
  - Actions à **réduire** (avec justification)
  - Actions à **augmenter** (avec justification)
  - Actions à **ajouter** si pas dans le portefeuille

##### Rotation sectorielle
- **Graphique** montrant:
  - Secteurs à surpondérer
  - Secteurs à sous-pondérer
  - Impact sur la diversification

##### Explications transparentes
- Pour chaque recommandation, **explication claire**:
  - Pourquoi cette recommandation ?
  - Quel est le raisonnement ?
  - Quels sont les risques atténués ?

#### 5. **Visualisations Clés**

- **Graphiques en barres**: Top entreprises à risque
- **Heatmap**: Impact par secteur × pays
- **Graphiques en camembert**: Distribution du risque
- **Graphique évolution**: Impact sur valorisation du portefeuille
- **Tableau interactif**: Filtrables et triables

#### 6. **Transparence et Explicabilité**

- **Section "Comment ça marche"**:
  - Explication de la méthodologie
  - Sources des données utilisées
  - Limitations et incertitudes

- **Détails par entreprise**:
  - Pourquoi cette entreprise est à risque ?
  - Quelles parties du 10-K ont été analysées ?
  - Quel lien avec la réglementation ?

---

### 📊 Exemple de Résultat Concret

**Scénario**: Analyse du document "中华人民共和国能源法" (Loi énergétique chinoise)

**Résultats affichés**:

1. **Extraction**:
   - Secteurs: Énergie, Batteries, Automobile
   - Mesures: Restrictions export énergétiques, taxes carbone
   - Dates: Application progressive dès 2025

2. **Impact calculé**:
   - **Apple (AAPL)**: Risque **ÉLEVÉ** (75/100)
     - Raison: Supply chain dépendante de Chine, fournisseurs énergétiques
     - Impact estimé: -3.2% sur marge opérationnelle
     - Exposition: 40% de production en Chine
   
   - **Tesla (TSLA)**: Risque **MOYEN** (45/100)
     - Raison: Gigafactory Shanghai exposée, mais diversification
     - Impact estimé: -1.5% sur revenus
   
   - **ExxonMobil (XOM)**: Risque **FAIBLE** (15/100)
     - Raison: Pas d'opérations majeures en Chine
     - Impact estimé: <0.5%

3. **Recommandations**:
   - **Réduire** Apple de 5.97% → 4.5% du portefeuille
   - **Augmenter** entreprises énergétiques US (ExxonMobil, Chevron)
   - **Rotation**: Surpondérer secteurs non-dépendants de Chine
   - **Ajouter**: Entreprises bénéficiaires (fabricants équipements énergétiques US)

4. **Visualisations**:
   - Heatmap montrant concentration risque Chine
   - Graphique secteur: Tech très exposé, Énergie US moins exposé
   - Carte: Asie-Pacifique zone rouge, Amérique du Nord zone verte

---

## 💻 Points Clés dans les Notebooks

### 🔑 Code à Réutiliser

#### 1. **Extraction avec Bedrock (Introduction-Datathon, Cellule 20)**

**Utilisation** : Extraction structurée avec instructor + Pydantic pour extraire informations réglementaires, chaînes d'approvisionnement, expositions géographiques depuis les 10-K.

**💡 Adaptation** : Créez vos propres modèles Pydantic selon vos besoins.

---

#### 2. **Utilisation Simple de Bedrock (Introduction-Datathon, Cellule 13)**
Utilisez `client.converse()` avec Claude Sonnet pour analyser les documents réglementaires et extraire les informations clés.

---

#### 3. **Liste des Modèles Disponibles (Introduction-Datathon, Cellule 15)**
Utilisez `bedrock.list_foundation_models()` pour identifier les modèles disponibles.

---

#### 4. **Agents Strands (Introduction-Datathon, Cellule 24)**
Créer une interface conversationnelle avec vos données en utilisant `Agent(tools=[file_read])`.

---

#### 5. **Configuration SageMaker Project (getting_started, Cellule 2-4)**
Accès aux ressources AWS via `project.iam_role`, `project.s3.root`, `project.connection()`.

---

#### 6. **Visualisation de DataFrames (getting_started, Cellule 30)**
Affichage automatique enrichi des DataFrames avec magic `%display`.

---

#### 7. **Chargement CSV (Format Européen)**
Convertir les colonnes avec virgule en float : `.str.replace(',', '.').astype(float)`

---

#### 8. **Enrichissement avec Yahoo Finance**
Utilisez `yfinance` pour enrichir avec données marché en temps réel (prix, beta, market cap).

---

#### 9. **Enrichissement avec Tavily API**
Utilisez `TavilyClient` pour rechercher actualités récentes sur les impacts réglementaires.

---

## 📊 Technologies et Bibliothèques

### Core
- **Python 3.9+**
- **FastAPI** : API backend (optionnel, si séparation frontend/backend)
- **Streamlit** : Interface utilisateur web

### IA et NLP
- **boto3** : SDK AWS
- **instructor[bedrock]** : Extraction structurée
- **anthropic** : Client Anthropic (si nécessaire)
- **langchain** : Framework LLM
- **chromadb** : Base vectorielle (alternative à OpenSearch)

### Data Science
- **pandas** : Manipulation de données
- **numpy** : Calculs numériques
- **scipy** : Statistiques

### Visualisation
- **plotly** : Graphiques interactifs
- **matplotlib** : Graphiques statiques
- **seaborn** : Visualisations statistiques

### Text Processing
- **beautifulsoup4** : Parsing HTML/XML
- **lxml** : Parseur XML rapide
- **sec-parser** : Parsing rapports 10-K
- **pdfplumber** / **PyPDF2** : Extraction PDF

### APIs Externes
- **yfinance** : Données Yahoo Finance
- **tavily-python** : Recherche web en temps réel

### Utilities
- **tqdm** : Barres de progression
- **python-dotenv** : Variables d'environnement
- **pydantic** : Validation de données

---

## ✅ Critères de Réussite

### Obligatoires
- ✅ Fonctionne avec **n'importe quel format** de document
- ✅ Extraction automatique des entités clés
- ✅ Calcul d'impact sur S&P 500
- ✅ Recommandations actionnables
- ✅ Interface visuelle claire

### Bonus (différenciation)
- ⭐ Explications très transparentes
- ⭐ Simulation de scénarios multiples
- ⭐ Export des résultats (PDF, Excel)
- ⭐ Historique des analyses
- ⭐ Comparaison entre réglementations

---

## 🔑 Points Différenciants

1. **Triple Approche** : Dashboard + Chatbot + Analyse de documents
2. **Optimisation AWS** : Cache intelligent, pré-filtrage Comprehend, traitement sélectif
3. **Transparence Maximale** : Explications détaillées pour chaque recommandation
4. **Flexibilité** : S'adapte à tout type de document réglementaire
5. **Base de Connaissances** : RAG avec OpenSearch/ChromaDB pour contexte riche
6. **Approche Hybride** : Datasets comme base + APIs pour enrichissement

---

## 🚀 Prochaines Étapes

1. **Explorer les données**:
   - Lire quelques documents réglementaires
   - Examiner des rapports 10-K
   - Analyser les CSV

2. **Prototyper l'extraction**:
   - Tester Bedrock sur un document
   - Extraire entités, mesures, dates

3. **Développer le calcul d'impact**:
   - Croiser réglementations + 10-K
   - Calculer scores de risque

4. **Créer l'interface**:
   - Dashboard interactif
   - Visualisations

5. **Tester et affiner**:
   - Tester avec tous les documents fournis
   - Préparer pour nouveau document dimanche

---

**Cette architecture est conçue pour être :**
- 🚀 **Performante** : Optimisations multiples
- 💰 **Coût-efficace** : Cache et pré-filtrage
- 📈 **Scalable** : Services serverless AWS
- 🔧 **Maintenable** : Architecture modulaire
- 🎯 **Aligned avec le jury** : Utilisation maximale des services AWS

---

**💡 Conseil Final :**

Utilisez les **datasets comme fondation** et les **APIs comme enrichissement**. C'est la meilleure approche pour impressionner le jury tout en respectant les données de référence fournies !

**Bonne chance pour le Datathon ! 🎯**

