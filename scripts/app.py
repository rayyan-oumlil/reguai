# 🚀 ReguAI - Regulatory Intelligence Assistant
# Datathon PolyFinances 2025
# Application Streamlit principale

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
import boto3
from datetime import datetime

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

@st.cache_data
def load_sp500_composition():
    """Charge la composition du S&P 500"""
    try:
        df = pd.read_csv('2025-08-15_composition_sp500.csv')
        # Convertir Weight et Price de string (format européen) en float
        if 'Weight' in df.columns:
            df['Weight'] = df['Weight'].astype(str).str.replace(',', '.').astype(float)
        if 'Price' in df.columns:
            df['Price'] = df['Price'].astype(str).str.replace(',', '.').astype(float)
        return df
    except FileNotFoundError:
        st.error("⚠️ Fichier '2025-08-15_composition_sp500.csv' non trouvé")
        return None

@st.cache_data
def load_stocks_performance():
    """Charge les métriques de performance"""
    try:
        df = pd.read_csv('2025-09-26_stocks-performance.csv')
        return df
    except FileNotFoundError:
        st.error("⚠️ Fichier '2025-09-26_stocks-performance.csv' non trouvé")
        return None

# Sidebar - Navigation
st.sidebar.title("🧭 Navigation")
page = st.sidebar.selectbox(
    "Choisir une page",
    ["🏠 Dashboard", "📄 Analyse de Documents", "🤖 Chatbot Financier", "📊 Analyse d'Impact"]
)

# Titre principal
st.markdown('<h1 class="main-header">ReguAI</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Regulatory Intelligence Assistant - Datathon PolyFinances 2025</p>', unsafe_allow_html=True)

# PAGE 1: Dashboard
if page == "🏠 Dashboard":
    st.header("📊 Dashboard - Vue Globale du Portefeuille S&P 500")
    
    # Charger les données
    if not st.session_state.data_loaded:
        with st.spinner("Chargement des données..."):
            st.session_state.composition_sp500 = load_sp500_composition()
            st.session_state.stocks_performance = load_stocks_performance()
            if st.session_state.composition_sp500 is not None and st.session_state.stocks_performance is not None:
                st.session_state.data_loaded = True
                st.success("✅ Données chargées avec succès !")
    
    if st.session_state.data_loaded:
        composition = st.session_state.composition_sp500
        performance = st.session_state.stocks_performance
        
        # KPIs Principaux
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Nombre d'entreprises",
                len(composition),
                delta="503 entreprises"
            )
        
        with col2:
            total_weight = composition['Weight'].sum()
            st.metric(
                "Poids total",
                f"{total_weight:.2%}",
                delta="100% attendu"
            )
        
        with col3:
            avg_weight = composition['Weight'].mean()
            st.metric(
                "Poids moyen",
                f"{avg_weight:.3%}",
                delta="~0.2% par entreprise"
            )
        
        with col4:
            total_companies_perf = len(performance)
            st.metric(
                "Entreprises analysées",
                total_companies_perf,
                delta=f"{len(composition)} attendues"
            )
        
        # Graphiques
        col_left, col_right = st.columns(2)
        
        with col_left:
            st.subheader("Top 10 Entreprises par Poids")
            top10 = composition.nlargest(10, 'Weight')
            fig1 = px.bar(
                top10,
                x='Symbol',
                y='Weight',
                title='Top 10 - Poids dans le S&P 500',
                labels={'Weight': 'Poids (%)', 'Symbol': 'Symbole'},
                color='Weight',
                color_continuous_scale='Blues'
            )
            fig1.update_layout(height=400)
            st.plotly_chart(fig1, use_container_width=True)
        
        with col_right:
            st.subheader("Distribution des Poids")
            fig2 = px.histogram(
                composition,
                x='Weight',
                nbins=50,
                title='Distribution des Poids dans le S&P 500',
                labels={'Weight': 'Poids (%)', 'count': 'Nombre d\'entreprises'}
            )
            fig2.update_layout(height=400)
            st.plotly_chart(fig2, use_container_width=True)
        
        # Tableau détaillé
        st.subheader("📋 Composition Complète du S&P 500")
        search_term = st.text_input("🔍 Rechercher une entreprise", "")
        
        if search_term:
            filtered = composition[
                composition['Company'].str.contains(search_term, case=False) |
                composition['Symbol'].str.contains(search_term, case=False)
            ]
            st.dataframe(
                filtered.sort_values('Weight', ascending=False),
                use_container_width=True,
                height=400
            )
        else:
            st.dataframe(
                composition.sort_values('Weight', ascending=False),
                use_container_width=True,
                height=400
            )
        
        # Métriques de Performance
        st.subheader("💰 Métriques de Performance (Top 20)")
        if len(performance) > 0:
            top_performers = performance.nlargest(20, 'Market Cap')
            st.dataframe(
                top_performers[['Symbol', 'Company Name', 'Market Cap', 'Revenue', 'EPS', 'FCF']],
                use_container_width=True,
                height=400
            )

