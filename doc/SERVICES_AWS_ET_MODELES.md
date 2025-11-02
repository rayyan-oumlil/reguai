# ☁️ Services AWS et Modèles - Guide Pratique ReguAI

Guide concis sur les services Amazon à utiliser et l'utilisation des modèles pour ReguAI.

---

## 🎯 Vue d'Ensemble

Après l'**extraction des données** (Textract, Sec-parser), nous utilisons les **modèles Bedrock** et d'autres services AWS pour analyser, enrichir et générer les recommandations.

---

## 🤖 Amazon Bedrock - Modèles d'IA

### 🎯 Utilisation Principale

**Bedrock est le cœur de l'IA** pour :
- ✅ Extraction structurée de données
- ✅ Analyse d'impact réglementaire
- ✅ Génération de recommandations
- ✅ Réponses du chatbot

### 📋 Modèles Disponibles

#### 1. **Claude Haiku** (Rapide et Économique)
```
modelId: "global.anthropic.claude-haiku-4-5-20251001-v1:0"
```

**Utilisation** :
- ✅ Extraction rapide de données structurées
- ✅ Pré-analyse de documents (premier passage)
- ✅ Traitement de gros volumes

**Avantages** :
- ⚡ Très rapide
- 💰 Moins cher que Sonnet/Opus
- 🎯 Parfait pour extractions simples

**Exemple** :
```python
import boto3
import instructor
from pydantic import BaseModel

bedrock_client = boto3.client('bedrock-runtime')
client = instructor.from_bedrock(bedrock_client)

# Extraction structurée
class RegulationInfo(BaseModel):
    companies: List[str]
    sectors: List[str]
    countries: List[str]
    effective_date: str

result = client.chat.completions.create(
    modelId="global.anthropic.claude-haiku-4-5-20251001-v1:0",
    messages=[{"role": "user", "content": document_text}],
    response_model=RegulationInfo
)
```

---

#### 2. **Claude Sonnet** (Analyse Complexe)
```
modelId: "global.anthropic.claude-sonnet-4-5-20250929-v1:0"
```

**Utilisation** :
- ✅ Analyse d'impact détaillée
- ✅ Raisonnement sur les expositions des entreprises
- ✅ Génération de recommandations justifiées
- ✅ Réponses du chatbot financier

**Avantages** :
- 🧠 Meilleur raisonnement
- 📊 Analyse plus approfondie
- 💬 Excellentes capacités conversationnelles

**Exemple** :
```python
# Analyse d'impact
response = client.converse(
    modelId="global.anthropic.claude-sonnet-4-5-20250929-v1:0",
    messages=[{
        "role": "user",
        "content": [{"text": f"""
            Analyse l'impact de cette réglementation sur {company}:
            {regulation_data}
            
            Données entreprise:
            {company_data}
        """}]
    }],
    inferenceConfig={"temperature": 0.3}  # Plus déterministe pour analyse
)
```

---

#### 3. **Claude Opus** (Optionnel - Analyses Très Approfondies)
```
modelId: "global.anthropic.claude-opus-..." (si disponible)
```

**Utilisation** :
- ⭐ Analyses très complexes
- ⭐ Recommandations stratégiques avancées
- ⭐ Quand Haiku/Sonnet ne suffisent pas

**Note** : Plus cher, utiliser seulement pour cas critiques.

---

### 🔧 Stratégie d'Utilisation Optimale

```
Document réglementaire
    ↓
Claude Haiku (extraction rapide)
    → Entités, dates, secteurs
    ↓
Pour chaque entreprise concernée:
    Claude Sonnet (analyse impact)
    → Score risque, impact financier
    ↓
Agrégation
    ↓
Claude Sonnet (génération recommandations)
    → Actions suggérées avec justifications
```

**Avantages** :
- 💰 Réduction des coûts (Haiku pour extractions simples)
- ⚡ Performance (analyse seulement où nécessaire)
- 🎯 Qualité (Sonnet pour raisonnement complexe)

---

## 📄 Amazon Textract - Extraction de Texte

### 🎯 Utilisation

**Textract extrait le texte** depuis :
- 📄 PDF (documents réglementaires scannés)
- 🖼️ Images (documents papier numérisés)
- 📋 Formulaires complexes

