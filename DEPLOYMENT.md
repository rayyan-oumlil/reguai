# 🚀 Guide de Déploiement Streamlit Cloud

## Prérequis

Votre application est **presque prête** pour Streamlit Cloud, mais quelques ajustements sont nécessaires.

## ✅ Ce qui est déjà OK

1. **requirements.txt** : Présent et complet
2. **Point d'entrée** : `scripts/app.py` existe
3. **Chemins relatifs** : Le code utilise `Path(__file__)` pour trouver la racine, ce qui fonctionne sur Streamlit Cloud

## ⚠️ Ce qui doit être configuré

### 1. Configuration Streamlit Cloud

Le fichier `.streamlit/config.toml` a été créé avec les paramètres de base.

### 2. Variables d'environnement AWS (Streamlit Secrets)

**Important** : Sur Streamlit Cloud, vous ne pouvez pas utiliser un fichier `.env`. Vous devez utiliser **Streamlit Secrets**.

#### Étape 1 : Configurer les secrets dans Streamlit Cloud

1. Allez sur [share.streamlit.io](https://share.streamlit.io)
2. Créez un nouveau projet ou modifiez un existant
3. Allez dans **Settings** → **Secrets**
4. Ajoutez les secrets suivants :

```toml
AWS_ACCESS_KEY_ID = "votre_access_key"
AWS_SECRET_ACCESS_KEY = "votre_secret_key"
AWS_REGION = "us-east-1"
S3_BUCKET_NAME = "datathon-reguai"  # Optionnel
```

#### Étape 2 : Adapter le code pour Streamlit Secrets

Le code actuel charge `.env` localement. Pour Streamlit Cloud, il faut aussi lire `st.secrets`.

**Option A : Modification manuelle (recommandée)**

Modifiez `scripts/app.py` pour ajouter la lecture de `st.secrets` :

```python
# Après l'import de streamlit
import streamlit as st

# Charger depuis st.secrets si disponible (Streamlit Cloud)
if hasattr(st, 'secrets') and st.secrets:
    try:
        if 'AWS_ACCESS_KEY_ID' in st.secrets:
            os.environ['AWS_ACCESS_KEY_ID'] = st.secrets['AWS_ACCESS_KEY_ID']
        if 'AWS_SECRET_ACCESS_KEY' in st.secrets:
            os.environ['AWS_SECRET_ACCESS_KEY'] = st.secrets['AWS_SECRET_ACCESS_KEY']
        if 'AWS_REGION' in st.secrets:
            os.environ['AWS_REGION'] = st.secrets['AWS_REGION']
        if 'S3_BUCKET_NAME' in st.secrets:
            os.environ['S3_BUCKET_NAME'] = st.secrets['S3_BUCKET_NAME']
    except Exception as e:
        print(f"⚠️ Erreur chargement secrets: {e}")
```

**Option B : Utiliser le code existant (fonctionne si .env est absent)**

Le code actuel charge `.env` mais continue si le fichier n'existe pas. Sur Streamlit Cloud, `.env` n'existera pas, donc les variables devront être dans `st.secrets`.

### 3. Données nécessaires

Votre application lit des données depuis :
- `data/generated/company_universe/company_universe.json`
- `data/generated/extracted_directives/`
- `data/generated/impact_analysis/`
- `data/generated/recommendations/`
- `data/raw/directives/`

**Important** : Ces dossiers doivent être dans votre repository Git pour être accessibles sur Streamlit Cloud.

Vérifiez que `.gitignore` n'ignore pas ces fichiers :
- ✅ `data/generated/` est explicitement inclus (`!data/generated/**/*`)
- ⚠️ `data/raw/directives/` pourrait être ignoré - vérifiez si vos fichiers sont trackés

### 4. Déploiement

1. **Pousser le code sur GitHub** :
   ```bash
   git add .
   git commit -m "Prepare for Streamlit Cloud deployment"
   git push origin main
   ```

2. **Créer le projet sur Streamlit Cloud** :
   - Allez sur [share.streamlit.io](https://share.streamlit.io)
   - Cliquez sur **New app**
   - Sélectionnez votre repository
   - **Main file path** : `scripts/app.py`
   - **Python version** : 3.9 ou supérieur (recommandé : 3.11)

3. **Configurer les secrets** (voir étape 2)

4. **Déployer** : Streamlit Cloud déploiera automatiquement

## 🔧 Problèmes potentiels

### Problème 1 : Chemins de fichiers

Les chemins relatifs `data/...` fonctionnent si les fichiers sont dans le repo. Si vous avez des fichiers volumineux, considérez :

- **Option A** : Utiliser S3 pour stocker les données et charger depuis S3
- **Option B** : Utiliser Git LFS pour les gros fichiers
- **Option C** : Générer les données à la volée au premier lancement

### Problème 2 : Taille du repository

Streamlit Cloud a une limite de taille pour les repositories. Si `data/` est trop volumineux :

- Utilisez S3 pour stocker les données
- Utilisez Git LFS
- Ne commitez que les fichiers essentiels

### Problème 3 : Timeout

Si certaines opérations (extraction, impact analysis) prennent trop de temps, vous pourriez rencontrer des timeouts. Dans ce cas :

- Utilisez des jobs asynchrones
- Cachez les résultats avec `@st.cache_data`
- Limitez la taille des documents traités

## 📝 Checklist avant déploiement

- [ ] Code poussé sur GitHub
- [ ] Secrets configurés sur Streamlit Cloud
- [ ] Fichiers de données trackés dans Git (ou accessible via S3)
- [ ] `.streamlit/config.toml` créé
- [ ] `requirements.txt` à jour
- [ ] Test local : `streamlit run scripts/app.py` fonctionne

## 🚨 Notes importantes

1. **Sécurité** : Ne commitez JAMAIS votre fichier `.env` dans Git
2. **Coûts AWS** : Les appels à Bedrock/Comprehend/Textract génèrent des coûts
3. **Limites Streamlit Cloud** : 
   - Free tier : 1 app par compte
   - Timeout : 30 secondes par requête
   - RAM : 1 GB
   - CPU : Limitée

## 📚 Ressources

- [Streamlit Cloud Documentation](https://docs.streamlit.io/streamlit-community-cloud)
- [Streamlit Secrets Management](https://docs.streamlit.io/streamlit-community-cloud/deploy-your-app/secrets-management)

