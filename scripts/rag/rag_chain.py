"""
RAG Chain avec LangChain
Construit et gère la chain RAG complète avec Bedrock
LangChain 1.0+ compatible
"""

import os
from pathlib import Path

# Charger .env AVANT d'importer langchain_aws
# Utilise la même logique que test_aws_services.ipynb
try:
    from dotenv import load_dotenv
    
    # Trouver la racine du projet (même logique que app.py)
    # Ne dépend QUE du .env, pas des variables d'environnement système
    script_file = Path(__file__).resolve()  # scripts/rag/rag_chain.py
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

from typing import List, Dict, Any, Optional

# Imports LangChain 1.0+
try:
    from langchain_core.prompts import PromptTemplate
    from langchain_core.runnables import RunnablePassthrough
    from langchain_core.output_parsers import StrOutputParser
except ImportError:
    # Fallback pour versions anciennes
    from langchain.prompts import PromptTemplate
    RunnablePassthrough = None
    StrOutputParser = None

from langchain_aws import ChatBedrock
from scripts.rag.config import RAG_CONFIG
from scripts.rag.vector_store import RAGVectorStore


def get_bedrock_llm() -> ChatBedrock:
    """
    Crée et retourne un client ChatBedrock via LangChain
    
    Returns:
        Instance ChatBedrock configurée
    """
    region = RAG_CONFIG['aws_region']
    model_id = RAG_CONFIG['llm_model']
    
    # Vérifier que les credentials sont dans l'environnement
    access_key = os.environ.get('AWS_ACCESS_KEY_ID') or os.environ.get('AWS_ACCESS_KEY')
    secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY') or os.environ.get('AWS_SECRET_KEY')
    session_token = os.environ.get('AWS_SESSION_TOKEN')  # Pour credentials temporaires
    
    if not access_key or not secret_key:
        error_msg = "❌ Credentials AWS non trouvées. Vérifiez que AWS_ACCESS_KEY_ID et AWS_SECRET_ACCESS_KEY sont dans .env"
        raise ValueError(error_msg)
    
    # Créer LLM - LangChain/boto3 détectera automatiquement depuis os.environ
    # Les credentials sont déjà chargées dans os.environ via dotenv au début du module
    llm = ChatBedrock(
        model_id=model_id,
        region_name=region,
        model_kwargs={
            'temperature': RAG_CONFIG['temperature'],
            'max_tokens': RAG_CONFIG['max_tokens'],
        }
    )
    
    # Bedrock LLM configuré
    return llm


def create_rag_prompt_template() -> PromptTemplate:
    """
    Crée le template de prompt pour RAG
    
    Returns:
        PromptTemplate LangChain
    """
    prompt_template = """Tu es un assistant financier expert en réglementation et analyse de portefeuilles S&P 500. Tu aides les utilisateurs à comprendre les impacts réglementaires sur les entreprises.

CONTEXTE (Base de connaissances extraite de nos documents):
{context}

{question}

INSTRUCTIONS:
- Utilise les informations du contexte pour répondre de manière directe et utile
- Si un historique de conversation est fourni, utilise-le pour comprendre le contexte de la question actuelle et répondre en cohérence avec les échanges précédents
- Référence-toi aux questions/réponses précédentes si elles sont pertinentes pour la réponse actuelle
- Si le contexte contient des informations pertinentes (même partielles), SYNTHÉTISE-les pour répondre de façon constructive
- Ne dis PAS systématiquement "cette information n'est pas disponible" - utilise ce qui est disponible pour donner une réponse utile
- Si tu trouves des informations connexes (réglementations similaires, entreprises du même secteur, etc.), mentionne-les
- Cite tes sources brièvement : type ([regulation], [10k], [company_universe], [impact_analysis], [recommendations]) et nom/titre quand disponible
- Sois précis : utilise les tickers, dates, chiffres exacts du contexte
- Réponds de manière naturelle et conversationnelle, sans être trop procédural
- Structure ta réponse avec des sections courtes si nécessaire (titres courts en **gras**)

EXEMPLES DE BONNES RÉPONSES:
- "D'après [regulation] X, voici les impacts principaux..."
- "Dans notre base, nous avons des données sur les entreprises Y et Z du secteur tech qui pourraient être concernées..."
- "Cette réglementation mentionne les secteurs suivants : A, B, C. Voici ce que cela implique..."
- "Comme mentionné précédemment, [référence à conversation], voici des détails supplémentaires..."

Réponse directe et utile:"""
    
    return PromptTemplate(
        template=prompt_template,
        input_variables=["context", "question"]
    )


