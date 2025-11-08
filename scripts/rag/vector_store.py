"""
Gestion du Vector Store FAISS avec LangChain
"""

from pathlib import Path
from typing import List, Optional

# Import Document from langchain (compatible versions)
try:
    from langchain_core.documents import Document
except ImportError:
    try:
        from langchain.documents import Document
    except ImportError:
        from langchain.schema import Document

from langchain_community.vectorstores import FAISS
from langchain_aws import BedrockEmbeddings
from scripts.rag.config import DATA_PATHS, RAG_CONFIG
from scripts.rag.embeddings import get_embeddings_instance


class RAGVectorStore:
    """
    Classe wrapper pour gérer le vector store FAISS avec cache
    """
    
    def __init__(self, embeddings: Optional[BedrockEmbeddings] = None):
        """
        Initialise le RAG Vector Store
        
        Args:
            embeddings: Instance BedrockEmbeddings (si None, crée une nouvelle)
        """
        self.embeddings = embeddings or get_embeddings_instance()
        self.vector_store: Optional[FAISS] = None
        self.cache_path = DATA_PATHS['vector_store_cache']
    
    def create_from_documents(self, documents: List[Document]) -> None:
        """
        Crée le vector store depuis une liste de Documents
        
        Args:
            documents: Liste de Documents LangChain
        """
        if not documents:
            return
        
        print(f"📚 Création vector store FAISS avec {len(documents)} documents...")
        self.vector_store = FAISS.from_documents(
            documents=documents,
            embedding=self.embeddings
        )
        print(f"✅ Vector store créé avec succès")
    
    def load_from_cache(self) -> bool:
        """
        Charge le vector store depuis le cache (si disponible)
        
        Returns:
            True si chargé avec succès, False sinon
        """
        cache_dir = self.cache_path
        
        if not cache_dir.exists():
            return False
        
        try:
            self.vector_store = FAISS.load_local(
                str(cache_dir),
                self.embeddings,
                allow_dangerous_deserialization=True  # Nécessaire pour FAISS
            )
            print(f"✅ Vector store chargé depuis cache")
            return True
        except Exception as e:
            print(f"⚠️ Erreur chargement cache: {e}")
            return False
    
    def save_to_cache(self) -> None:
        """
        Sauvegarde le vector store dans le cache
        """
        if self.vector_store is None:
            return
        
        cache_dir = self.cache_path
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            print(f"💾 Sauvegarde vector store dans cache...")
            self.vector_store.save_local(str(cache_dir))
            print("✅ Vector store sauvegardé")
        except Exception as e:
            print(f"⚠️ Erreur sauvegarde cache: {e}")
    
    def search(self, query: str, top_k: int = None) -> List[Document]:
        """
        Recherche dans le vector store
        
        Args:
            query: Question/requête utilisateur
            top_k: Nombre de résultats (défaut: RAG_CONFIG['top_k'])
        
        Returns:
            Liste de Documents similaires avec scores
        """
        if self.vector_store is None:
            pass  # Vector store non initialisé
            return []
        
        top_k = top_k or RAG_CONFIG['top_k']
        
        # Recherche similarité avec LangChain
        results = self.vector_store.similarity_search_with_score(
            query=query,
            k=top_k
        )
        
        # Extraire seulement les documents (avec scores dans metadata si besoin)
        documents = []
        for doc, score in results:
            # Filtrer par threshold si nécessaire
            similarity_score = 1 / (1 + score) if score > 0 else 1.0  # Convertir distance en similarité
            
            if similarity_score >= RAG_CONFIG['similarity_threshold']:
                # Ajouter score dans metadata
                doc.metadata['similarity_score'] = similarity_score
                documents.append(doc)
        
        return documents
    
    def add_documents(self, documents: List[Document]) -> None:
        """
        Ajoute de nouveaux documents au vector store existant
        
        Args:
            documents: Liste de nouveaux Documents
        """
        if self.vector_store is None:
            self.create_from_documents(documents)
        else:
            self.vector_store.add_documents(documents)
            # Documents ajoutés
    
    def get_retriever(self, top_k: int = None):
        """
        Retourne un retriever LangChain pour utiliser dans chains
        
        Args:
            top_k: Nombre de résultats
        
        Returns:
            Retriever LangChain
        """
        if self.vector_store is None:
            raise ValueError("Vector store non initialisé")
        
        top_k = top_k or RAG_CONFIG['top_k']
        
        return self.vector_store.as_retriever(
            search_kwargs={"k": top_k}
        )
    
    def get_stats(self) -> dict:
        """
        Retourne des statistiques sur le vector store
        
        Returns:
            Dictionnaire avec stats
        """
        if self.vector_store is None:
            return {'initialized': False}
        
        # Compter documents par type depuis index
        # Note: FAISS ne stocke pas directement les métadonnées, on ne peut pas facilement
        # compter sans les documents originaux. Pour MVP, on retourne juste l'état.
        return {
            'initialized': True,
            'cache_path': str(self.cache_path),
            'cache_exists': self.cache_path.exists()
        }

