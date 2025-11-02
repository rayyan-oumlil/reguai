# ☁️ Services AWS - Résumé Rapide

Guide concis sur les services Amazon utilisés dans ReguAI.

---

## 🤖 Amazon Bedrock - IA Générative

**Utilisation** :
- **Claude Haiku** : Extractions rapides (entités, dates, secteurs) - rapide et économique
- **Claude Sonnet** : Analyses d'impact et génération de recommandations - meilleur raisonnement

**Pourquoi** : C'est le cerveau IA pour raisonner et générer du contenu

---

## 🧠 Amazon Comprehend - Pré-filtrage NLP

**Utilisation** :
- Détecte entités (entreprises, pays, dates) **avant** d'envoyer à Bedrock
- Identifie les parties pertinentes d'un document

**Pourquoi** : Réduit les tokens envoyés à Bedrock → **Économie 70-80%** des coûts

---

## 📦 Amazon S3 - Stockage et Cache

**Utilisation** :
- Stocke documents originaux, résultats Bedrock, extractions
- Cache intelligent pour réutiliser les analyses

**Pourquoi** : Cache → Réutilisation des analyses → **Économie 90%+** des appels Bedrock

---

## 📄 Amazon Textract - Extraction PDF

**Utilisation** :
- Extrait texte depuis PDF scannés/images

**Pourquoi** : Si documents en PDF/image (nos directives sont HTML, donc peu utilisé)

---

## ⚡ AWS Lambda - Orchestration

**Utilisation** :
- Déclenche workflow automatiquement quand document uploadé
- Orchestre les appels aux différents services

**Pourquoi** : Automation serverless sans gérer infrastructure

---

## 🔍 Amazon OpenSearch - Base de Connaissances

**Utilisation** :
- Indexe documents pour recherche sémantique (chatbot RAG)
- Recherche vectorielle pour contexte

**Pourquoi** : Permet au chatbot de trouver infos pertinentes dans les documents

---

## 🗃️ Amazon DynamoDB - Cache Rapide

**Utilisation** :
- Métadonnées des documents
- Cache résultats fréquents

**Pourquoi** : Accès très rapide (< 10ms) pour requêtes répétées

---

## 💻 Amazon SageMaker Studio - Environnement Dev

**Utilisation** :
- Notebooks Jupyter
- Développement et tests
- Déploiement Streamlit

**Pourquoi** : Environnement de développement avec accès direct aux services AWS

---

## 📊 Résumé en Une Ligne

**Essentiels** :
- 🧠 **Bedrock** = Cerveau IA
- 💾 **S3** = Stockage/Cache
- 🔍 **Comprehend** = Pré-filtrage économique

**Optionnels** :
- 📄 Textract (si PDF scannés)
- ⚡ Lambda (orchestration)
- 🔍 OpenSearch (chatbot RAG)
- 🗃️ DynamoDB (cache rapide)
- 💻 SageMaker (dev)

---

**💡 Astuce** : Commencez avec Bedrock + S3 + Comprehend, ajoutez le reste selon besoins !

