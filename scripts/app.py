# 🚀 ReguAI - Regulatory Intelligence Assistant
# Datathon PolyFinances 2025
# Application Streamlit principale

# Fix OpenMP initialization conflict on macOS
# Must be set before importing any libraries that use OpenMP (numpy, etc.)
import os
os.environ.setdefault('KMP_DUPLICATE_LIB_OK', 'TRUE')

# Fix import paths for Streamlit
import sys
from pathlib import Path

# Ensure current directory is in Python path
if __name__ != '__main__':
    # When run via streamlit run scripts/app.py, add parent directory to path
    script_file = Path(__file__).resolve()
    parent_dir = script_file.parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import json
from typing import Dict, List

# Charger la configuration depuis .env (local) ou st.secrets (Streamlit Cloud)
# IMPORTANT: Charger AVANT les imports RAG pour que les credentials soient disponibles
# Priorité en LOCAL: .env (override tout) > variables d'environnement système
# Priorité en CLOUD: st.secrets > variables d'environnement système

# D'abord, vérifier si on est en local (fichier .env existe)
# Si .env existe, on l'utilise (priorité absolue pour le développement local)
script_file = Path(__file__).resolve()  # scripts/app.py
project_root = script_file.parent.parent  # Racine du projet
env_path = project_root / '.env'

# Si .env n'existe pas à la racine, essayer depuis cwd
if not env_path.exists():
    env_path = Path.cwd() / '.env'
    # Si on est dans scripts/, remonter
    if not env_path.exists() and 'scripts' in str(Path.cwd()):
        env_path = Path.cwd().parent / '.env'

is_local_env = env_path.exists()

# Si pas de .env local, essayer st.secrets (Streamlit Cloud)
if not is_local_env:
    if hasattr(st, 'secrets') and st.secrets:
        try:
            secrets_dict = dict(st.secrets)
            if 'AWS_ACCESS_KEY_ID' in secrets_dict:
                os.environ['AWS_ACCESS_KEY_ID'] = str(secrets_dict['AWS_ACCESS_KEY_ID'])
            if 'AWS_SECRET_ACCESS_KEY' in secrets_dict:
                os.environ['AWS_SECRET_ACCESS_KEY'] = str(secrets_dict['AWS_SECRET_ACCESS_KEY'])
            if 'AWS_REGION' in secrets_dict:
                os.environ['AWS_REGION'] = str(secrets_dict['AWS_REGION'])
            if 'AWS_DEFAULT_REGION' in secrets_dict:
                os.environ['AWS_DEFAULT_REGION'] = str(secrets_dict['AWS_DEFAULT_REGION'])
            if 'S3_BUCKET_NAME' in secrets_dict:
                os.environ['S3_BUCKET_NAME'] = str(secrets_dict['S3_BUCKET_NAME'])
            if 'AWS_SESSION_TOKEN' in secrets_dict:
                os.environ['AWS_SESSION_TOKEN'] = str(secrets_dict['AWS_SESSION_TOKEN'])
            print("✅ Credentials AWS chargés depuis Streamlit Secrets (Cloud)")
        except Exception as e:
            print(f"⚠️ Erreur chargement Streamlit Secrets: {e}")

# Charger depuis .env (développement local) - prend le dessus si présent
# Le .env sera ignoré si on est sur Streamlit Cloud (fichier n'existe pas)
try:
    from dotenv import load_dotenv
    
    if is_local_env:
        # Charger le .env et OVERRIDE toutes les variables existantes
        # pour être sûr qu'on utilise uniquement le .env
        load_dotenv(env_path, override=True)
        
        # Vérifier que les credentials sont bien chargées dans os.environ
        # Gérer le BOM UTF-8 qui peut être présent au début du fichier .env
        access_key = (
            os.environ.get('AWS_ACCESS_KEY_ID') or 
            os.environ.get('AWS_ACCESS_KEY') or
            os.environ.get('\ufeffAWS_ACCESS_KEY_ID') or  # BOM UTF-8
            os.environ.get('\ufeffAWS_ACCESS_KEY')
        )
        has_access = bool(access_key)
        has_secret = bool(os.environ.get('AWS_SECRET_ACCESS_KEY') or os.environ.get('AWS_SECRET_KEY'))
        has_token = bool(os.environ.get('AWS_SESSION_TOKEN'))
        
        # Si trouvé avec BOM, corriger automatiquement
        if not has_access:
            bom_key = '\ufeffAWS_ACCESS_KEY_ID'
            if bom_key in os.environ:
                os.environ['AWS_ACCESS_KEY_ID'] = os.environ[bom_key]
                access_key = os.environ['AWS_ACCESS_KEY_ID']
                has_access = True
        
        # Si pas trouvé, recharger une fois de plus (au cas où Streamlit aurait modifié os.environ)
        if not has_access or not has_secret:
            load_dotenv(env_path, override=True)
            # Réessayer avec gestion BOM
            access_key = (
                os.environ.get('AWS_ACCESS_KEY_ID') or 
                os.environ.get('AWS_ACCESS_KEY') or
                os.environ.get('\ufeffAWS_ACCESS_KEY_ID') or
                os.environ.get('\ufeffAWS_ACCESS_KEY')
            )
            has_access = bool(access_key)
            # Corriger si BOM présent
            if not has_access:
                bom_key = '\ufeffAWS_ACCESS_KEY_ID'
                if bom_key in os.environ:
                    os.environ['AWS_ACCESS_KEY_ID'] = os.environ[bom_key]
                    access_key = os.environ['AWS_ACCESS_KEY_ID']
                    has_access = True
            has_secret = bool(os.environ.get('AWS_SECRET_ACCESS_KEY') or os.environ.get('AWS_SECRET_KEY'))
            has_token = bool(os.environ.get('AWS_SESSION_TOKEN'))
        
            if has_access and has_secret:
                # .env chargé avec succès
                pass
    else:
        print(f"⚠️ .env non trouvé (cherché: {env_path.absolute()})")
except ImportError:
    print("⚠️ python-dotenv non installé")
except Exception as e:
    print(f"⚠️ Erreur chargement .env: {e}")
    import traceback
    traceback.print_exc()

# Import helpers
from scripts.helpers.document_analysis_helper import (
    extract_from_uploaded_file,
    extract_from_local_file,
    load_existing_extractions,
    generate_filename_from_extraction,
    delete_extraction,
    get_all_documents_with_status,
    save_uploaded_file
)
from scripts.helpers.dashboard_helper import (
    load_company_universe,
    company_universe_to_dataframes,
    render_dashboard_kpis,
    render_sector_treemap,
    render_composition_charts,
    render_performance_table,
    render_composition_table
)
# Chatbot helper functions (merged from chatbot_helper.py)
import boto3
from botocore.exceptions import ClientError

# Singleton pattern pour le client Bedrock (chatbot fallback)
_bedrock_chatbot_client = None

def get_bedrock_chatbot_client():
    """Retourne un client Bedrock pour chatbot simple (singleton)"""
    global _bedrock_chatbot_client
    if _bedrock_chatbot_client is None:
        region = os.environ.get('AWS_REGION', 'us-west-2')
        _bedrock_chatbot_client = boto3.client('bedrock-runtime', region_name=region)
    return _bedrock_chatbot_client

def chat_with_claude(
    messages: List[Dict[str, str]],
    model: str = "anthropic.claude-3-haiku-20240307-v1:0",
    max_tokens: int = 4000
) -> Dict:
    """
    Envoie un message à Claude via Bedrock et retourne la réponse (fallback sans RAG)
    
    Args:
        messages: Liste de messages au format [{"role": "user|assistant", "content": "..."}]
        model: ID du modèle Claude à utiliser
        max_tokens: Nombre maximum de tokens dans la réponse
    
    Returns:
        Dict avec 'response', 'usage', 'error'
    """
    try:
        bedrock = get_bedrock_chatbot_client()
        
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
from scripts.rag import (
    initialize_rag_system,
    chat_with_rag,
    get_rag_stats
)
from scripts.helpers.impact_helper import (
    load_impact_results,
    load_recommendations,
    impact_results_to_dataframes,
    render_impact_summary,
    render_tier1_fcf_chart,
    render_tier2_risk_chart,
    render_tier3_price_impact_chart,
    render_final_risk_distribution,
    render_companies_table,
    render_recommendations_table,
    render_regulation_selector,
    render_company_details_table,
    # Signal helper functions (merged from signal_helper.py)
    generate_signals_for_analysis,
    signals_to_dataframe,
    render_signals_summary,
    render_signals_distribution,
    render_component_signals_chart,
    render_signals_table,
    render_signal_details
)
# streamlit_impact_runner functions not used - removed

