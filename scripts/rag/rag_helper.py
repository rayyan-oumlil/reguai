"""
Helper principal RAG pour intégration Streamlit
Point d'entrée principal pour utiliser le système RAG
"""

import os
from pathlib import Path
from typing import Optional

# Charger .env AVANT d'importer les autres modules RAG
# Utilise la même logique que test_aws_services.ipynb
load_dotenv_func = None
env_path: Optional[Path] = None

try:
    from dotenv import load_dotenv
    load_dotenv_func = load_dotenv
    
    # Essayer plusieurs chemins possibles pour trouver .env
    # 1. Depuis le module (scripts/rag/)
    env_path = Path(__file__).parent.parent.parent / '.env'
    
    # 2. Depuis le répertoire de travail actuel
    if not env_path.exists():
        env_path = Path.cwd() / '.env'
    
    # 3. Remonter depuis cwd si on est dans un sous-répertoire
    if not env_path.exists():
        current = Path.cwd()
        if 'scripts' in str(current) or 'notebooks' in str(current):
            env_path = current.parent / '.env'
        else:
            # Dernier essai : depuis scripts/rag -> racine
            env_path = Path(__file__).parent.parent.parent / '.env'
    
    if env_path and env_path.exists() and load_dotenv_func:
        load_dotenv_func(env_path)
        pass  # .env chargé
    # .env non trouvé - ignoré
except ImportError:
    pass  # python-dotenv non installé
except Exception as e:
    pass  # Erreur chargement .env

from typing import List, Dict, Any

# Import Document from langchain (compatible versions)
try:
    from langchain_core.documents import Document
except ImportError:
    try:
        from langchain.documents import Document  # type: ignore
    except ImportError:
        from langchain.schema import Document  # type: ignore

from scripts.rag.config import DATA_PATHS, RAG_CONFIG
from scripts.rag.data_loader import (
    load_regulatory_extractions,
    load_10k_extractions,
    load_company_universe,
    load_impact_analysis,
    load_recommendations,
    create_documents_from_data
)
from scripts.rag.vector_store import RAGVectorStore
from scripts.rag.rag_chain import create_rag_chain, invoke_rag_chain, get_bedrock_llm
from scripts.rag.embeddings import get_embeddings_instance


# Instance globale du système RAG (singleton)
_rag_system = None
_vector_store = None
_qa_chain = None