def create_rag_chain(vector_store: RAGVectorStore, llm: Optional[ChatBedrock] = None):
    """
    Crée la chain RAG complète avec LangChain 1.0+
    
    Args:
        vector_store: Instance RAGVectorStore initialisée
        llm: Instance ChatBedrock (si None, crée une nouvelle)
    
    Returns:
        Chain RAG configurée (compatible LangChain 1.0+)
    """
    if llm is None:
        llm = get_bedrock_llm()
    
    # Créer retriever depuis vector store
    retriever = vector_store.get_retriever(top_k=RAG_CONFIG['top_k'])
    
    # Créer prompt template
    prompt = create_rag_prompt_template()
    
    # Créer chain RAG (approche simple et robuste pour LangChain 1.0+)
    def format_docs(docs):
        """Formate les documents récupérés"""
        return "\n\n".join([doc.page_content for doc in docs])
    
    # Créer une fonction chain simple qui fonctionne avec toutes versions
    def rag_chain_function(query: str, conversation_history: list = None):
        """Fonction RAG complète avec historique de conversation"""
        # Construire un contexte enrichi à partir de l'historique
        enriched_query = query
        
        # Si on a un historique, l'inclure pour enrichir la recherche et le contexte
        if conversation_history and len(conversation_history) > 0:
            # Prendre les 3 derniers échanges (6 messages max : 3 user + 3 assistant)
            recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
            
            # Construire un résumé de l'historique pour enrichir la requête de recherche
            history_summary = []
            for msg in recent_history:
                role = msg.get('role', '')
                content = msg.get('content', '')
                if role == 'user' and content:
                    history_summary.append(f"Question précédente: {content[:200]}")
                elif role == 'assistant' and content:
                    history_summary.append(f"Réponse précédente: {content[:200]}")
            
            # Enrichir la requête avec le contexte de l'historique
            if history_summary:
                enriched_query = f"{query}\n\nContexte de conversation précédente:\n" + "\n".join(history_summary[-2:])  # Garder seulement les 2 derniers pour la recherche
        
        # 1. Rechercher documents pertinents (avec contexte enrichi)
        docs = retriever.invoke(enriched_query)
        
        # Si peu de documents trouvés, essayer une recherche plus large
        if len(docs) < 3:
            # Essayer une recherche avec des termes plus génériques
            query_terms = query.lower().split()
            if len(query_terms) > 1:
                # Prendre les mots clés principaux
                simplified_query = ' '.join(query_terms[:3])
                additional_docs = retriever.invoke(simplified_query)
                # Combiner sans doublons
                seen = set()
                for doc in docs:
                    seen.add(doc.page_content[:50])
                for doc in additional_docs:
                    if doc.page_content[:50] not in seen:
                        docs.append(doc)
                        seen.add(doc.page_content[:50])
        
        context = format_docs(docs)
        
        # 2. Construire le prompt avec historique de conversation
        conversation_context = ""
        if conversation_history and len(conversation_history) > 0:
            # Prendre les 4 derniers échanges (8 messages max)
            recent_messages = conversation_history[-8:] if len(conversation_history) > 8 else conversation_history
            
            conv_parts = []
            for msg in recent_messages:
                role = msg.get('role', '')
                content = msg.get('content', '')
                if role == 'user' and content:
                    conv_parts.append(f"Utilisateur: {content}")
                elif role == 'assistant' and content:
                    conv_parts.append(f"Assistant: {content}")
            
            if conv_parts:
                conversation_context = "\n\nHISTORIQUE DE LA CONVERSATION:\n" + "\n".join(conv_parts) + "\n\nQUESTION ACTUELLE:\n"
        
        # 3. Formater prompt avec contexte et historique
        if conversation_context:
            formatted_prompt = prompt.format(context=context, question=conversation_context + query)
        else:
            formatted_prompt = prompt.format(context=context, question=query)
        
        # 4. Appeler LLM
        try:
            response = llm.invoke(formatted_prompt)
            # Extraire contenu (format peut varier)
            if hasattr(response, 'content'):
                answer = response.content
            elif isinstance(response, str):
                answer = response
            else:
                answer = str(response)
        except Exception as e:
            return {
                'result': f"Erreur lors de l'appel LLM: {str(e)}",
                'source_documents': docs
            }
        
        return {
            'result': answer,
            'source_documents': docs
        }
    
    rag_chain = rag_chain_function
    
    # RAG Chain créée avec succès
    return rag_chain


