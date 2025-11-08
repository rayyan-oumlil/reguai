"""
Gestion des Embeddings avec AWS Bedrock via LangChain
"""

import os
from pathlib import Path

# Charger .env AVANT d'importer langchain_aws
# Utilise la même logique que test_aws_services.ipynb
try:
    from dotenv import load_dotenv
    
    # Trouver la racine du projet (même logique que app.py)
    # Ne dépend QUE du .env, pas des variables d'environnement système
    script_file = Path(__file__).resolve()  # scripts/rag/embeddings.py
    project_root = script_file.parent.parent.parent  # Racine du projet
    env_path = project_root / '.env'
    
    # Si .env n'existe pas à la racine, essayer depuis cwd
    if not env_path.exists():
        env_path = Path.cwd() / '.env'
        # Si on est dans scripts/ ou notebooks/, remonter
        if not env_path.exists():
            current = Path.cwd()
            if 'scripts' in str(current) or 'notebooks' in str(current):
                env_path = current.parent / '.env'
    
    if env_path.exists():
        load_dotenv(env_path, override=True)  # override=True pour utiliser UNIQUEMENT .env
        pass  # .env chargé
    # .env non trouvé - ignoré
except ImportError:
    pass  # python-dotenv non installé
except Exception as e:
    pass  # Erreur chargement .env

from langchain_aws import BedrockEmbeddings
from scripts.rag.config import RAG_CONFIG


def get_bedrock_embeddings() -> BedrockEmbeddings:
    """
    Crée et retourne un client BedrockEmbeddings via LangChain
    
    Returns:
        Instance BedrockEmbeddings configurée
    """
    region = RAG_CONFIG['aws_region']
    model_id = RAG_CONFIG['embedding_model']
    
    # Vérifier que les credentials sont dans l'environnement
    access_key = os.environ.get('AWS_ACCESS_KEY_ID') or os.environ.get('AWS_ACCESS_KEY')
    secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY') or os.environ.get('AWS_SECRET_KEY')
    session_token = os.environ.get('AWS_SESSION_TOKEN')  # Pour credentials temporaires
    
    if not access_key or not secret_key:
        error_msg = "❌ Credentials AWS non trouvées. Vérifiez que AWS_ACCESS_KEY_ID et AWS_SECRET_ACCESS_KEY sont dans .env"
        raise ValueError(error_msg)
    
    # Créer embeddings - LangChain/boto3 détectera automatiquement depuis os.environ
    # Les credentials sont déjà chargées dans os.environ via dotenv au début du module
    embeddings = BedrockEmbeddings(
        model_id=model_id,
        region_name=region
    )
    
    # Bedrock Embeddings configuré
    return embeddings


# Singleton pattern pour éviter recréer le client
_embeddings_instance = None


def get_embeddings_instance() -> BedrockEmbeddings:
    """
    Retourne l'instance singleton de BedrockEmbeddings
    
    Returns:
        Instance BedrockEmbeddings (singleton)
    """
    global _embeddings_instance
    
    if _embeddings_instance is None:
        _embeddings_instance = get_bedrock_embeddings()
    
    return _embeddings_instance

