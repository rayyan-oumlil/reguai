# 🚀 ReguAI - Regulatory Intelligence Assistant
# Datathon PolyFinances 2025
# Application Streamlit principale

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from datetime import datetime
import json
import os

# Charger la configuration depuis .env si disponible
try:
    from dotenv import load_dotenv
    env_path = Path('.env')
    if env_path.exists():
        load_dotenv(env_path)
        # Afficher la configuration chargée dans la sidebar (optionnel)
        if os.environ.get('S3_BUCKET_NAME'):
            st.sidebar.success(f"☁️ S3: {os.environ.get('S3_BUCKET_NAME')}")
except ImportError:
    pass  # python-dotenv non installé, ce n'est pas critique
except Exception as e:
    pass  # Erreur silencieuse si .env ne peut pas être chargé

# Import helpers
from scripts.document_analysis_helper import (
    extract_from_uploaded_file,
    extract_from_local_file,
    load_existing_extractions,
    generate_filename_from_extraction,
    delete_extraction,
    toggle_document_visibility,
    get_all_documents_with_status,
    save_uploaded_file
)
from scripts.dashboard_helper import (
    load_company_universe,
    company_universe_to_dataframes,
    render_dashboard_kpis,
    render_sector_treemap,
    render_composition_charts,
    render_performance_table,
    render_composition_table
)
from scripts.chatbot_helper import (
    chat_with_claude,
    format_chat_message,
    get_example_questions
)