# Configuration de la page
st.set_page_config(
    page_title="ReguAI - Regulatory Intelligence Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme mode - Always dark (no toggle)
st.session_state.theme_mode = 'dark'


# CSS personnalisé avec support du thème
theme_css = """
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #10b981;
    }
"""

# Apply dark theme CSS (always dark mode)
theme_css += """
    .main-header { color: #e8eaf6; }
    .sub-header { color: #b0bec5; }
    .metric-card { background-color: #1a2332; color: #e8eaf6; }
"""

st.markdown(theme_css, unsafe_allow_html=True)


# Initialisation de session state
if 'data_loaded' not in st.session_state:
    st.session_state.data_loaded = False
if 'composition_sp500' not in st.session_state:
    st.session_state.composition_sp500 = None
if 'stocks_performance' not in st.session_state:
    st.session_state.stocks_performance = None

# Track running extractions
if 'running_extractions' not in st.session_state:
    st.session_state.running_extractions = {}  # {filename: {'status': 'processing', 'start_time': datetime}}
if 'last_refresh' not in st.session_state:
    st.session_state.last_refresh = None


def _check_running_extractions():
    """Check if any running extractions have completed by verifying if extraction files exist"""
    if not st.session_state.running_extractions:
        return False
    
    # Check all documents to see if any extractions completed
    all_extractions = load_existing_extractions()
    extraction_filenames = {ext['filename']: ext for ext in all_extractions}
    
    completed = []
    for filename, info in list(st.session_state.running_extractions.items()):
        # Check if extraction now exists for this document
        # Match by checking if filename appears in any extraction
        for ext_filename, ext_data in extraction_filenames.items():
            # Try matching various ways
            base_filename = Path(filename).stem
            if (filename in ext_filename or 
                ext_filename in filename or 
                base_filename in ext_filename):
                # Extraction completed!
                completed.append(filename)
                break
    
    # Remove completed from running list
    for filename in completed:
        del st.session_state.running_extractions[filename]
    
    # Auto-refresh if something completed
    if completed:
        st.session_state.last_refresh = datetime.now()
        return True
    return False


def _display_extraction_results(result: dict):
    """Helper function to display extraction results in a nice format"""
    if result.get('processing_status') != 'completed':
        return
    
    extracted_info = result.get('extracted_info', {})
    
    # Header avec métadonnées
    col1, col2, col3 = st.columns(3)
    with col1:
        category = result.get('category', 'N/A')
        if isinstance(category, str):
            category = category.split('\n')[0].replace('Category: ', '')
        st.metric("Catégorie", category)
    with col2:
        confidence = result.get('legalbert_confidence', 0.0)
        st.metric("Confiance LegalBERT", f"{confidence:.1%}")
    with col3:
        st.metric("Document ID", result.get('document_id', 'N/A'))
    
    st.divider()
    
    # Informations extraites
    st.subheader("📋 Informations Extraites")
    
    # Titre, Pays, Date
    if extracted_info.get('title'):
        st.markdown(f"**📌 Titre:** {extracted_info['title']}")
    
    cols_info = st.columns(2)
    with cols_info[0]:
        if extracted_info.get('country'):
            st.markdown(f"**🌍 Pays/Région:** {extracted_info['country']}")
    with cols_info[1]:
        if extracted_info.get('effective_date'):
            st.markdown(f"**📅 Date d'effet:** {extracted_info['effective_date']}")
    
    # Secteurs affectés
    if extracted_info.get('affected_sectors'):
        st.subheader("🏢 Secteurs Affectés")
        sectors = extracted_info['affected_sectors']
        if isinstance(sectors, list):
            for i, sector in enumerate(sectors, 1):
                st.markdown(f"{i}. {sector}")
        else:
            st.markdown(sectors)
    
    # Exigences clés
    if extracted_info.get('key_requirements'):
        st.subheader("📝 Exigences Clés")
        requirements = extracted_info['key_requirements']
        if isinstance(requirements, list):
            for i, req in enumerate(requirements, 1):
                st.markdown(f"{i}. {req}")
        else:
            st.markdown(requirements)
    
    # Pénalités
    if extracted_info.get('penalties'):
        st.subheader("⚖️ Pénalités")
        penalties = extracted_info['penalties']
        if isinstance(penalties, list):
            for i, penalty in enumerate(penalties, 1):
                st.markdown(f"{i}. {penalty}")
        else:
            st.markdown(penalties)
    
    # JSON brut (optionnel, dans expander)
    with st.expander("🔍 Voir les données JSON brutes"):
        st.json(result)

# Sidebar - Logo ReguAI en haut
# Logo depuis doc/Logo.png
logo_path = Path(__file__).parent.parent / 'doc' / 'Logo.png'
if logo_path.exists():
    # Logo personnalisé trouvé - même largeur que les boutons du menu, légèrement cropé en haut/bas
    st.sidebar.markdown("""
        <style>
        .logo-container {
            width: 100%;
            height: 80px;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0;
            padding: 0;
        }
        .logo-container img {
            width: 100%;
            height: 150%;
            object-fit: cover;
            object-position: center;
        }
        </style>
        <div class='logo-container' style='margin-top: 0; padding-top: 0;'>
    """, unsafe_allow_html=True)
    st.sidebar.image(str(logo_path), use_container_width=True)
    st.sidebar.markdown("""
        </div>
        <div style='margin-bottom: 0.75rem; padding-bottom: 0.5rem; border-bottom: 2px solid #e2e8f0; margin-top: 0.5rem;'></div>
    """, unsafe_allow_html=True)
else:
    # Logo temporaire (emoji) si logo non trouvé
    st.sidebar.markdown("""
        <div style='text-align: center; margin-top: 0; padding-top: 0;'>
            <div style='width: 180px; height: 180px; background: linear-gradient(135deg, #10b981 0%, #059669 100%); border-radius: 12px; display: inline-flex; align-items: center; justify-content: center; box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);'>
                <span style='font-size: 4.5rem;'>📊</span>
            </div>
        </div>
        <div style='margin-bottom: 1.5rem; padding-bottom: 1rem; border-bottom: 2px solid #e2e8f0; margin-top: 1rem;'></div>
""", unsafe_allow_html=True)

# Initialize session state for current page
if 'current_page' not in st.session_state:
    st.session_state.current_page = "🏠 Dashboard"

# Pages disponibles
pages_options = [
    "🏠 Dashboard",
    "📄 Analyse de Documents",
    "📈 Analyse d'Impact",
    "🤖 Chatbot Financier",
    "📚 Documentation"
]

# Menu de navigation avec boutons cliquables (remplace les radio buttons)
# CSS scoped to sidebar only to prevent conflicts - Design moderne blanc/gris
st.sidebar.markdown("""
    <style>
        /* Largeur du sidebar légèrement réduite */
        section[data-testid="stSidebar"] {
            min-width: 280px !important;
            width: 280px !important;
        }
        /* Sidebar navigation buttons only - Design moderne */
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button {
            width: 100% !important;
            padding: 0.75rem 1rem !important;
            margin: 0.4rem 0 !important;
            border-radius: 10px !important;
            text-align: left !important;
            border-left: 4px solid transparent !important;
            transition: all 0.3s ease !important;
            font-size: 0.95rem !important;
            line-height: 1.4 !important;
            font-weight: 900 !important;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"] {
            background-color: #ffffff !important;
            color: #4a5568 !important;
            border: 1px solid #e2e8f0 !important;
            font-weight: 900 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="secondary"]:hover {
            background-color: #f7fafc !important;
            border-left-color: #10b981 !important;
            border-color: #cbd5e0 !important;
            transform: translateX(3px) !important;
            color: #2d3748 !important;
            box-shadow: 0 2px 8px rgba(16, 185, 129, 0.15) !important;
            font-weight: 900 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #10b981 0%, #059669 100%) !important;
            color: #ffffff !important;
            border: none !important;
            border-left: 4px solid #047857 !important;
            font-weight: 900 !important;
            box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3) !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stButton"] > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
            box-shadow: 0 6px 16px rgba(16, 185, 129, 0.4) !important;
            transform: translateY(-1px) !important;
            font-weight: 900 !important;
        }
    </style>
""", unsafe_allow_html=True)

# Create navigation buttons
page = st.session_state.current_page
for nav_page in pages_options:
    is_active = nav_page == st.session_state.current_page
    if st.sidebar.button(
        nav_page, 
        key=f"nav_{nav_page}",
        use_container_width=True,
        type="primary" if is_active else "secondary"
    ):
        st.session_state.current_page = nav_page
        st.rerun()

# Update page variable after button clicks
page = st.session_state.current_page

# Séparateur visuel
st.sidebar.markdown("---")

# Titre principal
st.markdown('<h1 class="main-header">ReguAI</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Regulatory Intelligence Assistant - Datathon PolyFinances 2025</p>', unsafe_allow_html=True)

# PAGE 1: Dashboard
if page == "🏠 Dashboard":
    st.header("📊 Dashboard - Vue Globale du Portefeuille S&P 500")
    
    # Charger les données depuis company_universe.json (source principale)
    if not st.session_state.data_loaded:
        with st.spinner("Chargement des données depuis Company Universe..."):
            # Charger company_universe (contient tout : market data + 10-K filings)
            company_universe = load_company_universe()
            
            if company_universe:
                # Convertir en DataFrames pour le dashboard
                composition_df, performance_df = company_universe_to_dataframes(company_universe)
                
                if composition_df is not None and performance_df is not None:
                    st.session_state.company_universe = company_universe
                    st.session_state.composition_sp500 = composition_df
                    st.session_state.stocks_performance = performance_df
                    st.session_state.data_loaded = True
                else:
                    pass  # Erreur silencieuse - données non disponibles
            # Company Universe non trouvé - ignoré
    
    if st.session_state.data_loaded:
        composition = st.session_state.composition_sp500
        performance = st.session_state.stocks_performance
        company_universe = st.session_state.get('company_universe', None)
        
        # Afficher tous les composants via les fonctions helper
        render_dashboard_kpis(composition, performance, company_universe)
        render_sector_treemap(performance)
        render_composition_charts(composition)
        render_composition_table(composition)
        render_performance_table(performance, composition)

# PAGE 2: Analyse de Documents
elif page == "📄 Analyse de Documents":
    st.header("📄 Analyse de Documents Réglementaires")
    
    # Détecter si AWS est disponible
    aws_available = False
    aws_error_msg = None
    try:
        import boto3
        # Test rapide des credentials AWS - utilise list_foundation_models sans maxResults
        bedrock_client = boto3.client('bedrock', region_name='us-east-1')
        # Appel simple sans maxResults (qui n'est plus supporté)
        bedrock_client.list_foundation_models()
        aws_available = True
    except Exception as e:
        aws_available = False
        aws_error_msg = str(e)
    
    # Si AWS indisponible, mode visualisation uniquement
        if not aws_available:
            st.warning("⚠️ AWS non disponible. Mode visualisation uniquement : affichage des analyses déjà effectuées.")
            if aws_error_msg:
                with st.expander("🔍 Détails de l'erreur AWS"):
                    st.code(aws_error_msg)
        
        # Upload Section pour ajouter des documents dans raw
        with st.expander("📤 Upload Nouveau Document", expanded=False):
            uploaded_file = st.file_uploader(
                "Choisir un document réglementaire",
                type=['html', 'xml', 'pdf', 'txt'],
                help="Formats supportés: HTML, XML, PDF, TXT. Le fichier sera sauvegardé dans data/raw/directives",
                key="doc_uploader_viz"
            )
            
            if uploaded_file is not None:
                # Button to save the file
                if st.button("💾 Enregistrer le Document", type="primary", key="save_uploaded_viz"):
                    # Save uploaded file to raw directory (also uploads to S3 if AWS available)
                    from scripts.helpers.document_analysis_helper import save_uploaded_file
                    
                    save_result = save_uploaded_file(uploaded_file, destination_dir='data/raw/directives', use_aws=True)
                    
                    if save_result['success']:
                        st.success(f"✅ Document sauvegardé : {save_result['filename']}")
                        
                        # Show S3 upload status if available
                        if save_result.get('stored_in') == 'local_and_s3':
                            st.info(f"☁️ Également uploadé sur AWS S3 : {save_result.get('s3_path', 'N/A')}")
                        elif save_result.get('stored_in') == 'local_only':
                            st.caption("💾 Sauvegardé localement uniquement (AWS non disponible ou non configuré)")
                        
                        st.info("💡 Le document a été ajouté à la liste. Vous pouvez l'analyser plus tard si AWS est disponible.")
                        st.balloons()
                        # Rerun to refresh the page and show the new document
                        st.rerun()
                    else:
                        st.error(f"❌ Erreur lors de la sauvegarde : {save_result.get('error', 'Erreur inconnue')}")
        
        st.divider()
        st.subheader("📚 Tous les Documents")
        
        # Charger tous les documents (bruts + extractions)
        all_documents = get_all_documents_with_status()
        
        if all_documents:
            # Filter options
            filter_status = st.selectbox(
                "Filtrer par statut",
                ["Tous", "Analysés", "Non analysés"],
                key="filter_status_viz",
                index=0
            )
            
            # Apply filters
            filtered_docs = []
            for doc in all_documents:
                # Status filter
                if filter_status == "Analysés" and doc['status'] not in ['analyzed', 'analyzed_3tier']:
                    continue
                elif filter_status == "Non analysés" and doc['status'] in ['analyzed', 'analyzed_3tier']:
                    continue
                
                filtered_docs.append(doc)
            
            if filtered_docs:
                # Create table header
                st.markdown("""
                <style>
                .doc-table {
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }
                .doc-table th {
                    background-color: #f0f0f0;
                    padding: 12px;
                    text-align: left;
                    border-bottom: 2px solid #ddd;
                    font-weight: bold;
                }
                .doc-table td {
                    padding: 12px;
                    border-bottom: 1px solid #e0e0e0;
                    vertical-align: top;
                }
                .doc-table tr:hover {
                    background-color: #f9f9f9;
                }
                </style>
                """, unsafe_allow_html=True)
                
                # Table header
                header_cols = st.columns([3, 2, 1.5, 2.5])
                with header_cols[0]:
                    st.markdown("**📄 Document**")
                with header_cols[1]:
                    st.markdown("**📅 Date**")
                with header_cols[2]:
                    st.markdown("**📊 Statut**")
                with header_cols[3]:
                    st.markdown("**⚙️ Actions**")
                
                st.divider()
                
                # Display documents in table rows
                for idx, doc in enumerate(filtered_docs):
                    col_info, col_date, col_status, col_actions = st.columns([3, 2, 1.5, 2.5])
                    
                    with col_info:
                        icon = "📄"
                        display_name = doc.get('title') or doc.get('document_id', doc['filename'])
                        
                        # For raw files, show badge
                        if doc.get('is_raw_file'):
                            st.markdown(f"{icon} **{display_name}** 📄 Fichier brut")
                        else:
                            st.markdown(f"{icon} **{display_name}**")
                    
                    with col_date:
                        # Try to get document date from extracted info, otherwise use upload date
                        doc_date = None
                        if doc.get('extraction') and doc['extraction'].get('data'):
                            extracted_info = doc['extraction']['data'].get('extracted_info', {})
                            doc_date = extracted_info.get('effective_date')
                        
                        if doc_date:
                            st.text(f"📅 {doc_date}")
                        else:
                            upload_date_str = doc['upload_date'].strftime("%Y-%m-%d")
                            st.text(f"📅 {upload_date_str}")
                    
                    with col_status:
                        if doc['status'] == 'analyzed_3tier':
                            st.success("✅ Analysé (3-Tier)")
                        elif doc['status'] == 'analyzed':
                            st.info("✅ Analysé")
                        else:
                            st.warning("⏳ Non analysé")
                    
                    with col_actions:
                        if doc['status'] in ['analyzed', 'analyzed_3tier'] and doc.get('extraction'):
                            # Impact analysis button (all analyses are complete)
                            doc_id = None
                            if doc.get('extraction') and doc['extraction'].get('data'):
                                doc_id = doc['extraction']['data'].get('document_id', '')
                            if st.button("📈 Analyse d'Impact", key=f"view_impact_viz_{idx}", help="Voir l'analyse d'impact"):
                                # Store document_id to pre-select in Impact page
                                if doc_id:
                                    st.session_state['selected_regulation_id'] = doc_id
                                # Redirect to Impact Analysis page
                                st.session_state.current_page = "📈 Analyse d'Impact"
                                st.rerun()
                    
                    # Détails expandable avec titre de la directive (s'ouvre/se ferme directement)
                    if doc['status'] in ['analyzed', 'analyzed_3tier'] and doc.get('extraction'):
                        data = doc['extraction'].get('data', {})
                        if data:
                            # Get directive title for the expander
                            extracted_info = data.get('extracted_info', {})
                            directive_title = extracted_info.get('title', display_name)
                            
                            with st.expander(f"📋 Détails d'extraction - {directive_title}"):
                                _display_extraction_results(data)
                    
                    if idx < len(filtered_docs) - 1:
                        st.divider()
    else:
        # Mode normal avec AWS disponible
        
        # Check for completed extractions first
        needs_refresh = _check_running_extractions()
        
        # Note: Extractions process immediately when triggered (Streamlit limitation)
        # We check for completion on each page load
        
        # Clean up old running extractions (in case page was refreshed during processing)
        if st.session_state.running_extractions:
            # Clean up stale entries (older than 10 minutes)
            current_time = datetime.now()
            stale = []
            for filename, info in st.session_state.running_extractions.items():
                start_time = info.get('start_time')
                if start_time and (current_time - start_time).total_seconds() > 600:
                    stale.append(filename)
            for filename in stale:
                del st.session_state.running_extractions[filename]
        
        # Upload Section (always visible at top)
        with st.expander("📤 Upload Nouveau Document", expanded=False):
            uploaded_file = st.file_uploader(
                "Choisir un document réglementaire",
                type=['html', 'xml', 'pdf', 'txt'],
                help="Formats supportés: HTML, XML, PDF, TXT",
                key="doc_uploader"
            )
            
            if uploaded_file is not None:
                # Button to save the file
                if st.button("💾 Enregistrer le Document", type="primary", key="save_uploaded"):
                    # Save the file directly to documents directory
                    save_result = save_uploaded_file(uploaded_file)
                    
                    if save_result['success']:
                        st.success(f"✅ Document '{save_result['filename']}' ajouté avec succès !")
                        st.info("💡 Le document apparaît maintenant dans la liste ci-dessous. Vous pouvez l'analyser en cliquant sur le bouton 🔍")
                        st.balloons()
                        # Auto-refresh to show the new document in the list
                        st.rerun()
                    else:
                        st.error(f"❌ Erreur lors de l'enregistrement: {save_result.get('error', 'Erreur inconnue')}")
        
        st.divider()
        
        # Main Documents View - Unified Table
        st.subheader("📚 Tous les Documents")
        
        # Refresh button to force reload
        col_filter, col_refresh = st.columns([3, 1])
        with col_filter:
            filter_status = st.selectbox(
                "Filtrer par statut",
                ["Tous", "Analysés", "Non analysés"],
                key="filter_status",
                index=0  # Par défaut "Tous" pour voir tous les documents
            )
        with col_refresh:
            if st.button("🔄 Actualiser", help="Rafraîchir la liste des documents"):
                st.rerun()
        
        # Get all documents with status
        # Force refresh by calling the function directly (no cache)
        all_documents = get_all_documents_with_status()
        
        # Debug: Print status for first few documents (remove after testing)
        # import sys
        # print(f"DEBUG: {len(all_documents)} documents loaded", file=sys.stderr)
        # for doc in all_documents[:3]:
        #     print(f"  - {doc.get('filename', '?')[:50]}: status={doc.get('status', '?')}", file=sys.stderr)
        
        # Apply filters
        filtered_docs = []
        for doc in all_documents:
            # Status filter
            if filter_status == "Analysés" and doc['status'] not in ['analyzed', 'analyzed_3tier']:
                continue
            elif filter_status == "Non analysés" and doc['status'] in ['analyzed', 'analyzed_3tier']:
                continue
            
            
            filtered_docs.append(doc)
        
        if filtered_docs:
            # Create table header
            st.markdown("""
            <style>
            .doc-table {
                width: 100%;
                border-collapse: collapse;
                margin: 20px 0;
            }
            .doc-table th {
                background-color: #f0f0f0;
                padding: 12px;
                text-align: left;
                border-bottom: 2px solid #ddd;
                font-weight: bold;
            }
            .doc-table td {
                padding: 12px;
                border-bottom: 1px solid #e0e0e0;
                vertical-align: top;
            }
            .doc-table tr:hover {
                background-color: #f9f9f9;
            }
            </style>
            """, unsafe_allow_html=True)
            
            # Table header
            header_cols = st.columns([3, 2, 1.5, 2.5])
            with header_cols[0]:
                st.markdown("**📄 Document**")
            with header_cols[1]:
                st.markdown("**📅 Date**")
            with header_cols[2]:
                st.markdown("**📊 Statut**")
            with header_cols[3]:
                st.markdown("**⚙️ Actions**")
            
            st.divider()
            
            # Display documents in table rows
            for idx, doc in enumerate(filtered_docs):
                # Create columns for document info and actions
                col_info, col_date, col_status, col_actions = st.columns([3, 2, 1.5, 2.5])
                
                with col_info:
                    # Document name with icon
                    icon = "📄" if not doc['is_hidden'] else "👁️‍🗨️"
                    
                    # Get display name: use extracted title if available, otherwise use filename
                    display_name = doc.get('title') or doc['filename']
                    original_filename = doc['filename']  # Keep for duplicate detection
                
                    if doc['status'] in ['analyzed', 'analyzed_3tier'] and doc.get('extraction') and doc['extraction'].get('data'):
                        extracted_info = doc['extraction']['data'].get('extracted_info', {})
                        title = extracted_info.get('title', '')
                        if title:
                            display_name = title
                    
                    # Also check if document_id is available
                    if doc.get('document_id'):
                        display_name = doc.get('title', doc.get('document_id', display_name))
                    
                    # Display the title (or filename if not analyzed)
                    # For raw files, show a badge
                    if doc.get('is_raw_file'):
                        st.markdown(f"**{icon} {display_name}** 📄 Fichier brut")
                    else:
                        st.markdown(f"**{icon} {display_name}**")
                    
                    # File info removed as requested
                    
                    with col_date:
                        # Try to get document date from extracted info, otherwise use upload date
                        doc_date = None
                        if doc.get('extraction') and doc['extraction'].get('data'):
                            extracted_info = doc['extraction']['data'].get('extracted_info', {})
                            doc_date = extracted_info.get('effective_date')
                        
                        if doc_date:
                            st.text(f"📅 {doc_date}")
                        else:
                            upload_date_str = doc['upload_date'].strftime("%Y-%m-%d")
                            st.text(f"📅 {upload_date_str}")
                    
                    with col_status:
                        if doc['status'] == 'analyzed_3tier':
                            st.success("✅ Analysé (3-Tier)")
                        elif doc['status'] == 'analyzed':
                            st.info("✅ Analysé")
                        else:
                            st.warning("⏳ Non analysé")
                    
                    with col_actions:
                        # Action buttons in a row
                        action_col1, action_col2, action_col3 = st.columns(3)
                        
                        with action_col1:
                            # Analyze button
                            if doc['status'] not in ['analyzed', 'analyzed_3tier']:
                                if st.button("🔍", key=f"analyze_{idx}", help="Analyser ce document"):
                                    # Process immediately with clear feedback
                                    progress_msg = st.empty()
                                    with progress_msg.container():
                                        st.warning(f"⏳ Analyse de '{doc['filename']}' en cours...")
                                        st.caption("⏱️ Cela peut prendre 1-3 minutes. Vous pouvez continuer à naviguer dans l'application.")
                                    
                                    try:
                                        # For raw files, force new analysis (don't use existing extracted directives)
                                        # Check if this is a raw file (not from extracted_directives)
                                        is_raw_file = not doc['path'].endswith('_extracted.json')
                                        result = extract_from_local_file(
                                            doc['path'], 
                                            use_cache=True, 
                                            use_aws_services=True,
                                            force_new_analysis=is_raw_file  # Force new analysis for raw files
                                        )
                                        
                                        progress_msg.empty()
                                        
                                        if result.get('processing_status') == 'completed':
                                            st.success("✅ Analyse terminée avec succès !")
                                            
                                            # Show suggested filename if different
                                            suggested_name = generate_filename_from_extraction(result, Path(doc['filename']).suffix)
                                            if suggested_name != doc['filename']:
                                                st.info(f"📝 Nom suggéré: `{suggested_name}`")
                                            
                                            st.balloons()
                                            st.rerun()  # Refresh to show updated status
                                        else:
                                            st.error(f"❌ Erreur: {result.get('error', 'Erreur inconnue')}")
                                    except Exception as e:
                                        progress_msg.empty()
                                        st.error(f"❌ Erreur: {str(e)}")
                        
                        with action_col2:
                            # View Impact Analysis button (all analyses are complete)
                            if doc['status'] in ['analyzed', 'analyzed_3tier'] and doc.get('extraction'):
                                doc_id = None
                                if doc.get('extraction') and doc['extraction'].get('data'):
                                    doc_id = doc['extraction']['data'].get('document_id', '')
                                if st.button("📈 Impact", key=f"view_impact_{idx}", help="Voir l'analyse d'impact"):
                                    # Store document_id to pre-select in Impact page
                                    if doc_id:
                                        st.session_state['selected_regulation_id'] = doc_id
                                    # Redirect to Impact Analysis page
                                    st.session_state.current_page = "📈 Analyse d'Impact"
                                    st.rerun()
                        
                        with action_col3:
                            # View/Delete extraction results
                            if doc['status'] in ['analyzed', 'analyzed_3tier'] and doc['extraction']:
                                if st.button("🗑️", key=f"delete_ext_{idx}", help="Supprimer résultat"):
                                    if delete_extraction(doc['extraction']['path'], doc['extraction']['source']):
                                        st.success("✅ Résultat supprimé")
                                        st.rerun()
                                    else:
                                        st.error("❌ Erreur lors de la suppression")
                    
                    # Expandable section for viewing extraction results avec titre de la directive (s'ouvre/se ferme directement)
                    if doc['status'] in ['analyzed', 'analyzed_3tier'] and doc.get('extraction'):
                        data = doc['extraction'].get('data', {})
                        if data:
                            # Get directive title for the expander
                            extracted_info = data.get('extracted_info', {})
                            directive_title = extracted_info.get('title', display_name)
                            
                            with st.expander(f"📋 Détails d'extraction - {directive_title}"):
                                _display_extraction_results(data)
                
                if idx < len(filtered_docs) - 1:
                    st.divider()
        else:
            st.info("Aucun document trouvé. Uploadez un document pour commencer.")

# PAGE 3: Analyse d'Impact
elif page == "📈 Analyse d'Impact":
    st.header("📈 Analyse d'Impact Réglementaire - 3-Tier Valuation")
    st.info("💡 Mode visualisation : affichage des analyses déjà effectuées")
    st.divider()
    
    # Load and display results
    impact_results = load_impact_results()
    
    if impact_results is None:
        # Ne rien afficher si pas de données
        st.stop()
    
    # Convert to DataFrames
    companies_df_full, regulations_df_full = impact_results_to_dataframes(impact_results)
    
    # Vérifier si les DataFrames sont vides
    if len(companies_df_full) == 0 or len(regulations_df_full) == 0:
        # Ne rien afficher si pas de données
        st.stop()
    
    # Initialize selected_reg_id
    selected_reg_id = None
    
    # Directive selector at the top - ALWAYS show it first
    st.subheader("📋 Sélectionner la Directive à Analyser")
    
    if len(regulations_df_full) > 0:
        # Create display labels for selectbox
        regulation_options = regulations_df_full.apply(
            lambda row: f"{row['regulation_title'][:70]}... ({row['regulation_country']})",
            axis=1
        ).tolist()
        
        # Add "Aucune sélection" option at the beginning
        options_with_none = ["-- Sélectionner une directive --"] + regulation_options
        
        # Check if we have a pre-selected regulation from document page
        default_index = 0  # Default to "-- Sélectionner une directive --"
        if 'selected_regulation_id' in st.session_state and st.session_state['selected_regulation_id']:
            # Find the matching regulation in the dataframe
            pre_selected_reg_id = st.session_state['selected_regulation_id']
            matching_regs = regulations_df_full[regulations_df_full['regulation_id'] == pre_selected_reg_id]
            if len(matching_regs) > 0:
                # Find the index in the full dataframe
                matching_idx = matching_regs.index[0]
                # Get the position in the dataframe (reset index to get numeric position)
                reg_positions = list(regulations_df_full.index)
                try:
                    reg_index = reg_positions.index(matching_idx)
                    # Add 1 because first option is placeholder
                    default_index = reg_index + 1
                except (ValueError, IndexError):
                    default_index = 0
                # Clear the pre-selection after using it
                del st.session_state['selected_regulation_id']
        
        selected_option = st.selectbox(
            f"Sélectionner une directive ({len(regulations_df_full)} disponibles):",
            options_with_none,
            index=default_index,
            key="regulation_selector_top"
        )
        
        # Si aucune directive n'est sélectionnée, ne rien afficher
        if selected_option == "-- Sélectionner une directive --":
            st.stop()
        
        # Get selected regulation index (subtract 1 because first option is placeholder)
        selected_idx = options_with_none.index(selected_option) - 1
        selected_reg = regulations_df_full.iloc[selected_idx]
        selected_reg_id = selected_reg['regulation_id']
        selected_reg_title = selected_reg['regulation_title']
        
        st.divider()
        
        # Filter ALL data by selected directive
        companies_df = companies_df_full[companies_df_full['regulation_id'] == selected_reg_id].copy()
        regulations_df = regulations_df_full[regulations_df_full['regulation_id'] == selected_reg_id].copy()
        
        # Vérifier si les données filtrées sont vides
        if len(companies_df) == 0 or len(regulations_df) == 0:
            # Ne rien afficher si pas de données
            st.stop()
        
        # Display summary (filtered by selected directive)
        # Ensure DataFrames (not Series)
        if isinstance(companies_df, pd.Series):
            companies_df = companies_df.to_frame().T
        if isinstance(regulations_df, pd.Series):
            regulations_df = regulations_df.to_frame().T
        render_impact_summary(companies_df, regulations_df)
        
        st.divider()
        
        # Load recommendations (will be filtered in render_recommendations_table)
        recommendations = load_recommendations()
        
        # Generate signals from impact results (filtered by selected directive)
        # Create filtered impact_results for signals
        if len(companies_df) > 0 and selected_reg_id:
            filtered_impact_results = {
                'analysis_date': impact_results.get('analysis_date'),
                'total_pairs': len(companies_df),
                'total_regulations': 1,
                # Complete analysis always available
                'regulations': {}
            }
            
            # Get the selected regulation data
            if selected_reg_id in impact_results.get('regulations', {}):
                filtered_impact_results['regulations'][selected_reg_id] = impact_results['regulations'][selected_reg_id]
            
            with st.spinner("🔄 Generating trading signals..."):
                try:
                    signals_data = generate_signals_for_analysis(filtered_impact_results, investment_strategy='LONG_ONLY')
                    signals_df = signals_to_dataframe(signals_data, impact_results=filtered_impact_results)
                except Exception as e:
                    st.warning(f"⚠️ Could not generate signals: {e}")
                    signals_data = None
                    signals_df = pd.DataFrame()
        else:
            signals_df = pd.DataFrame()
        
        # Main tabs - using expanders for clickable headers
        with st.expander("📊 3-Tier Analysis", expanded=True):
            st.subheader("Three-Tier Valuation Architecture")
            
            # Tier 1: FCF Impact
            # Ensure DataFrame (not Series)
            if isinstance(companies_df, pd.Series):
                companies_df = companies_df.to_frame().T
            render_tier1_fcf_chart(companies_df)
            
            st.divider()
            
            # Tier 2: Risk Premium
            render_tier2_risk_chart(companies_df)
            
            st.divider()
            
            # Tier 3: Price Impact
            render_tier3_price_impact_chart(companies_df)
            
            st.divider()
            
            # Risk Distribution
            render_final_risk_distribution(companies_df)
        
        with st.expander("📈 Trading Signals"):
            if not signals_df.empty:
                # Signal summary
                render_signals_summary(signals_df)
                
                st.divider()
                
                # Signal distribution
                render_signals_distribution(signals_df)
                
                st.divider()
                
                # Component signals
                render_component_signals_chart(signals_df)
                
                st.divider()
                
                # Signals table
                render_signals_table(signals_df)
        
        with st.expander("🤖 Recommendations"):
            # Load recommendations per directive format only
            recommendations = load_recommendations()
            
            if recommendations and 'recommendations_by_directive' in recommendations:
                # Filter by selected directive
                render_recommendations_table(recommendations, selected_reg_id=selected_reg_id)
            else:
                # No recommendations found
                # Check if AWS is available
                try:
                    import boto3
                    test_client = boto3.client('bedrock', region_name='us-east-1')
                    test_client.list_foundation_models()
                    aws_available = True
                except Exception:
                    aws_available = False
                
                # Recommendations not found - no message needed
                pass
        
        with st.expander("📋 Companies Details"):
            # Display regulation info (already filtered by directive selector at top)
            if len(regulations_df) > 0:
                st.divider()
            
            # Companies table (already filtered by directive)
            # Ensure DataFrame (not Series) - already checked above but ensure again
            if isinstance(companies_df, pd.Series):
                companies_df = companies_df.to_frame().T
            render_company_details_table(companies_df, filter_regulation_id=None)
            
            # Companies table with all metrics
            if len(companies_df) > 0:
                st.subheader(f"Entreprises affectées ({len(companies_df)} entreprises)")
            else:
                st.subheader("Entreprises affectées")
            render_companies_table(companies_df)

# PAGE 4: Chatbot Financier
elif page == "🤖 Chatbot Financier":
    st.header("🤖 Chatbot Financier avec RAG")
    
    # Initialiser RAG au chargement (avec cache Streamlit)
    @st.cache_resource
    def init_rag():
        """Initialise le système RAG (cache avec Streamlit)"""
        result = initialize_rag_system(
            use_cache=True,
            tenk_limit=100  # MVP : 100 fichiers 10-K pour performance
        )
        return result
    
    # Gestion des conversations sauvegardées
    conv_dir = Path('data/generated/saved_conversations')
    conv_dir.mkdir(parents=True, exist_ok=True)
    
    # Lister les conversations sauvegardées
    saved_conversations = sorted(conv_dir.glob("conversation_*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    
    # Interface pour sauvegarder/charger
    col1, col2 = st.columns([3, 1])
    with col1:
        # Sélecteur pour charger une conversation
        if saved_conversations:
            # Extraire le nom personnalisé du filename si disponible
            def extract_conv_name(conv_path):
                stem = conv_path.stem.replace('conversation_', '')
                # Format: nom_personnalise_YYYYMMDD_HHMMSS ou YYYYMMDD_HHMMSS
                parts = stem.split('_')
                if len(parts) >= 3:
                    # Il y a un nom personnalisé (tout sauf les 2 dernières parties qui sont date/heure)
                    custom_name = '_'.join(parts[:-2])
                    timestamp = '_'.join(parts[-2:])
                    return f"{custom_name} - {datetime.strptime(timestamp, '%Y%m%d_%H%M%S').strftime('%Y-%m-%d %H:%M')}"
                else:
                    # Pas de nom personnalisé, juste timestamp
                    timestamp = stem
                    return f"Conversation - {datetime.strptime(timestamp, '%Y%m%d_%H%M%S').strftime('%Y-%m-%d %H:%M')}"
            
            conv_names = [extract_conv_name(conv) for conv in saved_conversations]
            
            # Initialiser le state pour suivre la dernière conversation chargée
            if 'last_loaded_conversation' not in st.session_state:
                st.session_state.last_loaded_conversation = None
            
            # Liste des options
            options = ["Nouvelle conversation"] + conv_names
            
            # Trouver l'index actuel
            current_index = 0
            if st.session_state.last_loaded_conversation and st.session_state.last_loaded_conversation in conv_names:
                current_index = conv_names.index(st.session_state.last_loaded_conversation) + 1
            
            selected_conv = st.selectbox(
                "📂 Charger une conversation sauvegardée",
                options,
                key="load_conversation",
                index=current_index
            )
            
            # Charger seulement si la sélection a changé
            if selected_conv != "Nouvelle conversation":
                if st.session_state.last_loaded_conversation != selected_conv:
                    try:
                        # Trouver le fichier correspondant
                        idx = conv_names.index(selected_conv)
                        conv_file = saved_conversations[idx]
                        
                        # Charger la conversation
                        with open(conv_file, 'r', encoding='utf-8') as f:
                            loaded_messages = json.load(f)
                        
                        st.session_state.messages = loaded_messages
                        st.session_state.last_loaded_conversation = selected_conv
                        st.success(f"✅ Conversation chargée")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erreur chargement: {e}")
            else:
                # Si on sélectionne "Nouvelle conversation", effacer l'historique seulement si on vient d'une conversation chargée
                if st.session_state.last_loaded_conversation and st.session_state.last_loaded_conversation != "Nouvelle conversation":
                    st.session_state.messages = []
                    st.session_state.last_loaded_conversation = None
                    st.rerun()
        else:
            st.caption("Aucune conversation sauvegardée")
    with col2:
        # Bouton Effacer à côté du nom de la discussion, à droite
        st.markdown("<br>", unsafe_allow_html=True)  # Aligner verticalement avec le selectbox
        if st.button("🗑️ Effacer", help="Efface l'historique actuel", key="clear_conversation", use_container_width=True):
            st.session_state.messages = []
            st.success("✅ Historique effacé")
            st.rerun()
    
    # Interface pour sauvegarder
    col_save1, col_save2 = st.columns([2, 1])
    with col_save1:
        # Input pour le nom de la conversation
        if 'save_conversation_name' not in st.session_state:
            st.session_state.save_conversation_name = ""
        
        conv_name = st.text_input(
            "Nom de la conversation",
            value=st.session_state.save_conversation_name,
            placeholder="Ex: Discussion sur Nvidia",
            key="conversation_name_input"
        )
        
        if st.button("💾 Sauvegarder", help="Sauvegarde la conversation actuelle", key="save_conversation"):
            try:
                # Vérifier que un nom a été fourni
                if not conv_name.strip():
                    st.error("❌ Veuillez entrer un nom pour la conversation avant de sauvegarder.")
                else:
                    # Nettoyer le nom (enlever caractères spéciaux pour nom de fichier)
                    safe_name = "".join(c for c in conv_name.strip() if c.isalnum() or c in (' ', '-', '_')).strip()
                    safe_name = safe_name.replace(' ', '_')
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"conversation_{safe_name}_{timestamp}.json"
                    
                    conv_file = conv_dir / filename
                    
                    # Sauvegarder
                    with open(conv_file, 'w', encoding='utf-8') as f:
                        json.dump(st.session_state.messages, f, indent=2, ensure_ascii=False)
                    
                    st.success(f"✅ Conversation sauvegardée : {conv_name}")
                    st.session_state.save_conversation_name = ""  # Réinitialiser le champ
                    st.rerun()
            except Exception as e:
                st.error(f"❌ Erreur sauvegarde: {e}")
    
    # Initialiser RAG si pas déjà fait (silencieux - sans spinner visible)
    if 'rag_initialized' not in st.session_state:
        # Initialiser en arrière-plan sans afficher de spinner visible
            rag_result = init_rag()
            if rag_result['success']:
                st.session_state.rag_initialized = True
                st.session_state.rag_from_cache = rag_result.get('from_cache', False)
                
                if rag_result.get('from_cache'):
                    print(f"✅ RAG initialisé depuis cache")
                else:
                    print(f"✅ RAG initialisé avec {rag_result.get('num_documents', 0)} documents")
            else:
                error_msg = rag_result.get('error', 'Erreur inconnue')
                suggestion = rag_result.get('suggestion', '')
                
                st.error(f"❌ Erreur initialisation RAG: {error_msg}")
                if suggestion:
                    st.info(f"💡 {suggestion}")
                
                st.warning("⚠️ Le chatbot fonctionnera sans RAG (mode basique)")
                st.session_state.rag_initialized = False
    
    # Afficher stats RAG dans sidebar
    if st.session_state.get('rag_initialized'):
        stats = get_rag_stats()
        # RAG actif (pas besoin d'afficher, c'est implicite si le chatbot fonctionne)
        # Cache RAG disponible
    
    # Initialisation de l'historique de chat
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    
    # Mode RAG ou basique
    use_rag = st.session_state.get('rag_initialized', False)
    if use_rag:
        st.caption("🟢 Mode RAG activé - Réponses basées sur la base de connaissances")
    
    # Container pour forcer le scroll
    scroll_container = st.container()
    
    with scroll_container:
        # Afficher l'historique (sauf si on est en train de générer une nouvelle réponse)
        # On vérifie s'il y a une question en cours pour éviter d'afficher l'ancienne réponse en double
        generating_new_response = st.session_state.get("_generating", False)
        
        for idx, message in enumerate(st.session_state.messages):
            # Si c'est la dernière réponse d'assistant et qu'on génère une nouvelle réponse, skip
            # (elle sera affichée dans le bloc de génération)
            if generating_new_response and message["role"] == "assistant" and idx == len(st.session_state.messages) - 1:
                continue
                
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
                
                # Afficher sources si disponibles (mode RAG)
                if message["role"] == "assistant" and "sources" in message and message["sources"]:
                    with st.expander("📚 Sources utilisées"):
                        for i, source in enumerate(message["sources"][:5], 1):  # Top 5 sources
                            source_type = source.get('type', 'unknown')
                            if source_type == 'regulation':
                                st.write(f"**{i}. [{source_type}]** {source.get('title', 'Réglementation')}")
                                if source.get('country'):
                                    st.caption(f"   Pays: {source['country']}")
                            elif source_type in ['10k', 'company_universe']:
                                st.write(f"**{i}. [{source_type}]** {source.get('company_name', 'N/A')} ({source.get('ticker', 'N/A')})")
                            else:
                                st.write(f"**{i}. [{source_type}]** {source.get('content_preview', '')[:100]}...")
    
    # Script JavaScript pour auto-scroll vers le bas après chaque nouveau message
    if st.session_state.messages:
        st.markdown("""
        <script>
            // Auto-scroll vers le bas
            function scrollToBottom() {
                window.scrollTo({
                    top: document.body.scrollHeight,
                    behavior: 'smooth'
                });
            }
            
            // Scroll immédiatement
            scrollToBottom();
            
            // Re-scroll après un court délai (au cas où le contenu n'est pas encore rendu)
            setTimeout(scrollToBottom, 100);
            setTimeout(scrollToBottom, 500);
        </script>
        """, unsafe_allow_html=True)
    
    # Traiter une question d'exemple si elle a été cliquée (AVANT chat_input)
    # Pas de logique de questions d'exemple - les utilisateurs saisissent directement leurs questions
    
    # Input utilisateur - Plus grand et visible
    if prompt := st.chat_input(
        "Posez votre question sur les réglementations ou les entreprises...",
        key="chat_input_main"
    ):
        st.session_state["_generating"] = True  # Marquer qu'on génère
        
        # Liste complète des questions d'exemple (affichées + backup)
        all_example_questions = [
            "Quel est l'impact de l'EU AI Act sur les entreprises tech du S&P 500 ?",
            "Quelles entreprises sont le plus exposées aux réglementations chinoises ?",
            "Compare l'impact de deux réglementations sur le portefeuille",
            "Explique-moi pourquoi Nvidia est recommandé à la réduction",
            "Quels sont les secteurs les plus impactés par l'Inflation Reduction Act ?",
            "Comment l'EU AI Act affecte-t-il les entreprises européennes ?",
            "Quelle est la différence entre l'exposure score et le final risk score ?",
            "Quelles entreprises du secteur énergétique sont concernées par les nouvelles réglementations ?",
            "Peux-tu expliquer le calcul du price impact pour une entreprise ?",
            "Quelles réglementations ont le plus grand impact sur le secteur financier ?",
            "Comment interpréter les recommandations REDUCE et INCREASE ?",
            "Quelles entreprises ont un risk score élevé mais un price impact faible ?",
            "Qu'est-ce que le Tier 1, Tier 2 et Tier 3 de l'analyse ?",
            "Quelles entreprises sont recommandées pour une augmentation de position ?",
            "Comment les réglementations européennes affectent-elles les entreprises américaines ?",
            "Quels sont les principaux risques identifiés pour le secteur tech ?",
            "Peux-tu comparer l'impact de l'EU AI Act et de l'Inflation Reduction Act ?",
            "Quelles entreprises sont les moins exposées aux réglementations ?",
            "Comment calculer le FCF impact per share ?",
            "Quelles réglementations sont en vigueur en Chine ?",
            "Quel est l'impact moyen des réglementations sur le S&P 500 ?",
            "Quelles entreprises ont un discount rate change significatif ?",
            "Comment les réglementations japonaises diffèrent-elles des européennes ?",
            "Quelles sont les entreprises avec le plus haut exposure score ?",
            "Peux-tu expliquer le processus de matching entre réglementations et entreprises ?",
            "Quelles réglementations ont le plus grand nombre d'entreprises affectées ?",
            "Comment interpréter les trading signals générés ?",
            "Quelles entreprises sont dans la catégorie 'high risk' ?"
        ]
        
        # Vérifier si la question posée correspond à une question d'exemple
        prompt_normalized = prompt.strip().lower()
        matching_example = None
        
        for example_q in all_example_questions:
            if prompt_normalized == example_q.strip().lower():
                matching_example = example_q
                break
        
        # Si la question correspond à une question d'exemple, la remplacer par une autre
        original_prompt = prompt
        question_replaced = False
        if matching_example:
            import random
            # Filtrer les questions d'exemple pour exclure celle qui a été posée
            available_questions = [q for q in all_example_questions if q.strip().lower() != prompt_normalized]
            # Sélectionner une question aléatoire parmi les disponibles
            if available_questions:
                prompt = random.choice(available_questions)
                question_replaced = True
        
        # Ajouter le message utilisateur avec la question (potentiellement remplacée)
        if not st.session_state.messages or st.session_state.messages[-1].get("content") != prompt:
            st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Afficher message utilisateur (la question remplacée si applicable)
        with st.chat_message("user"):
            # Si la question a été remplacée, afficher d'abord l'info
            if question_replaced:
                st.info(f"💡 Question d'exemple détectée et remplacée automatiquement")
                st.caption(f"Originale: « {original_prompt} »")
                st.markdown("---")
            
            # Afficher la question qui sera réellement traitée (remplacée si applicable)
            st.markdown(prompt)
            
            # Scroll immédiatement après affichage question
            st.markdown("""
            <script>
                setTimeout(function() {
                    window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});
                }, 50);
            </script>
            """, unsafe_allow_html=True)
        
        # Générer réponse
        with st.chat_message("assistant"):
            if use_rag:
                # Mode RAG - s'assurer que _generating reste True pendant toute la recherche
                # Utiliser un placeholder pour indiquer qu'on est en train de rechercher
                st.session_state["_generating"] = True
                st.session_state["_searching"] = True
                with st.spinner("🔍 Recherche dans la base de connaissances..."):
                    # Passer l'historique de conversation au RAG
                    conversation_history = st.session_state.messages[:-1] if len(st.session_state.messages) > 1 else []
                    rag_response = chat_with_rag(prompt, return_sources=True, conversation_history=conversation_history)
                    
                    if rag_response['error']:
                        response = f"❌ Erreur: {rag_response['error']}"
                        st.error(response)
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response,
                            "sources": []
                        })
                    else:
                        response = rag_response['answer']
                        st.markdown(response)
                        
                        # Ajouter réponse avec sources
                        st.session_state.messages.append({
                            "role": "assistant",
                            "content": response,
                            "sources": rag_response.get('sources', [])
                        })
                        
                        # Afficher info sur sources
                        if rag_response.get('sources'):
                            num_sources = len(rag_response['sources'])
                            st.caption(f"📚 Réponse basée sur {num_sources} document(s) de la base de connaissances")
                        
                        # Force scroll après affichage réponse (chat_input - RAG)
                        st.markdown("""
                        <script>
                            setTimeout(function() {
                                window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});
                            }, 100);
                        </script>
                        """, unsafe_allow_html=True)
            else:
                # Mode basique (sans RAG) - chat_input
                with st.spinner("🤔 Réflexion en cours..."):
                    # Convertir l'historique au format Claude
                    claude_messages = [
                        format_chat_message(msg["role"], msg["content"])
                        for msg in st.session_state.messages
                    ]
                    
                    # Appel à Claude (mode basique)
                    # Utiliser un modèle disponible dans votre compte
                    result = chat_with_claude(
                        claude_messages,
                        model="global.anthropic.claude-sonnet-4-5-20250929-v1:0",  # Modèle disponible dans votre compte
                        max_tokens=4000
                    )
                    
                    if result['error']:
                        response = f"❌ Erreur: {result['error']}"
                        st.error(response)
                    else:
                        response = result['response']
                        st.markdown(response)
                        
                        # Afficher usage si disponible
                        if result['usage']:
                            with st.expander("📊 Usage (Tokens)"):
                                usage = result['usage']
                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Input", usage.get('input_tokens', 0))
                                with col2:
                                    st.metric("Output", usage.get('output_tokens', 0))
                                with col3:
                                    total = usage.get('input_tokens', 0) + usage.get('output_tokens', 0)
                                    st.metric("Total", total)
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response,
                        "sources": []
                    })
                    
                    # Force scroll après affichage réponse (chat_input - basique)
                    st.markdown("""
                    <script>
                        setTimeout(function() {
                            window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'});
                        }, 100);
                    </script>
                    """, unsafe_allow_html=True)
        
        # Marquer génération terminée
        st.session_state["_generating"] = False
        st.session_state["_searching"] = False
    
    # Afficher des exemples de questions dans un expander
    # L'expander se ferme automatiquement pendant la génération mais peut être rouvert après
    st.markdown("---")
    
    # Déterminer si une génération est en cours
    is_generating = st.session_state.get("_generating", False) or st.session_state.get("_searching", False)
    
    # Initialiser l'état de l'expander si pas défini (ouvert au début)
    if "examples_expanded" not in st.session_state:
        st.session_state.examples_expanded = True
    
    # Fermer automatiquement si génération en cours
    # (on ne rouvre pas automatiquement après, l'utilisateur peut le faire manuellement)
    if is_generating:
        st.session_state.examples_expanded = False
    
    # Déterminer l'état d'expansion : utiliser l'état sauvé sauf si génération en cours
    expand_state = st.session_state.examples_expanded and not is_generating
    
    # Afficher l'expander (toujours visible, peut être contrôlé manuellement)
    # On utilise une key pour que Streamlit puisse gérer l'état, mais on force la fermeture pendant génération
    with st.expander("💡 Questions d'exemple", expanded=expand_state):
        # Mettre à jour l'état si on n'est pas en génération (l'utilisateur peut contrôler)
        if not is_generating:
            # Si l'expander est ouvert maintenant (après le rendu), mettre à jour le state
            # Note: On ne peut pas vraiment détecter le clic directement, mais on force l'état pendant génération
            # et on laisse l'utilisateur contrôler après
            st.session_state.examples_expanded = True  # On assume qu'il reste ouvert si pas de génération
        
        st.caption("Vous pouvez copier ces questions et les coller dans la barre de saisie")
        
        # Liste principale des questions d'exemple affichées (4)
        example_questions = [
            "Quel est l'impact de l'EU AI Act sur les entreprises tech du S&P 500 ?",
            "Quelles entreprises sont le plus exposées aux réglementations chinoises ?",
            "Compare l'impact de deux réglementations sur le portefeuille",
            "Explique-moi pourquoi Nvidia est recommandé à la réduction"
        ]
        
        # Liste de backup avec 20+ questions supplémentaires
        backup_questions = [
            "Quels sont les secteurs les plus impactés par l'Inflation Reduction Act ?",
            "Comment l'EU AI Act affecte-t-il les entreprises européennes ?",
            "Quelle est la différence entre l'exposure score et le final risk score ?",
            "Quelles entreprises du secteur énergétique sont concernées par les nouvelles réglementations ?",
            "Peux-tu expliquer le calcul du price impact pour une entreprise ?",
            "Quelles réglementations ont le plus grand impact sur le secteur financier ?",
            "Comment interpréter les recommandations REDUCE et INCREASE ?",
            "Quelles entreprises ont un risk score élevé mais un price impact faible ?",
            "Qu'est-ce que le Tier 1, Tier 2 et Tier 3 de l'analyse ?",
            "Quelles entreprises sont recommandées pour une augmentation de position ?",
            "Comment les réglementations européennes affectent-elles les entreprises américaines ?",
            "Quels sont les principaux risques identifiés pour le secteur tech ?",
            "Peux-tu comparer l'impact de l'EU AI Act et de l'Inflation Reduction Act ?",
            "Quelles entreprises sont les moins exposées aux réglementations ?",
            "Comment calculer le FCF impact per share ?",
            "Quelles réglementations sont en vigueur en Chine ?",
            "Quel est l'impact moyen des réglementations sur le S&P 500 ?",
            "Quelles entreprises ont un discount rate change significatif ?",
            "Comment les réglementations japonaises diffèrent-elles des européennes ?",
            "Quelles sont les entreprises avec le plus haut exposure score ?",
            "Peux-tu expliquer le processus de matching entre réglementations et entreprises ?",
            "Quelles réglementations ont le plus grand nombre d'entreprises affectées ?",
            "Comment interpréter les trading signals générés ?",
            "Quelles entreprises sont dans la catégorie 'high risk' ?"
        ]
        
        # Afficher chaque question dans une boîte copiable
        for i, question in enumerate(example_questions):
            st.markdown(f"""
            <div style="
                background-color: #f0f2f6;
                border: 1px solid #d1d5db;
                border-radius: 8px;
                padding: 12px 16px;
                margin-bottom: 10px;
                cursor: text;
                user-select: all;
                -webkit-user-select: all;
                -moz-user-select: all;
                -ms-user-select: all;
                font-size: 14px;
                color: #1f2937;
            ">
                {question}
            </div>
            """, unsafe_allow_html=True)
    
    # Style CSS pour agrandir la barre de saisie (grande dès le début)
    st.markdown("""
    <style>
        /* Barre de saisie plus grande - taille fixe dès le début */
        div[data-testid="stChatInput"] {
            min-height: 100px !important;
        }
        div[data-testid="stChatInput"] > div > div {
            min-height: 100px !important;
            height: 100px !important;
            font-size: 16px !important;
            padding: 15px 20px !important;
        }
        div[data-testid="stChatInput"] textarea {
            min-height: 70px !important;
            height: 70px !important;
            font-size: 16px !important;
            line-height: 1.6 !important;
        }
        /* S'assurer que le conteneur principal garde la taille */
        div[data-testid="stChatInput"] > div {
            min-height: 100px !important;
        }
        /* Positionner le bouton d'envoi au milieu */
        div[data-testid="stChatInput"] button {
            margin-top: 0px !important;
            position: relative !important;
            top: 0px !important;
        }
        /* Ajuster le conteneur du bouton pour centrer verticalement */
        div[data-testid="stChatInput"] > div > div:last-child {
            align-items: center !important;
            padding-top: 0px !important;
        }
        
        /* Style pour les messages utilisateur (questions posées) - fond plus foncé */
        /* Streamlit génère les messages avec une structure spécifique */
        div[data-testid="stChatMessage"] > div > div:last-child {
            background-color: #d1d5db !important;
            border-radius: 8px !important;
            padding: 12px 16px !important;
            color: #1f2937 !important;
            margin: 4px 0 !important;
        }
        
        /* Essayer de cibler spécifiquement les messages utilisateur */
        div[data-testid="stChatMessage"]:has(svg[viewBox*="24"]) > div > div:last-child {
            background-color: #d1d5db !important;
        }
        
        /* Style pour les questions d'exemple - sélection facile */
        div[style*="user-select: all"]:hover {
            background-color: #e5e7eb !important;
            border-color: #9ca3af !important;
        }
    </style>
    """, unsafe_allow_html=True)
    

