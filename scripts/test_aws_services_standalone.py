"""
Script standalone pour tester les services AWS utilisés par ReguAI.
Peut être exécuté directement: python scripts/test_aws_services_standalone.py
"""

import os
import json
import boto3
from pathlib import Path
from botocore.exceptions import ClientError

# Charger .env
try:
    from dotenv import load_dotenv
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(env_path)
        print("✅ .env chargé")
    else:
        print("⚠️ .env non trouvé")
except ImportError:
    print("⚠️ python-dotenv non installé")

# Configuration AWS
bucket_name = os.environ.get('S3_BUCKET_NAME')
region = os.environ.get('AWS_REGION', 'us-west-2')

print(f"\n📋 Configuration AWS:")
print(f"   • Bucket S3: {bucket_name}")
print(f"   • Région: {region}")


def test_s3():
    """Test S3 Storage"""
    print("\n🧪 TEST 1: S3 Storage")
    print("=" * 50)
    
    try:
        s3 = boto3.client('s3', region_name=region)
        
        # Test 1.1: Vérifier l'accès au bucket
        print("\n1.1 Vérification accès bucket...")
        s3.head_bucket(Bucket=bucket_name)
        print(f"   ✅ Bucket '{bucket_name}' accessible")
        
        # Test 1.2: Lister quelques objets
        print("\n1.2 Liste des objets (10 premiers)...")
        response = s3.list_objects_v2(Bucket=bucket_name, MaxKeys=10)
        if 'Contents' in response:
            for obj in response['Contents']:
                print(f"   📁 {obj['Key']} ({obj['Size']} bytes)")
        else:
            print("   ℹ️ Bucket vide")
        
        # Test 1.3: Test d'écriture (cache)
        print("\n1.3 Test d'écriture cache...")
        test_key = "test_cache/test_file.json"
        test_data = {"test": "ReguAI", "timestamp": "2025-01-01"}
        s3.put_object(
            Bucket=bucket_name,
            Key=test_key,
            Body=json.dumps(test_data).encode('utf-8'),
            ContentType='application/json'
        )
        print(f"   ✅ Écriture réussie: s3://{bucket_name}/{test_key}")
        
        # Test 1.4: Test de lecture
        print("\n1.4 Test de lecture...")
        obj = s3.get_object(Bucket=bucket_name, Key=test_key)
        read_data = json.loads(obj['Body'].read().decode('utf-8'))
        print(f"   ✅ Lecture réussie: {read_data}")
        
        # Test 1.5: Nettoyage (optionnel)
        print("\n1.5 Nettoyage test...")
        s3.delete_object(Bucket=bucket_name, Key=test_key)
        print(f"   ✅ Fichier test supprimé")
        
        print("\n✅ S3 : TOUS LES TESTS RÉUSSIS")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"\n❌ ERREUR S3 ({error_code}): {e}")
        if error_code == '403':
            print("   → Problème de permissions IAM")
        elif error_code == '404':
            print("   → Bucket non trouvé")
        return False
    except Exception as e:
        print(f"\n❌ ERREUR S3 (autre): {e}")
        return False


def test_comprehend():
    """Test Amazon Comprehend"""
    print("\n🧪 TEST 2: Amazon Comprehend")
    print("=" * 50)
    
    try:
        comprehend = boto3.client('comprehend', region_name=region)
        
        # Test 2.1: Détection de langue
        print("\n2.1 Détection de langue...")
        sample_text = "This is a regulatory document about financial compliance."
        response = comprehend.detect_dominant_language(Text=sample_text)
        language = response['Languages'][0]['LanguageCode']
        confidence = response['Languages'][0]['Score']
        print(f"   ✅ Langue détectée: {language} (confiance: {confidence:.2%})")
        
        # Test 2.2: Extraction d'entités
        print("\n2.2 Extraction d'entités...")
        entities_response = comprehend.detect_entities(
            Text=sample_text,
            LanguageCode='en'
        )
        entities = entities_response['Entities']
        if entities:
            print(f"   ✅ {len(entities)} entité(s) trouvée(s):")
            for entity in entities[:3]:
                print(f"      • {entity['Text']} ({entity['Type']}, confiance: {entity['Score']:.2%})")
        else:
            print("   ℹ️ Aucune entité trouvée")
        
        # Test 2.3: Analyse de sentiment
        print("\n2.3 Analyse de sentiment...")
        sentiment_response = comprehend.detect_sentiment(
            Text=sample_text,
            LanguageCode='en'
        )
        sentiment = sentiment_response['Sentiment']
        print(f"   ✅ Sentiment: {sentiment}")
        
        print("\n✅ Comprehend : TOUS LES TESTS RÉUSSIS")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"\n❌ ERREUR Comprehend ({error_code}): {e}")
        if error_code == 'AccessDeniedException':
            print("   → Problème de permissions IAM pour Comprehend")
        return False
    except Exception as e:
        print(f"\n❌ ERREUR Comprehend (autre): {e}")
        return False


