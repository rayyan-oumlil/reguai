# ☁️ Configuration AWS pour ReguAI

Ce guide explique comment configurer les services AWS pour utiliser au maximum les capacités d'Amazon (S3, Comprehend, DynamoDB, Bedrock).

## 🎯 Services AWS Utilisés

1. **Amazon Bedrock** : Extraction et analyse avec Claude (Haiku, Sonnet)
2. **Amazon S3** : Cache des extractions et stockage des documents
3. **Amazon Comprehend** : Pré-filtrage intelligent pour réduire les coûts Bedrock
4. **Amazon DynamoDB** : Métadonnées des extractions (optionnel)
5. **Amazon Textract** : Extraction de texte depuis PDF scannés

## 📋 Configuration

### Option A : Configuration Automatique (SageMaker Studio)

Si vous travaillez dans SageMaker Studio, le bucket S3 est détecté automatiquement :

1. **Exécutez le notebook** `notebooks/utils/detect_s3_from_sagemaker.ipynb`
2. Le notebook détectera automatiquement votre bucket S3 depuis le projet
3. Il créera un fichier `.env` avec la configuration

### Option B : Configuration Manuelle

#### 1. Variables d'Environnement

Créez un fichier `.env` à la racine du projet ou configurez les variables d'environnement :

```bash
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=votre_access_key
AWS_SECRET_ACCESS_KEY=votre_secret_key

# S3 Configuration (optionnel mais recommandé)
S3_BUCKET_NAME=datathon-reguai
# ou
AWS_S3_BUCKET=datathon-reguai
```

### 2. Créer un Bucket S3

```bash
aws s3 mb s3://datathon-reguai --region us-east-1
```

Structure recommandée dans le bucket :
```
s3://datathon-reguai/
├── raw/
│   └── regulations/          # Documents originaux
├── processed/
│   └── extractions/          # Cache des extractions Bedrock
└── knowledge_base/           # Pour RAG (futur)
```

### 3. Créer une Table DynamoDB (Optionnel)

```bash
aws dynamodb create-table \
    --table-name reguai-extractions-metadata \
    --attribute-definitions \
        AttributeName=document_id,AttributeType=S \
    --key-schema \
        AttributeName=document_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region us-east-1
```

### 4. Permissions IAM Requises

Votre rôle/utilisateur AWS doit avoir les permissions suivantes :

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel",
                "bedrock:ListFoundationModels"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject",
                "s3:ListBucket"
            ],
            "Resource": [
                "arn:aws:s3:::datathon-reguai/*",
                "arn:aws:s3:::datathon-reguai"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "comprehend:DetectEntities",
                "comprehend:DetectSentiment",
                "comprehend:DetectKeyPhrases"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "textract:DetectDocumentText",
                "textract:AnalyzeDocument"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:Query"
            ],
            "Resource": "arn:aws:dynamodb:*:*:table/reguai-extractions-metadata"
        }
    ]
}
```

## 🚀 Utilisation

### Avec Services AWS

L'application utilisera automatiquement les services AWS si :
1. Les variables d'environnement sont configurées (`S3_BUCKET_NAME` ou `AWS_S3_BUCKET`)
2. Les credentials AWS sont valides

### Sans Services AWS (Fallback)

Si AWS n'est pas configuré, l'application fonctionnera quand même avec :
- Cache local dans `data/generated/extracted_directives/`
- Bedrock uniquement (sans Comprehend pré-filtrage)
- Pas de stockage S3 ni DynamoDB

## 💰 Optimisation des Coûts

### Stratégie avec Comprehend

1. **Document long (> 10,000 caractères)** :
   - Comprehend analyse le document ($0.0001/1000 chars)
   - Identifie les parties pertinentes
   - Réduit de 70-80% les tokens envoyés à Bedrock
   - **Économie** : ~$0.002 par document au lieu de $0.01

2. **Cache S3** :
   - Première extraction : coût Bedrock complet
   - Extractions suivantes : 0$ (depuis S3)
   - **Économie** : 90%+ pour documents ré-analysés

### Exemple de Coûts

**Sans optimisation** (100 documents, 50K chars chacun) :
- Bedrock : 100 × $0.01 = **$1.00**

**Avec optimisation** :
- Comprehend : 100 × $0.0005 = $0.05
- Bedrock (20% tokens) : 100 × $0.002 = $0.20
- **Total** : **$0.25** (75% d'économie)

## 🔍 Vérification

### Tester la Configuration

```python
from scripts.aws_services_helper import get_aws_helper

helper = get_aws_helper()
print(f"S3 Bucket: {helper.s3_bucket}")
print(f"Region: {helper.region_name}")
print(f"DynamoDB Available: {helper.dynamodb_available}")
```

### Lister les Extractions S3

```python
from scripts.aws_services_helper import get_aws_helper

helper = get_aws_helper()
extractions = helper.list_s3_extractions()
print(f"Found {len(extractions)} extractions in S3")
```

## 📝 Notes

- **S3 Bucket** : Si non configuré, l'application utilise le cache local
- **Comprehend** : Activé automatiquement pour documents > 10K caractères
- **DynamoDB** : Optionnel, utilisé seulement si la table existe
- **Bedrock** : Requis pour l'extraction (fonctionne sans autres services)

## 🐛 Dépannage

### Erreur "NoSuchBucket"
- Vérifiez que le bucket S3 existe
- Vérifiez les permissions IAM
- Vérifiez la région (doit correspondre)

### Erreur "AccessDenied"
- Vérifiez les credentials AWS
- Vérifiez les permissions IAM
- Utilisez `aws configure` pour reconfigurer

### Comprehend ne réduit pas les tokens
- Vérifiez que le document fait > 10K caractères
- Les documents courts ne sont pas pré-filtrés (pas nécessaire)