# PAGE 5: Documentation
elif page == "📚 Documentation":
    st.header("📚 Documentation ReguAI")
    st.markdown("**Guide complet de l'application Regulatory Intelligence Assistant**")
    
    # Table des matières
    st.markdown("---")
    st.markdown("### 📑 Table des matières")
    toc_col1, toc_col2 = st.columns(2)
    with toc_col1:
        st.markdown("""
        - [🎯 Vue d'ensemble](#vue-densemble)
        - [🏠 Dashboard](#dashboard)
        - [📄 Analyse de Documents](#analyse-de-documents)
        - [📈 Analyse d'Impact](#analyse-dimpact)
        - [🤖 Chatbot Financier](#chatbot-financier)
        """)
    with toc_col2:
        st.markdown("""
        - [🔧 Architecture Technique](#architecture-technique)
        - [⚙️ Configuration](#configuration)
        - [📊 Sources de Données](#sources-de-données)
        - [❓ FAQ](#faq)
        """)
    
    st.markdown("---")
    
    # Vue d'ensemble
    st.markdown("## 🎯 Vue d'ensemble")
    st.markdown("""
    **ReguAI** est une application d'intelligence réglementaire conçue pour aider les gestionnaires de portefeuilles
    à comprendre et analyser l'impact des réglementations sur leurs investissements dans le S&P 500.
    
    ### Objectifs principaux :
    - 📊 **Visualiser** la composition et la performance du portefeuille S&P 500
    - 📄 **Analyser** des documents réglementaires pour extraire les informations clés
    - 📈 **Évaluer** l'impact des réglementations sur les entreprises
    - 🤖 **Interroger** une base de connaissances via un chatbot RAG (Retrieval Augmented Generation)
    """)
    
    st.markdown("---")
    
    # Dashboard
    st.markdown("## 🏠 Dashboard")
    st.markdown("""
    La page **Dashboard** offre une vue globale du portefeuille S&P 500 avec :
    
    ### KPIs Principaux
    - **Nombre total d'entreprises** dans le portefeuille
    - **Capitalisation boursière totale** (Market Cap)
    - **Répartition sectorielle** avec visualisations interactives
    - **Indicateurs de performance** (P/E ratio, Profit Margin, etc.)
    
    ### Visualisations
    - 🌳 **Treemap sectoriel** : Visualisation hiérarchique des secteurs et industries
    - 📊 **Graphiques de composition** : Répartition par poids, secteurs, industries
    - 📈 **Tableaux de performance** : Métriques financières détaillées par entreprise
    
    ### Données
    Les données proviennent du **Company Universe** qui contient :
    - Composition du portefeuille (Symbol, Company, Weight, Price, Sector, Industry)
    - Performance financière (Market Cap, Revenue, Op. Income, Net Income, EPS, FCF, P/E Ratio, Profit Margin)
    - Informations opérationnelles (Has NA Operations, Has EU Operations, Num Segments, Company Type)
    """)
    
    st.markdown("---")
    
    # Analyse de Documents
    st.markdown("## 📄 Analyse de Documents")
    st.markdown("""
    La page **Analyse de Documents** permet d'analyser des documents réglementaires avec extraction automatique d'informations.
    
    ### Fonctionnalités
    - 📤 **Upload de documents** : Formats supportés (HTML, XML, PDF, TXT)
    - 🔍 **Extraction automatique** : Utilisation d'Amazon Textract, Comprehend et Claude (Bedrock)
    - 📋 **Affichage des résultats** : Visualisation structurée des données extraites
    
    ### Processus d'extraction
    1. **Upload** : Sélectionner un document réglementaire
    2. **Traitement** : Analyse via AWS services (Textract, Comprehend)
    3. **Extraction** : Utilisation de Claude Sonnet pour extraire les data points clés
    4. **Résultat** : Affichage structuré avec :
       - Titre et date du document
       - Secteurs affectés
       - Exigences clés
       - Pénalités
       - Confiance LegalBERT
    
    ### Filtres disponibles
    - Filtrer par statut (Tous, Analysés, Non analysés)
    - Supprimer des résultats d'extraction
    """)
    
    st.markdown("---")
    
    # Analyse d'Impact
    st.markdown("## 📈 Analyse d'Impact")
    st.markdown("""
    La page **Analyse d'Impact** évalue l'impact des réglementations sur le portefeuille S&P 500.
    
    ### Fonctionnalités
    - 🎯 **Sélection de réglementation** : Choisir parmi les réglementations analysées
    - 📊 **Métriques d'impact** :
      - Nombre d'entreprises affectées
      - Score de risque global
      - Impact financier estimé
      - Secteurs exposés
    
    ### Visualisations
    - 📈 **Graphiques d'impact par entreprise** : Top 10 des entreprises les plus impactées
    - 🎨 **Carte de chaleur** : Colorisation selon l'intensité de l'impact
    
    ### Processus
    1. Sélectionner une réglementation depuis la liste
    2. Cliquer sur "Analyser l'Impact"
    3. Visualiser les métriques et graphiques générés
    
    ⚠️ **Note** : Cette fonctionnalité est en cours de développement avancé pour intégrer des calculs d'impact réels basés sur les extractions de documents.
    """)
    
    st.markdown("---")
    
    # Chatbot Financier
    st.markdown("## 🤖 Chatbot Financier")
    st.markdown("""
    Le **Chatbot Financier** utilise la technologie **RAG (Retrieval Augmented Generation)** pour répondre à vos questions
    basées sur la base de connaissances de l'application.
    
    ### Fonctionnalités RAG
    - 🔍 **Recherche sémantique** : Trouve les documents pertinents via embeddings
    - 📚 **Base de connaissances** : Contient :
      - Extraits de documents réglementaires
      - Extraits de 10-K filings
      - Données du Company Universe
    - 💬 **Réponses contextuelles** : Génération de réponses basées sur les documents trouvés
    
    ### Technologies utilisées
    - **LangChain** : Framework pour applications LLM
    - **FAISS** : Vector store pour recherche sémantique performante
    - **AWS Bedrock** :
      - **Embeddings** : Cohere Embed v4 (`global.cohere.embed-v4:0`)
      - **LLM** : Claude Sonnet 4.5 (`global.anthropic.claude-sonnet-4-5-20250929-v1:0`)
    
   ### Utilisation
    1. Tapez votre question dans le champ de saisie
    2. Ou cliquez sur une question d'exemple
    3. Le chatbot recherche dans la base de connaissances
    4. Affiche la réponse avec les sources utilisées
    
    ### Exemples de questions
    - "Quel est l'impact de l'EU AI Act sur les entreprises tech du S&P 500 ?"
    - "Quelles entreprises sont le plus exposées aux réglementations chinoises ?"
    - "Compare l'impact de deux réglementations sur le portefeuille"
    """)
    
    st.markdown("---")
    
    # Architecture Technique
    st.markdown("## 🔧 Architecture Technique")
    st.markdown("""
    ### Stack Technologique
    
    #### Frontend
    - **Streamlit** : Interface utilisateur interactive
    - **Plotly** : Graphiques interactifs
    - **Pandas** : Manipulation de données
    
    #### Backend & IA
    - **Python 3.x** : Langage principal
    - **LangChain** : Framework RAG
    - **FAISS** : Vector store (recherche sémantique)
    
    #### AWS Services
    - **Amazon S3** : Stockage de données
    - **Amazon Bedrock** : Modèles LLM et embeddings
      - Claude Sonnet 4.5 (génération)
      - Cohere Embed v4 (embeddings)
    - **Amazon Textract** : Extraction de texte (PDF, images)
    - **Amazon Comprehend** : NLP et classification
    - **Amazon DynamoDB** : Base de données (si utilisée)
    
    #### Données
    - **Company Universe JSON** : 500 entreprises S&P 500
    - **Documents réglementaires** : Stockés localement et dans S3
    - **Extractions** : Résultats d'analyse stockés en JSON
    
    ### Structure du Projet
    ```
    Datathon2025/
    ├── scripts/
    │   ├── app.py                    # Application Streamlit principale
    │   ├── dashboard_helper.py        # Helpers pour Dashboard
    │   ├── document_analysis_helper.py  # Extraction de documents
    │   ├── impact_orchestrator.py     # Analyse d'impact
    │   ├── chatbot_helper.py          # Chatbot basique
    │   ├── rag/                       # Module RAG
    │   │   ├── config.py              # Configuration RAG
    │   │   ├── data_loader.py         # Chargement données
    │   │   ├── embeddings.py           # Embeddings Bedrock
    │   │   ├── vector_store.py        # FAISS vector store
    │   │   ├── rag_chain.py           # Chaîne RAG LangChain
    │   │   └── rag_helper.py          # Orchestrateur RAG
    │   └── aws_services_helper.py      # Helpers AWS
    ├── notebooks/                     # Notebooks Jupyter
    ├── data/                          # Données locales
    ├── documents/                     # Documents réglementaires
    └── .env                           # Variables d'environnement AWS
    ```
    """)
    
    st.markdown("---")
    
    # Configuration
    st.markdown("## ⚙️ Configuration")
    st.markdown("""
    ### Variables d'environnement (.env)
    
    L'application nécessite un fichier `.env` à la racine avec :
    ```env
    AWS_ACCESS_KEY_ID=your_access_key
    AWS_SECRET_ACCESS_KEY=your_secret_key
    AWS_SESSION_TOKEN=your_session_token  # Si credentials temporaires
    AWS_DEFAULT_REGION=us-west-2
    AWS_REGION=us-west-2
    S3_BUCKET_NAME=your_bucket_name
    ```
    
    ### Installation des dépendances
    ```bash
    pip install -r requirements.txt
    ```
    
    ### Lancement de l'application
    ```bash
    python -m streamlit run scripts/app.py
    ```
    
    L'application sera accessible sur `http://localhost:8501`
    
    ### Permissions AWS requises
    - **Bedrock** : Accès aux modèles Claude et Cohere
    - **S3** : Lecture/Écriture sur le bucket
    - **Textract** : Extraction de texte depuis documents
    - **Comprehend** : Analyse NLP
    """)
    
    st.markdown("---")
    
    # Sources de Données
    st.markdown("## 📊 Sources de Données")
    st.markdown("""
    ### 1. Company Universe
    - **Format** : JSON (`data/company_universe.json`)
    - **Contenu** : 500 entreprises S&P 500
    - **Champs principaux** :
      - Composition : Symbol, Company, Weight, Price, Sector, Industry
      - Performance : Market Cap, Revenue, Op. Income, Net Income, EPS, FCF, P/E Ratio, Profit Margin
      - Opérations : Has NA Operations, Has EU Operations, Num Segments, Company Type
    
    ### 2. Documents Réglementaires
    - **Localisation** : `documents/`
    - **Formats supportés** : HTML, XML, PDF, TXT
    - **Traitement** : Extraction via AWS services
    
    ### 3. Extractions 10-K
    - **Format** : JSON
    - **Contenu** : Data points extraits des filings 10-K
    - **Usage** : Intégré dans la base de connaissances RAG
    
    ### 4. Extraits Réglementaires
    - **Format** : JSON
    - **Contenu** : Data points extraits des documents réglementaires
    - **Usage** : Base de connaissances RAG + Analyse d'Impact
    """)
    
    st.markdown("---")
    
    # FAQ
    st.markdown("## ❓ FAQ")
    
    faq_items = [
        {
            "question": "Comment charger les données du Dashboard ?",
            "reponse": "Les données se chargent automatiquement au démarrage. Si besoin, utilisez le bouton 'Rafraîchir les données' dans le Dashboard."
        },
        {
            "question": "Pourquoi le RAG ne fonctionne pas ?",
            "reponse": "Vérifiez vos credentials AWS dans le fichier `.env`. Le RAG nécessite un accès à Bedrock pour les embeddings et le LLM."
        },
        {
            "question": "Combien de temps prend l'analyse d'un document ?",
            "reponse": "L'analyse complète prend généralement 1-3 minutes selon la taille du document et la complexité de l'extraction."
        },
        {
            "question": "Les données sont-elles stockées dans le cloud ?",
            "reponse": "Les documents peuvent être stockés dans S3, mais par défaut, les données sont stockées localement. Les extractions sont sauvegardées localement en JSON."
        },
        {
            "question": "Puis-je utiliser mes propres modèles ?",
            "reponse": "L'application utilise actuellement les modèles Bedrock disponibles dans votre région. Vous pouvez modifier les identifiants de modèles dans `scripts/rag/config.py`."
        },
        {
            "question": "Comment puis-je ajouter de nouveaux documents ?",
            "reponse": "Utilisez la section 'Upload Nouveau Document' dans la page 'Analyse de Documents'. Les documents seront ensuite disponibles pour analyse."
        },
        {
            "question": "Le chatbot utilise-t-il Internet ?",
            "reponse": "Non, le chatbot RAG fonctionne uniquement avec votre base de connaissances locale (extractions réglementaires, 10-K, Company Universe). Il ne fait pas de recherches externes."
        },
        {
            "question": "Comment améliorer les réponses du RAG ?",
            "reponse": "Ajoutez plus de documents réglementaires et d'extractions 10-K à votre base de connaissances. Plus la base est riche, meilleures sont les réponses."
        }
    ]
    
    for idx, faq in enumerate(faq_items, 1):
        with st.expander(f"**Q{idx}** : {faq['question']}"):
            st.markdown(faq['reponse'])
    
    st.markdown("---")
    
    # Contact et Support
    st.markdown("## 📞 Support")
    st.markdown("""
    Pour toute question ou problème technique, consultez la documentation du projet ou contactez l'équipe de développement.
    """)




