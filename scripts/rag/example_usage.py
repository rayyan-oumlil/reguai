"""
Exemple d'utilisation du module RAG
Montre comment intégrer dans Streamlit ou utiliser standalone
"""

# ============================================
# EXEMPLE 1 : Utilisation Standalone
# ============================================

def example_standalone():
    """Exemple d'utilisation standalone (hors Streamlit)"""
    
    from scripts.rag import initialize_rag_system, chat_with_rag
    
    # 1. Initialiser le système
    print("Initialisation...")
    result = initialize_rag_system(
        use_cache=True,
        tenk_limit=50  # MVP : seulement 50 fichiers 10-K
    )
    
    if not result['success']:
        print(f"❌ Erreur: {result['error']}")
        return
    
    print(f"✅ {result['message']}")
    
    # 2. Poser des questions
    questions = [
        "Quel est l'impact de l'EU AI Act sur les entreprises tech ?",
        "Quelles entreprises opèrent en Chine ?",
        "Explique-moi le Inflation Reduction Act"
    ]
    
    for question in questions:
        print(f"\n📝 Question: {question}")
        response = chat_with_rag(question, return_sources=True)
        
        if response['error']:
            print(f"❌ Erreur: {response['error']}")
        else:
            print(f"✅ Réponse: {response['answer'][:200]}...")
            print(f"📚 Sources: {len(response['sources'])} documents utilisés")


# ============================================
# EXEMPLE 2 : Intégration Streamlit
# ============================================

def example_streamlit_integration():
    """
    Code à ajouter dans scripts/app.py dans la page Chatbot
    
    À ajouter dans la section "🤖 Chatbot Financier"
    """
    
    streamlit_code = '''
import streamlit as st
from scripts.rag import initialize_rag_system, chat_with_rag, get_rag_stats

# Dans la page Chatbot
if page == "🤖 Chatbot Financier":
    st.header("🤖 Chatbot Financier avec RAG")
    
    # Initialiser RAG au chargement (avec cache Streamlit)
    @st.cache_resource
    def init_rag():
        return initialize_rag_system(use_cache=True, tenk_limit=100)
    
    # Initialiser si pas déjà fait
    if 'rag_initialized' not in st.session_state:
        with st.spinner("🚀 Initialisation système RAG..."):
            result = init_rag()
            if result['success']:
                st.session_state.rag_initialized = True
                st.success(result['message'])
            else:
                st.error(f"Erreur: {result['error']}")
                st.stop()
    
    # Afficher stats
    stats = get_rag_stats()
    if stats['initialized']:
        st.sidebar.info("✅ RAG initialisé")
    
    # Interface chat
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Afficher historique
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            
            # Afficher sources si disponibles
            if message["role"] == "assistant" and "sources" in message:
                with st.expander("📚 Sources utilisées"):
                    for source in message["sources"][:3]:  # Top 3 sources
                        st.write(f"**[{source['type']}]** {source.get('title', source.get('company_name', ''))}")
    
    # Input utilisateur
    if prompt := st.chat_input("Posez votre question..."):
        # Ajouter message utilisateur
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Générer réponse avec RAG
        with st.chat_message("assistant"):
            with st.spinner("🤔 Recherche dans la base de connaissances..."):
                response = chat_with_rag(prompt, return_sources=True)
                
                if response['error']:
                    st.error(f"Erreur: {response['error']}")
                else:
                    # Afficher réponse
                    st.markdown(response['answer'])
                    
                    # Afficher sources
                    if response['sources']:
                        st.caption(f"📚 {len(response['sources'])} sources utilisées")
                    
                    # Ajouter à historique
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": response['answer'],
                        "sources": response['sources']
                    })
'''
    
    print("Code Streamlit à intégrer:")
    print(streamlit_code)


# ============================================
# EXEMPLE 3 : Test Rapide
# ============================================

if __name__ == "__main__":
    # Exécuter exemple standalone
    example_standalone()