### 📋 Exemple d'Utilisation

```python
import boto3

textract = boto3.client('textract')

# Extraire texte depuis PDF
response = textract.detect_document_text(
    Document={'S3Object': {'Bucket': 'datathon-reguai', 'Name': 'regulation.pdf'}}
)

# Extraire le texte
text = ""
for item in response['Blocks']:
    if item['BlockType'] == 'LINE':
        text += item['Text'] + "\n"

# Puis envoyer à Bedrock pour analyse
```

**Quand utiliser** :
- ✅ Documents PDF non-texte (scannés)
- ✅ Images de documents
- ✅ Quand le texte n'est pas directement accessible

**Note** : Pour HTML/XML (comme nos directives), pas besoin de Textract.

---

## 🧠 Amazon Comprehend - NLP et Pré-filtrage

### 🎯 Utilisation Principale

**Comprehend est utilisé pour** :
- 🔍 Pré-filtrage avant Bedrock (réduction des coûts)
- 🏷️ Détection d'entités rapide
- 📊 Analyse de sentiment
- 🎯 Classification de documents

### 💰 Pourquoi Comprehend ?

**Comparaison des coûts** :
- Comprehend : ~$0.0001/1000 caractères
- Bedrock : ~$0.003/1000 tokens

**Stratégie** :
```
Document (50,000 caractères)
    ↓
Comprehend (détection entités)
    → Identifie parties pertinentes (10,000 caractères)
    ↓
Bedrock (analyse seulement parties pertinentes)
    → Économie de 80% des tokens !
```

### 📋 Exemple d'Utilisation

```python
import boto3

comprehend = boto3.client('comprehend')

# Détecter les entités (organisations, lieux, dates)
response = comprehend.detect_entities(
    Text=document_text,
    LanguageCode='en'
)

# Filtrer pour garder seulement parties avec entités pertinentes
relevant_entities = [e for e in response['Entities'] 
                    if e['Type'] in ['ORGANIZATION', 'LOCATION', 'DATE']]

# Extraire seulement les passages pertinents
relevant_text = extract_relevant_sections(document_text, relevant_entities)

# Maintenant envoyer seulement relevant_text à Bedrock
```

---

## 🗄️ Amazon S3 - Stockage Centralisé

### 🎯 Structure Recommandée

```
s3://datathon-reguai/
├── raw/
│   ├── regulations/          # Documents originaux
│   └── fillings/             # 10-K originaux
│
├── processed/
│   ├── extractions/          # Résultats Bedrock (CACHE)
│   │   ├── reg_eu_ai_act.json
│   │   └── reg_china_energy.json
│   ├── company_data/         # Extractions 10-K
│   │   ├── AAPL.json
│   │   └── MSFT.json
│   └── market_data/          # Données marché enrichies
│
└── cache/
    └── analysis_results/     # Analyses complètes
```

### 💡 Stratégie de Cache

```python
import boto3
import json
import hashlib

s3 = boto3.client('s3')
BUCKET = 'datathon-reguai'

def extract_with_cache(document_text):
    # Générer hash du document
    doc_hash = hashlib.md5(document_text.encode()).hexdigest()
    cache_key = f'processed/extractions/{doc_hash}.json'
    
    # Vérifier cache
    try:
        response = s3.get_object(Bucket=BUCKET, Key=cache_key)
        cached_data = json.loads(response['Body'].read())
        print("✅ Utilisation du cache")
        return cached_data
    except:
        pass
    
    # Sinon, appeler Bedrock
    print("🔄 Extraction avec Bedrock...")
    extracted_data = bedrock_extract(document_text)
    
    # Sauvegarder en cache
    s3.put_object(
        Bucket=BUCKET,
        Key=cache_key,
        Body=json.dumps(extracted_data)
    )
    
    return extracted_data
```

**Bénéfices** :
- ⚡ Réponses instantanées pour documents déjà analysés
- 💰 Économie de 90%+ des appels Bedrock
- 📊 Historique des analyses

---

## ⚡ AWS Lambda - Orchestration Serverless

### 🎯 Utilisation

**Lambda orchestre** le workflow complet :