# PAGE 2: Analyse de Documents
elif page == "📄 Analyse de Documents":
    st.header("📄 Analyse de Documents Réglementaires")
    
    st.info("💡 Cette fonctionnalité permettra d'uploader et d'analyser des documents réglementaires avec Amazon Bedrock")
    
    # Upload de fichiers
    uploaded_file = st.file_uploader(
        "Choisir un document réglementaire",
        type=['html', 'xml', 'pdf', 'txt'],
        help="Formats supportés: HTML, XML, PDF, TXT"
    )
    
    if uploaded_file is not None:
        st.success(f"✅ Fichier '{uploaded_file.name}' chargé")
        
        # Affichage du contenu (exemple)
        if uploaded_file.type == 'text/html' or uploaded_file.name.endswith('.html'):
            content = uploaded_file.read().decode('utf-8')
            st.subheader("Aperçu du document")
            st.text_area("Contenu", content[:2000], height=200)
        
        # Bouton d'analyse (à implémenter avec Bedrock)
        if st.button("🔍 Analyser avec Bedrock", type="primary"):
            with st.spinner("Analyse en cours avec Amazon Bedrock..."):
                st.info("⚠️ Fonctionnalité à implémenter avec Bedrock")
                st.code("""
# Exemple d'extraction avec Bedrock:
import boto3
import instructor
from pydantic import BaseModel

bedrock_client = boto3.client('bedrock-runtime')
client = instructor.from_bedrock(bedrock_client)

class RegulationInfo(BaseModel):
    entities: list[str]
    sectors: list[str]
    countries: list[str]
    measures: list[str]
    dates: dict

result = client.chat.completions.create(
    modelId="global.anthropic.claude-haiku-4-5-20251001-v1:0",
    messages=[{"role": "user", "content": content}],
    response_model=RegulationInfo
)
                """, language="python")
    
    # Documents disponibles
    st.subheader("📚 Documents Réglementaires Disponibles")
    directives_path = Path('directives')
    if directives_path.exists():
        directives = list(directives_path.glob('*.html')) + list(directives_path.glob('*.xml'))
        for doc in directives:
            with st.expander(f"📄 {doc.name}"):
                st.write(f"**Chemin:** `{doc}`")
                if st.button(f"Analyser {doc.name}", key=str(doc)):
                    st.info("Analyse avec Bedrock - À implémenter")

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
        
        # Réponse (exemple - à remplacer par Bedrock)
        with st.chat_message("assistant"):
            response = f"Exemple de réponse pour: {prompt}"
            st.markdown(response)
            st.info("⚠️ Intégration avec Bedrock à implémenter")
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Exemples de questions
    st.subheader("💡 Exemples de questions")
    example_questions = [
        "Quel est l'impact de l'EU AI Act sur les entreprises tech du S&P 500 ?",
        "Quelles entreprises sont le plus exposées aux réglementations chinoises ?",
        "Compare l'impact de deux réglementations sur le portefeuille",
        "Explique-moi pourquoi Nvidia est recommandé à la réduction"
    ]
    for q in example_questions:
        if st.button(q, key=f"example_{q}"):
            st.session_state.messages.append({"role": "user", "content": q})
            st.rerun()

# PAGE 4: Analyse d'Impact
elif page == "📊 Analyse d'Impact":
    st.header("📊 Analyse d'Impact Réglementaire sur le Portefeuille")
    
    st.info("💡 Cette section permettra d'analyser l'impact des réglementations sur le S&P 500")
    
    if st.session_state.data_loaded:
        composition = st.session_state.composition_sp500
        
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
            st.plotly_chart(fig, use_container_width=True)
            
            st.info("⚠️ Intégration avec Bedrock pour calcul réel à implémenter")
    else:
        st.warning("⚠️ Veuillez d'abord charger les données depuis le Dashboard")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p><strong>ReguAI</strong> - Regulatory Intelligence Assistant</p>
    <p>Datathon PolyFinances 2025 | Transformant la complexité réglementaire en décisions stratégiques</p>
</div>
""", unsafe_allow_html=True)