# Configuration de la page
st.set_page_config(
    page_title="ReguAI - Regulatory Intelligence Assistant",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    </style>
""", unsafe_allow_html=True)

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

# Sidebar - Navigation
st.sidebar.title("🧭 Navigation")
page = st.sidebar.selectbox(
    "Choisir une page",
    ["🏠 Dashboard", "📊 Analyse", "🤖 Chatbot Financier"]
)

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
                    st.success("✅ Company Universe chargé avec succès ! (Market Data + 10-K Filings)")
                else:
                    st.error("❌ Erreur lors de la conversion du Company Universe")
            else:
                st.error("❌ Company Universe non trouvé. Vérifiez que company_universe.json existe.")
                st.info("💡 Le Company Universe contient les données fusionnées de Market Data et 10-K Filings")
    
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

# PAGE 2: Analyse (Documents + Impact)
elif page == "📊 Analyse":
    st.header("📊 Analyse de Documents et d'Impact Réglementaire")
    
    # Onglets principaux : Analyse de Documents et Analyse d'Impact
    main_tab1, main_tab2 = st.tabs(["📄 Analyse de Documents", "📈 Analyse d'Impact"])
    
    # TAB PRINCIPAL 1: Analyse de Documents
    with main_tab1:
        # Check for completed extractions first
        needs_refresh = _check_running_extractions()
        
        # Note: Extractions process immediately when triggered (Streamlit limitation)
        # We check for completion on each page load
        
        st.subheader("📄 Analyse de Documents Réglementaires")
        st.info("💡 Uploadez ou analysez des documents réglementaires pour extraire automatiquement les informations clés")
        
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
                st.success(f"✅ Fichier '{uploaded_file.name}' sélectionné")
                st.caption(f"Taille: {uploaded_file.size / 1024:.1f} KB")
                
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
        
        # Filter options
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            filter_status = st.selectbox(
                "Filtrer par statut",
                ["Tous", "Analysés", "Non analysés"],
                key="filter_status"
            )
        with col2:
            show_hidden = st.checkbox("Afficher documents masqués", value=False, key="show_hidden")
        with col3:
            st.write("")  # Spacer
        
        # Get all documents with status
        all_documents = get_all_documents_with_status()
        
        # Apply filters
        filtered_docs = []
        for doc in all_documents:
            # Status filter
            if filter_status == "Analysés" and doc['status'] != 'analyzed':
                continue
            elif filter_status == "Non analysés" and doc['status'] == 'analyzed':
                continue
            
            # Hidden filter
            if doc['is_hidden'] and not show_hidden:
                continue
            
            filtered_docs.append(doc)
        
        if filtered_docs:
            st.info(f"📊 {len(filtered_docs)} document(s) trouvé(s)")
            
            # Display as table with actions
            for idx, doc in enumerate(filtered_docs):
                with st.container():
                    # Create columns for document info and actions
                    col_info, col_date, col_status, col_actions = st.columns([3, 2, 1.5, 2.5])
                    
                    with col_info:
                        # Document name with icon
                        icon = "📄" if not doc['is_hidden'] else "👁️‍🗨️"
                        
                        # Get display name: use extracted title if available, otherwise use filename
                        display_name = doc['filename']
                        original_filename = doc['filename']  # Keep for duplicate detection
                        
                        if doc['status'] == 'analyzed' and doc.get('extraction') and doc['extraction'].get('data'):
                            extracted_info = doc['extraction']['data'].get('extracted_info', {})
                            title = extracted_info.get('title', '')
                            if title:
                                display_name = title
                        
                        # Display the title (or filename if not analyzed)
                        st.markdown(f"**{icon} {display_name}**")
                        
                        # Show file info: size and original filename (hidden but accessible)
                        if display_name != original_filename:
                            # Show original filename in small text for reference/duplicate detection
                            st.caption(f"📁 {original_filename} • {doc['size'] / 1024:.1f} KB")
                        else:
                            st.caption(f"{doc['size'] / 1024:.1f} KB")
                    
                    with col_date:
                        upload_date_str = doc['upload_date'].strftime("%Y-%m-%d %H:%M")
                        st.text(f"📅 {upload_date_str}")
                    
                    with col_status:
                        if doc['status'] == 'analyzed':
                            st.success("✅ Analysé")
                        else:
                            st.warning("⏳ Non analysé")
                    
                    with col_actions:
                        # Action buttons in a row
                        action_col1, action_col2, action_col3 = st.columns(3)
                        
                        with action_col1:
                            # Analyze button
                            if doc['status'] != 'analyzed':
                                if st.button("🔍", key=f"analyze_{idx}", help="Analyser ce document"):
                                    # Process immediately with clear feedback
                                    progress_msg = st.empty()
                                    with progress_msg.container():
                                        st.warning(f"⏳ Analyse de '{doc['filename']}' en cours...")
                                        st.caption("⏱️ Cela peut prendre 1-3 minutes. Vous pouvez continuer à naviguer dans l'application.")
                                    
                                    try:
                                        result = extract_from_local_file(
                                            doc['path'], 
                                            use_cache=True, 
                                            use_aws_services=True
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
                            # View/Delete extraction results
                            if doc['status'] == 'analyzed' and doc['extraction']:
                                if st.button("🗑️", key=f"delete_ext_{idx}", help="Supprimer résultat"):
                                    if delete_extraction(doc['extraction']['path'], doc['extraction']['source']):
                                        st.success("✅ Résultat supprimé")
                                        st.rerun()
                                    else:
                                        st.error("❌ Erreur lors de la suppression")
                        
                        with action_col3:
                            # Hide/Show toggle
                            hide_label = "👁️" if doc['is_hidden'] else "👁️‍🗨️"
                            hide_help = "Afficher" if doc['is_hidden'] else "Masquer"
                            if st.button(hide_label, key=f"toggle_{idx}", help=hide_help):
                                toggle_document_visibility(doc['filename'], hide=not doc['is_hidden'])
                                st.rerun()
                    
                    # Expandable section for viewing results
                    if doc['status'] == 'analyzed' and doc['extraction']:
                        with st.expander("📋 Voir les résultats d'extraction"):
                            data = doc['extraction']['data']
                            if data.get('processing_status') == 'completed':
                                _display_extraction_results(data)
                            else:
                                st.error(f"❌ Statut: {data.get('processing_status', 'unknown')}")
                                if 'error' in data:
                                    st.error(f"Erreur: {data['error']}")
                    
                    st.divider()
        else:
            st.info("Aucun document trouvé. Uploadez un document pour commencer.")
    
    # TAB PRINCIPAL 2: Analyse d'Impact
    with main_tab2:
        st.subheader("📈 Analyse d'Impact Réglementaire sur le Portefeuille")
        st.info("💡 Cette section permet d'analyser l'impact des réglementations extraites sur le S&P 500")
        
        if st.session_state.data_loaded:
            composition = st.session_state.composition_sp500
            performance = st.session_state.stocks_performance
            
            # Sélection d'une réglementation
            st.subheader("Sélectionner une Réglementation")
            regulations = [
                "EU AI Act (12 juillet 2024)",
                "Loi énergétique chinoise (9 novembre 2024)",
                "Inflation Reduction Act (16 août 2022)",
                "Directive UE 2019/2161"
            ]
            selected_reg = st.selectbox("Choisir une réglementation", regulations)
            
            if st.button("🔍 Analyser l'Impact", type="primary"):
                st.success(f"Analyse de '{selected_reg}' en cours...")
                
                # Placeholder pour les résultats
                col1, col2 = st.columns(2)
                
                with col1:
                    st.metric("Entreprises affectées", "127", delta="25.2%")
                    st.metric("Score de risque global", "62/100", delta="Moyen")
                
                with col2:
                    st.metric("Impact financier estimé", "-2.34%", delta="Négatif")
                    st.metric("Secteurs exposés", "5", delta="Tech, Energie, ...")
                
                # Graphique d'impact simulé
                st.subheader("Impact Simulé par Entreprise (Top 10)")
                # Données d'exemple
                impact_data = pd.DataFrame({
                    'Symbol': composition.head(10)['Symbol'].tolist(),
                    'Impact_Score': np.random.randint(20, 95, 10),
                    'Impact_Percent': np.random.uniform(-15, 5, 10)
                })
                
                fig = px.bar(
                    impact_data,
                    x='Symbol',
                    y='Impact_Score',
                    title='Score d\'Impact par Entreprise',
                    labels={'Impact_Score': 'Score d\'Impact', 'Symbol': 'Symbole'},
                    color='Impact_Percent',
                    color_continuous_scale='RdYlGn_r'
                )
                st.plotly_chart(fig, width='stretch')
                
                st.info("⚠️ Fonctionnalité d'analyse d'impact en cours de développement")
        else:
            st.warning("⚠️ Veuillez d'abord charger les données depuis le Dashboard")

# PAGE 3: Chatbot Financier
elif page == "🤖 Chatbot Financier":
    st.header("🤖 Financial Chatbot")
    st.info("💡 Interface conversationnelle pour poser des questions sur les réglementations et les entreprises")
    
    # Initialisation de l'historique de chat
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    # Afficher l'historique
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Input utilisateur
    if prompt := st.chat_input("Posez votre question sur les réglementations ou les entreprises..."):
        # Ajouter le message utilisateur
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Réponse via Bedrock
        with st.chat_message("assistant"):
            with st.spinner("🤔 Réflexion en cours..."):
                # Convertir l'historique au format Claude
                claude_messages = [
                    format_chat_message(msg["role"], msg["content"])
                    for msg in st.session_state.messages
                ]
                
                # Appel à Claude
                result = chat_with_claude(claude_messages)
                
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
        
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Exemples de questions
    st.subheader("💡 Exemples de questions")
    example_questions = get_example_questions()
    for q in example_questions:
        if st.button(q, key=f"example_{q}"):
            st.session_state.messages.append({"role": "user", "content": q})
            st.rerun()


# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p><strong>ReguAI</strong> - Regulatory Intelligence Assistant</p>
    <p>Datathon PolyFinances 2025 | Transformant la complexité réglementaire en décisions stratégiques</p>
</div>
""", unsafe_allow_html=True)