def test_bedrock():
    """Test Amazon Bedrock (Claude)"""
    print("\n🧪 TEST 3: Amazon Bedrock (Claude)")
    print("=" * 50)
    
    try:
        bedrock = boto3.client('bedrock-runtime', region_name=region)
        bedrock_client = boto3.client('bedrock', region_name=region)
        
        # Test 3.1: Vérifier les modèles disponibles
        print("\n3.1 Vérification modèles disponibles...")
        try:
            models = bedrock_client.list_foundation_models()
            claude_models = [
                m for m in models['modelSummaries'] 
                if 'claude' in m['modelId'].lower()
            ]
            
            if claude_models:
                print(f"   ✅ {len(claude_models)} modèle(s) Claude trouvé(s):")
                for model in claude_models[:3]:
                    print(f"      • {model['modelId']}")
            else:
                print("   ⚠️ Aucun modèle Claude trouvé")
        except Exception as e:
            print(f"   ⚠️ Impossible de lister les modèles: {e}")
        
        # Test 3.2: Appel simple avec Claude Haiku
        print("\n3.2 Test appel Claude Haiku...")
        model_id = "anthropic.claude-3-haiku-20240307-v1:0"
        prompt = "What is the capital of France? Answer in one word."
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 100,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }
        
        response = bedrock.invoke_model(
            modelId=model_id,
            body=json.dumps(body)
        )
        
        response_body = json.loads(response['body'].read())
        answer = response_body['content'][0]['text']
        
        print(f"   ✅ Réponse Claude: {answer.strip()}")
        print(f"   ✅ Tokens utilisés: {response_body.get('usage', {})}")
        
        print("\n✅ Bedrock : TOUS LES TESTS RÉUSSIS")
        return True
        
    except ClientError as e:
        error_code = e.response['Error']['Code']
        print(f"\n❌ ERREUR Bedrock ({error_code}): {e}")
        if error_code == 'AccessDeniedException':
            print("   → Problème de permissions IAM pour Bedrock")
            print("   → OU modèle non activé dans la console AWS")
        elif error_code == 'ModelNotReadyException':
            print("   → Modèle non prêt ou non activé")
        return False
    except Exception as e:
        print(f"\n❌ ERREUR Bedrock (autre): {e}")
        return False


def main():
    """Exécute tous les tests"""
    results = {
        'S3': test_s3(),
        'Comprehend': test_comprehend(),
        'Bedrock': test_bedrock()
    }
    
    print("\n" + "=" * 50)
    print("📊 RÉSUMÉ DES TESTS")
    print("=" * 50)
    
    for service, success in results.items():
        status = "✅ RÉUSSI" if success else "❌ ÉCHOUÉ"
        print(f"   • {service}: {status}")
    
    print("\n💡 Pour tester dans l'application Streamlit:")
    print("   1. Lancez: streamlit run scripts/app.py")
    print("   2. Allez dans '📄 Analyse de Documents'")
    print("   3. Uploadez un document HTML/XML/PDF/TXT")
    print("   4. Cochez '☁️ Utiliser services AWS'")
    print("   5. Cliquez sur 'Analyser avec Bedrock'")


if __name__ == "__main__":
    main()

