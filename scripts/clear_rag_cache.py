"""
Script pour supprimer le cache RAG et forcer sa régénération
Utile après avoir modifié le formatage des données dans data_loader.py
"""

import sys
from pathlib import Path
import shutil

# Ajouter le répertoire parent au path
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# Définir le chemin du cache directement pour éviter les imports problématiques
CACHE_PATH = BASE_DIR / 'data' / 'generated' / 'rag_cache' / 'vector_store'

def clear_rag_cache():
    """Supprime le cache RAG pour forcer sa régénération"""
    cache_path = CACHE_PATH
    
    if cache_path.exists():
        print(f"Suppression du cache RAG: {cache_path}")
        shutil.rmtree(cache_path)
        print("Cache supprime avec succes")
        print("Le prochain demarrage de l'app Streamlit regenerera le cache avec les nouvelles donnees")
    else:
        print("Aucun cache a supprimer")

if __name__ == "__main__":
    clear_rag_cache()