```python
import json
import boto3

def lambda_handler(event, context):
    # 1. Récupérer document depuis S3
    s3 = boto3.client('s3')
    document = s3.get_object(...)
    
    # 2. Pré-filtrage avec Comprehend
    comprehend = boto3.client('comprehend')
    entities = comprehend.detect_entities(...)
    
    # 3. Extraction avec Bedrock
    bedrock = boto3.client('bedrock-runtime')
    extracted = bedrock_extract(...)
    
    # 4. Identifier entreprises concernées
    affected_companies = identify_companies(extracted)
    
    # 5. Analyser impact pour chaque entreprise (parallèle)
    impacts = []
    for ticker in affected_companies:
        impact = analyze_company_impact(ticker, extracted)
        impacts.append(impact)
    
    # 6. Générer recommandations
    recommendations = generate_recommendations(impacts)
    
    # 7. Sauvegarder résultats
    s3.put_object(..., Body=json.dumps({
        'extracted': extracted,
        'impacts': impacts,
        'recommendations': recommendations
    }))
    
    return {'statusCode': 200}
```

**Avantages** :
- ⚡ Pas de gestion d'infrastructure
- 📈 Auto-scaling
- 💰 Pay-per-use
- 🔄 Déclenchement automatique (S3 upload → Lambda)

---

## 🔍 Amazon OpenSearch Serverless - Base de Connaissances

### 🎯 Utilisation

**OpenSearch pour** :
- 📚 Indexation des documents réglementaires
- 📚 Indexation des extractions 10-K
- 🔍 Recherche sémantique (RAG pour chatbot)
- 🔍 Recherche vectorielle

### 📋 Architecture RAG (Retrieval Augmented Generation)

```
Question utilisateur
    ↓
OpenSearch (recherche vecteurs similaires)
    → Trouve documents/réponses pertinents
    ↓
Contexte récupéré
    ↓
Bedrock (génère réponse avec contexte)
    → Réponse précise et contextuelle
```

### 📋 Exemple d'Utilisation

```python
from opensearchpy import OpenSearch

# Connexion OpenSearch
client = OpenSearch(...)

# Indexer un document réglementaire
document = {
    'regulation_id': 'eu_ai_act',
    'text': regulation_text,
    'companies': ['MSFT', 'GOOGL', 'META'],
    'embedding': generate_embedding(regulation_text)  # Vector
}

client.index(index='regulations', body=document)

# Recherche pour chatbot
query_vector = generate_embedding(user_question)
results = client.search(
    index='regulations',
    body={
        'query': {
            'knn': {
                'embedding': {
                    'vector': query_vector,
                    'k': 5
                }
            }
        }
    }
)

# Utiliser résultats comme contexte pour Bedrock
context = [r['_source'] for r in results['hits']['hits']]
response = bedrock_with_context(user_question, context)
```

**Alternatives légères** :
- **ChromaDB** : Pour développement local
- **DynamoDB + S3** : Pour solution simple sans recherche vectorielle

---

## 🗃️ Amazon DynamoDB - Cache et Métadonnées

### 🎯 Utilisation

**DynamoDB pour** :
- ⚡ Cache rapide des résultats fréquents
- 📊 Métadonnées des documents
- 📝 Sessions utilisateur
- 🔄 Statut des traitements

### 📋 Exemple

```python
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('reguai-metadata')

# Stocker métadonnées
table.put_item(Item={
    'document_id': 'eu_ai_act_2024',
    'status': 'processed',
    'processed_date': '2025-01-15',
    'affected_companies': ['MSFT', 'GOOGL', 'META'],
    'risk_score': 75,
    'cache_key': 's3://.../extractions/eu_ai_act.json'
})

# Récupérer rapidement
response = table.get_item(Key={'document_id': 'eu_ai_act_2024'})
metadata = response['Item']
```

**Quand utiliser** :
- ✅ Besoin d'accès très rapide (< 10ms)
- ✅ Beaucoup de lectures
- ✅ Pas besoin de requêtes SQL complexes

---

## 📊 Amazon SageMaker Studio - Environnement de Développement

### 🎯 Utilisation

**SageMaker Studio pour** :
- 💻 Développement (Jupyter notebooks)
- 🧪 Tests et expérimentations
- 🔄 Déploiement d'applications (notre Streamlit app)
- 📦 Gestion des bibliothèques

### 🔧 Accès aux Ressources

