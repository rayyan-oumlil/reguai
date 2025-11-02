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

### 1. Vérifier les imports

```bash
python test_imports.py
```

### 2. Lancer l'application Streamlit

```bash
python -m streamlit run app.py
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
├── app.py                          # Application Streamlit principale
├── test_imports.py                 # Script de test des imports
├── requirements_essential.txt      # Dépendances essentielles
├── README.md                       # Ce fichier
├── ARCHITECTURE_ET_FONCTIONNEMENT.md
├── GUIDE_COMPLET_PROJET.md
├── STRATEGIE_DONNEES_DATASETS_ET_APIS.md
├── 2025-08-15_composition_sp500.csv
├── 2025-09-26_stocks-performance.csv
├── directives/                     # Documents réglementaires
└── fillings/                       # Rapports 10-K
```

## 🔧 Technologies Utilisées

- **Streamlit** : Interface web
- **Plotly** : Visualisations interactives
- **Pandas** : Manipulation de données
- **Amazon Bedrock** : IA générative (à implémenter)
- **boto3** : SDK AWS

## 📝 Notes de Développement

### Fonctionnalités à Implémenter

1. **Extraction avec Bedrock** :
   - Intégrer `instructor[bedrock]` pour l'extraction structurée
   - Créer des modèles Pydantic pour les réglementations

2. **Analyse d'Impact** :
   - Croiser réglementations avec données 10-K
   - Calculer scores de risque

3. **Chatbot** :
   - Intégrer Bedrock pour réponses conversationnelles
   - Base de connaissances avec RAG (optionnel)

4. **Cache** :
   - Implémenter cache S3 pour les extractions
   - Réduire les coûts Bedrock

## 🎓 Ressources

- Documentation Streamlit : https://docs.streamlit.io
- Amazon Bedrock : https://docs.aws.amazon.com/bedrock
- Introduction-Datathon.ipynb : Exemples de code

## 📧 Support

Pour toute question, consultez les fichiers de documentation :
- `ARCHITECTURE_ET_FONCTIONNEMENT.md` : Architecture détaillée
- `GUIDE_COMPLET_PROJET.md` : Guide complet du projet
- `STRATEGIE_DONNEES_DATASETS_ET_APIS.md` : Stratégie données

---

**Bonne chance pour le Datathon ! 🚀**
