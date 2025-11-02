"""
Helper functions for Financial Chatbot page in Streamlit app.

Ce module est spécifiquement utilisé par la page "🤖 Chatbot Financier".
Contient la logique pour l'interface conversationnelle avec Claude via Bedrock.
"""

import json
import os
from typing import List, Dict, Optional
import boto3
from botocore.exceptions import ClientError

# Singleton pattern pour le client Bedrock
_bedrock_client = None


def get_bedrock_client():
    """Retourne un client Bedrock (singleton)"""
    global _bedrock_client
    if _bedrock_client is None:
        region = os.environ.get('AWS_REGION', 'us-west-2')
        _bedrock_client = boto3.client('bedrock-runtime', region_name=region)
    return _bedrock_client


def chat_with_claude(
    messages: List[Dict[str, str]],
    model: str = "anthropic.claude-3-haiku-20240307-v1:0",
    max_tokens: int = 4000
) -> Dict:
    """
    Envoie un message à Claude via Bedrock et retourne la réponse.
    
    Args:
        messages: Liste de messages au format [{"role": "user|assistant", "content": "..."}]
        model: ID du modèle Claude à utiliser
        max_tokens: Nombre maximum de tokens dans la réponse
    
    Returns:
        Dict avec 'response', 'usage', 'error'
    """
    try:
        bedrock = get_bedrock_client()
        
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages
        }
        
        response = bedrock.invoke_model(
            modelId=model,
            body=json.dumps(body)
        )
        
        response_body = json.loads(response['body'].read())
        answer = response_body['content'][0]['text']
        usage = response_body.get('usage', {})
        
        return {
            'response': answer,
            'usage': usage,
            'error': None
        }
    except ClientError as e:
        error_code = e.response['Error']['Code']
        return {
            'response': None,
            'usage': None,
            'error': f"Erreur Bedrock ({error_code}): {str(e)}"
        }
    except Exception as e:
        return {
            'response': None,
            'usage': None,
            'error': f"Erreur: {str(e)}"
        }


def format_chat_message(role: str, content: str) -> Dict[str, str]:
    """Formate un message pour l'API Claude"""
    return {"role": role, "content": content}


def get_example_questions() -> List[str]:
    """Retourne une liste d'exemples de questions pour le chatbot"""
    return [
        "Quel est l'impact de l'EU AI Act sur les entreprises tech du S&P 500 ?",
        "Quelles entreprises sont le plus exposées aux réglementations chinoises ?",
        "Compare l'impact de deux réglementations sur le portefeuille",
        "Explique-moi pourquoi Nvidia est recommandé à la réduction"
    ]