def invoke_rag_chain(
    qa_chain,
    query: str,
    vector_store: RAGVectorStore,
    return_sources: bool = True,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Exécute la chain RAG avec une question et historique de conversation
    
    Args:
        qa_chain: Chain RAG (peut être une fonction ou un runnable)
        query: Question utilisateur
        vector_store: Vector store pour récupérer sources
        return_sources: Si True, retourne aussi les sources
        conversation_history: Liste des messages précédents [{"role": "user|assistant", "content": "..."}]
    
    Returns:
        Dictionnaire avec 'answer', 'sources', et éventuellement 'error'
    """
    try:
        # Exécuter chain (supporte fonction ou runnable)
        if callable(qa_chain) and not hasattr(qa_chain, 'invoke'):
            # C'est une fonction simple (fallback) - passer l'historique
            if conversation_history:
                result = qa_chain(query, conversation_history=conversation_history)
            else:
                result = qa_chain(query)
            answer = result.get('result', '') if isinstance(result, dict) else str(result)
            source_docs = result.get('source_documents', []) if isinstance(result, dict) else []
        else:
            # C'est un runnable LangChain (pour l'instant, pas de support historique)
            if hasattr(qa_chain, 'invoke'):
                answer = qa_chain.invoke(query)
            else:
                answer = str(qa_chain(query))
            
            # Récupérer sources séparément (avec requête enrichie si historique)
            if return_sources:
                search_query = query
                if conversation_history and len(conversation_history) > 0:
                    # Enrichir la recherche avec le dernier échange
                    last_user_msg = None
                    for msg in reversed(conversation_history):
                        if msg.get('role') == 'user':
                            last_user_msg = msg.get('content', '')
                            break
                    if last_user_msg:
                        search_query = f"{query} {last_user_msg[:100]}"
                source_docs = vector_store.search(search_query, top_k=RAG_CONFIG['top_k'])
            else:
                source_docs = []
        
        # Formater réponse
        response = {
            'answer': answer if isinstance(answer, str) else str(answer),
            'sources': [],
            'error': None
        }
        
        # Extraire sources si disponibles
        if return_sources and source_docs:
            sources = []
            for doc in source_docs:
                source_info = {
                    'type': doc.metadata.get('type', 'unknown'),
                    'content_preview': doc.page_content[:200] + '...' if len(doc.page_content) > 200 else doc.page_content,
                }
                
                # Ajouter info selon type
                if doc.metadata.get('type') == 'regulation':
                    source_info['title'] = doc.metadata.get('title', '')
                    source_info['country'] = doc.metadata.get('country', '')
                elif doc.metadata.get('type') in ['10k', 'company_universe']:
                    source_info['ticker'] = doc.metadata.get('ticker', '')
                    source_info['company_name'] = doc.metadata.get('company_name', '')
                elif doc.metadata.get('type') == 'impact_analysis':
                    source_info['regulation_id'] = doc.metadata.get('regulation_id', '')
                    source_info['regulation_title'] = doc.metadata.get('regulation_title', '')
                    source_info['total_companies_matched'] = doc.metadata.get('total_companies_matched', 0)
                elif doc.metadata.get('type') == 'recommendations':
                    source_info['ticker'] = doc.metadata.get('ticker', '')
                    source_info['company_name'] = doc.metadata.get('company_name', '')
                    source_info['recommendation_type'] = doc.metadata.get('recommendation_type', '')
                    source_info['risk_score'] = doc.metadata.get('risk_score', 0)
                
                if 'similarity_score' in doc.metadata:
                    source_info['similarity_score'] = doc.metadata['similarity_score']
                
                sources.append(source_info)
            
            response['sources'] = sources
        
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'answer': None,
            'sources': [],
            'error': f"Erreur RAG chain: {str(e)}"
        }