def initialize_rag_system(
    use_cache: bool = True,
    tenk_limit: Optional[int] = 100  # Limiter 10-K pour MVP (100 au lieu de 500)
) -> Dict[str, Any]:
    """
    Initialise le système RAG complet
    
    Args:
        use_cache: Si True, essaie de charger depuis cache
        tenk_limit: Limite le nombre de fichiers 10-K à charger (None = tous)
    
    Returns:
        Dictionnaire avec statut et infos
    """
    global _rag_system, _vector_store, _qa_chain
    
    try:
        print("🚀 Initialisation système RAG...")
        
        # Recharger .env explicitement avant vérification credentials
        # Utilise la même logique que app.py pour trouver la racine du projet
        local_env_path: Optional[Path] = None
        try:
            from dotenv import load_dotenv
            
            # Trouver la racine du projet (où se trouve .env)
            script_file = Path(__file__).resolve()  # scripts/rag/rag_helper.py
            project_root = script_file.parent.parent.parent  # Racine du projet
            local_env_path = project_root / '.env'
            
            # Si .env n'existe pas à la racine, essayer depuis cwd
            if not local_env_path.exists():
                local_env_path = Path.cwd() / '.env'
                # Si on est dans scripts/ ou notebooks/, remonter
                if not local_env_path.exists():
                    current = Path.cwd()
                    if 'scripts' in str(current) or 'notebooks' in str(current):
                        local_env_path = current.parent / '.env'
            
            if local_env_path and local_env_path.exists():
                load_dotenv(local_env_path, override=True)  # override=True pour forcer le rechargement
                pass  # .env rechargé
            # .env non trouvé - ignoré
        except Exception as e:
            pass  # Erreur rechargement .env
        
        # Vérifier credentials AWS après rechargement
        # Essayer plusieurs fois et avec plusieurs noms de variables
        # NOTE: Gérer le BOM UTF-8 (\ufeff) qui peut être présent au début du fichier .env
        access_key = (
            os.environ.get('AWS_ACCESS_KEY_ID') or 
            os.environ.get('AWS_ACCESS_KEY') or
            os.environ.get('\ufeffAWS_ACCESS_KEY_ID') or  # BOM UTF-8
            os.environ.get('\ufeffAWS_ACCESS_KEY')
        )
        secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY') or os.environ.get('AWS_SECRET_KEY')
        
        # Si pas trouvé, forcer un dernier rechargement
        if not access_key or not secret_key:
            # Credentials non trouvées - tentative de rechargement
            if load_dotenv_func and env_path is not None and env_path.exists():
                load_dotenv_func(env_path, override=True)
            # Gérer aussi le BOM UTF-8 après rechargement
            access_key = (
                os.environ.get('AWS_ACCESS_KEY_ID') or 
                os.environ.get('AWS_ACCESS_KEY') or
                os.environ.get('\ufeffAWS_ACCESS_KEY_ID') or  # BOM UTF-8
                os.environ.get('\ufeffAWS_ACCESS_KEY')
            )
            secret_key = os.environ.get('AWS_SECRET_ACCESS_KEY') or os.environ.get('AWS_SECRET_KEY')
        
        if not access_key or not secret_key:
            print(f"🔍 Debug - Variables d'environnement après rechargement:")
            print(f"   AWS_ACCESS_KEY_ID: {'✅' if os.environ.get('AWS_ACCESS_KEY_ID') else '❌'}")
            print(f"   \\ufeffAWS_ACCESS_KEY_ID (BOM): {'✅' if os.environ.get('\ufeffAWS_ACCESS_KEY_ID') else '❌'}")
            print(f"   AWS_ACCESS_KEY: {'✅' if os.environ.get('AWS_ACCESS_KEY') else '❌'}")
            print(f"   AWS_SECRET_ACCESS_KEY: {'✅' if os.environ.get('AWS_SECRET_ACCESS_KEY') else '❌'}")
            print(f"   AWS_SECRET_KEY: {'✅' if os.environ.get('AWS_SECRET_KEY') else '❌'}")
            print(f"   AWS_SESSION_TOKEN: {'✅' if os.environ.get('AWS_SESSION_TOKEN') else '❌'}")
            print(f"   Toutes variables AWS: {[k for k in os.environ.keys() if 'AWS' in k]}")
            
            # Si on trouve la variable avec BOM, la renommer
            bom_key = '\ufeffAWS_ACCESS_KEY_ID'
            if bom_key in os.environ and 'AWS_ACCESS_KEY_ID' not in os.environ:
                # Détection BOM UTF-8 - Correction automatique
                os.environ['AWS_ACCESS_KEY_ID'] = os.environ[bom_key]
                access_key = os.environ['AWS_ACCESS_KEY_ID']
            
            # Lire directement le fichier pour debug
            try:
                if env_path is not None and env_path.exists():
                    with open(env_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        aws_lines = [l.strip() for l in lines if 'AWS' in l and not l.strip().startswith('#')]
                        # Lignes AWS dans .env détectées
                elif local_env_path is not None and local_env_path.exists():
                    with open(local_env_path, 'r', encoding='utf-8') as f:
                        lines = f.readlines()
                        aws_lines = [l.strip() for l in lines if 'AWS' in l and not l.strip().startswith('#')]
                        # Lignes AWS dans .env détectées
            except:
                pass
            
            return {
                'success': False,
                'error': 'Credentials AWS non trouvées dans .env (AWS_ACCESS_KEY_ID et AWS_SECRET_ACCESS_KEY requis)'
            }
        
        # 1. Créer vector store
        vector_store = RAGVectorStore()
        
        # 2. Essayer de charger depuis cache
        if use_cache:
            if vector_store.load_from_cache():
                print("✅ Vector store chargé depuis cache")
                _vector_store = vector_store
                
                # Créer chain RAG
                _qa_chain = create_rag_chain(vector_store)
                _rag_system = {
                    'vector_store': vector_store,
                    'qa_chain': _qa_chain,
                    'initialized': True
                }
                
                return {
                    'success': True,
                    'from_cache': True,
                    'message': 'Système RAG initialisé depuis cache'
                }
        
        # 3. Charger données si pas de cache
        print("📂 Chargement des données...")
        regulatory_data = load_regulatory_extractions()
        tenk_data = load_10k_extractions(limit=tenk_limit if tenk_limit is not None else None)
        company_universe = load_company_universe()
        impact_analysis = load_impact_analysis()
        recommendations = load_recommendations()
        
        print("📝 Création des documents...")
        documents = create_documents_from_data(
            regulatory_data=regulatory_data,
            tenk_data=tenk_data,
            company_universe=company_universe,
            impact_analysis=impact_analysis,
            recommendations=recommendations
        )
        
        if not documents:
            return {
                'success': False,
                'error': 'Aucun document à indexer'
            }
        
        print("🔨 Indexation dans vector store (peut prendre quelques minutes)...")
        vector_store.create_from_documents(documents)
        
        # Sauvegarder cache
        if use_cache:
            vector_store.save_to_cache()
        
        # Créer chain RAG
        _qa_chain = create_rag_chain(vector_store)
        
        # Sauvegarder instances
        _vector_store = vector_store
        _rag_system = {
            'vector_store': vector_store,
            'qa_chain': _qa_chain,
            'initialized': True
        }
        
        print("✅ Système RAG initialisé avec succès!")
        
        return {
            'success': True,
            'from_cache': False,
            'num_documents': len(documents),
            'message': f'Système RAG initialisé avec {len(documents)} documents'
        }
        
    except ValueError as e:
        # Erreur de credentials ou configuration
        print(f"❌ Erreur configuration RAG: {e}")
        return {
            'success': False,
            'error': str(e),
            'suggestion': 'Vérifiez que vos credentials AWS dans .env sont valides et non expirées'
        }
    except Exception as e:
        import traceback
        print(f"❌ Erreur initialisation RAG: {e}")
        traceback.print_exc()
        return {
            'success': False,
            'error': str(e)
        }


def _is_general_greeting(query: str) -> bool:
    """
    Détecte si la requête est une salutation ou question générale (pas besoin de RAG)
    """
    query_lower = query.lower().strip()
    greetings = ['hello', 'bonjour', 'salut', 'hi', 'hey', 'coucou', 'bonsoir']
    simple_questions = ['comment ça va', 'ça va', 'help', 'aide', '?']
    
    # Vérifier salutations simples
    if any(query_lower == g or query_lower.startswith(g + ' ') for g in greetings):
        return True
    
    # Vérifier questions très courtes sans contexte
    if len(query_lower.split()) <= 2 and any(q in query_lower for q in simple_questions):
        return True
    
    return False


def chat_with_rag(
    query: str,
    return_sources: bool = True,
    conversation_history: Optional[List[Dict[str, str]]] = None
) -> Dict[str, Any]:
    """
    Chat avec RAG - Point d'entrée principal avec historique de conversation
    
    Args:
        query: Question utilisateur
        return_sources: Si True, retourne sources utilisées
        conversation_history: Liste des messages précédents [{"role": "user|assistant", "content": "..."}]
    
    Returns:
        Dictionnaire avec 'answer', 'sources', 'error'
    """
    global _qa_chain, _rag_system
    
    # Détecter salutations/questions générales (pas besoin de RAG)
    if _is_general_greeting(query):
        return {
            'answer': """Bonjour ! 👋

Je suis votre assistant financier spécialisé dans l'analyse réglementaire et les portefeuilles S&P 500. Je peux vous aider à :

📋 **Analyser les réglementations** - Comprendre les impacts des nouvelles lois (EU AI Act, Inflation Reduction Act, etc.)

🏢 **Explorer les entreprises** - Informations sur les entreprises du S&P 500 et leur exposition réglementaire

💡 **Évaluer les impacts** - Identifier quelles entreprises sont concernées par quelles réglementations

Posez-moi une question spécifique pour commencer ! Par exemple :
- "Quel est l'impact de l'EU AI Act sur les entreprises tech ?"
- "Quelles entreprises sont exposées aux réglementations chinoises ?" """,
            'sources': [],
            'error': None
        }
    
    # Vérifier initialisation
    if _rag_system is None or not _rag_system.get('initialized'):
        return {
            'answer': None,
            'sources': [],
            'error': 'Système RAG non initialisé. Appelez initialize_rag_system() d\'abord.'
        }
    
    qa_chain = _rag_system['qa_chain']
    vector_store = _rag_system['vector_store']
    
    # Exécuter RAG avec historique
    return invoke_rag_chain(qa_chain, query, vector_store, return_sources=return_sources, conversation_history=conversation_history)


def search_rag_context(
    query: str,
    top_k: Optional[int] = None
) -> List[Document]:
    """
    Recherche dans le vector store sans générer de réponse
    
    Args:
        query: Question/requête
        top_k: Nombre de résultats
    
    Returns:
        Liste de Documents similaires
    """
    global _vector_store
    
    if _vector_store is None:
        return []
    
    # Use default top_k if None provided
    if top_k is None:
        top_k = 5  # Default value
    
    return _vector_store.search(query, top_k=top_k)


def get_rag_stats() -> Dict[str, Any]:
    """
    Retourne des statistiques sur le système RAG
    
    Returns:
        Dictionnaire avec stats
    """
    global _rag_system, _vector_store
    
    stats = {
        'initialized': _rag_system is not None and _rag_system.get('initialized', False),
        'cache_exists': DATA_PATHS['vector_store_cache'].exists(),
    }
    
    if _vector_store:
        stats.update(_vector_store.get_stats())
    
    return stats


def reset_rag_system() -> None:
    """
    Réinitialise le système RAG (utile pour tests ou rechargement)
    """
    global _rag_system, _vector_store, _qa_chain
    
    _rag_system = None
    _vector_store = None
    _qa_chain = None
    
    print("🔄 Système RAG réinitialisé")