```python
from sagemaker_studio import Project

project = Project()

# Accès S3 du projet
s3_root = project.s3.root  # s3://bucket-name/...

# Rôle IAM
iam_role = project.iam_role

# Stocker résultats
import boto3
s3 = boto3.client('s3')
s3.put_object(
    Bucket=project.s3.root.replace('s3://', '').split('/')[0],
    Key=f'{project.s3.root}/results/analysis.json',
    Body=json.dumps(results)
)
```

---

## 🔄 Workflow Complet avec Services AWS

### Scénario : Analyser un Nouveau Document

```
1. Upload Document → S3 (raw/regulations/)
   ↓
2. Lambda déclenché automatiquement
   ↓
3. Textract (si PDF scanné) OU lecture directe
   ↓
4. Comprehend (pré-filtrage)
   → Identifie parties pertinentes
   ↓
5. Vérifier cache S3
   → Si existe → utiliser cache
   → Sinon → Bedrock (Haiku extraction)
   ↓
6. Sauvegarder extraction → S3 (processed/extractions/)
   ↓
7. Identifier entreprises concernées
   ↓
8. Pour chaque entreprise:
   - Vérifier cache 10-K extrait
   - Si non → Bedrock (Haiku) extraction
   - Analyser impact → Bedrock (Sonnet)
   ↓
9. Générer recommandations → Bedrock (Sonnet)
   ↓
10. Sauvegarder résultats → S3 + DynamoDB (métadonnées)
   ↓
11. OpenSearch (indexer pour chatbot)
   ↓
12. Mise à jour Streamlit Dashboard
```

---

## 💰 Optimisation des Coûts

### 🎯 Stratégies

1. **Cache S3** : Réduction 90%+ appels Bedrock
2. **Comprehend pré-filtrage** : Réduction 70-80% tokens Bedrock
3. **Haiku pour extractions simples** : 3-5x moins cher que Sonnet
4. **Traitement sélectif** : Analyser seulement entreprises concernées (20-50 au lieu de 500)
5. **Batch processing** : Traiter plusieurs documents en parallèle

### 📊 Estimation Coûts (Exemple)

**Sans optimisation** :
- 500 entreprises × Bedrock Sonnet = ~$150
- 6 réglementations × Bedrock Sonnet = ~$12
- **Total : ~$162**

**Avec optimisations** :
- 50 entreprises concernées × Bedrock Sonnet = ~$15
- 6 réglementations × Bedrock Haiku + cache = ~$2
- Comprehend pré-filtrage = ~$1
- **Total : ~$18 (économie 89%)**

---

## 🚀 Services Optionnels (Selon Besoins)

### Amazon Athena - Analyse SQL sur S3

**Utilisation** : Requêtes SQL sur données stockées dans S3
```sql
SELECT ticker, risk_score, impact
FROM company_impacts
WHERE risk_score > 70
ORDER BY impact DESC
```

### Amazon Redshift - Data Warehouse

**Utilisation** : Si besoin d'analyses très complexes sur gros volumes

### Amazon QuickSight - Visualisations

**Utilisation** : Dashboards BI automatisés (alternative à Streamlit)

---

## ✅ Checklist Services à Utiliser

- [x] **Amazon Bedrock** : Modèles IA (Haiku, Sonnet)
- [x] **Amazon S3** : Stockage et cache
- [x] **Amazon Comprehend** : Pré-filtrage NLP
- [x] **AWS Lambda** : Orchestration (optionnel)
- [x] **Amazon SageMaker Studio** : Environnement dev
- [ ] **Amazon Textract** : Si PDF scannés (optionnel)
- [ ] **Amazon OpenSearch** : Si chatbot RAG (optionnel)
- [ ] **Amazon DynamoDB** : Si cache rapide nécessaire (optionnel)

---

## 📚 Ressources

- **Bedrock Models** : https://docs.aws.amazon.com/bedrock/
- **Comprehend** : https://docs.aws.amazon.com/comprehend/
- **S3 Best Practices** : https://docs.aws.amazon.com/s3/
- **Lambda Tutorials** : https://docs.aws.amazon.com/lambda/

---

**💡 Conseil Final** : Commencez simple (Bedrock + S3), puis ajoutez les autres services selon les besoins !

