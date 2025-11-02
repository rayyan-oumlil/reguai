"""
Data Loader pour RAG
Charge et prépare les données depuis les fichiers JSON générés
"""

import json
from pathlib import Path
from typing import List, Dict, Any

# Import Document from langchain (compatible versions)
try:
    from langchain_core.documents import Document
except ImportError:
    try:
        from langchain.documents import Document
    except ImportError:
        from langchain.schema import Document

from scripts.rag.config import DATA_PATHS, RAG_CONFIG, CHUNKING_PATTERNS


def load_regulatory_extractions() -> List[Dict[str, Any]]:
    """
    Charge toutes les extractions réglementaires depuis les fichiers JSON
    
    Returns:
        Liste de dictionnaires avec les données extraites
    """
    extractions = []
    regulatory_dir = DATA_PATHS['regulatory_extractions']
    
    if not regulatory_dir.exists():
        print(f"⚠️ Dossier réglementations non trouvé: {regulatory_dir}")
        return []
    
    # Charger tous les fichiers *_extracted.json
    for json_file in regulatory_dir.glob("*_extracted.json"):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ajouter métadonnées
                data['source_file'] = json_file.name
                data['data_type'] = 'regulation'
                extractions.append(data)
        except Exception as e:
            print(f"⚠️ Erreur chargement {json_file}: {e}")
    
    print(f"✅ {len(extractions)} extractions réglementaires chargées")
    return extractions


def load_10k_extractions(limit: int = None) -> List[Dict[str, Any]]:
    """
    Charge les extractions 10-K depuis les fichiers JSON
    
    Args:
        limit: Limite le nombre de fichiers à charger (None = tous)
    
    Returns:
        Liste de dictionnaires avec les données 10-K
    """
    tenk_extractions = []
    tenk_dir = DATA_PATHS['tenk_extractions']
    
    if not tenk_dir.exists():
        print(f"⚠️ Dossier 10-K non trouvé: {tenk_dir}")
        return []
    
    # Charger fichiers JSON (limit si spécifié)
    json_files = list(tenk_dir.glob("*.json"))
    if limit:
        json_files = json_files[:limit]
    
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Ajouter métadonnées
                data['source_file'] = json_file.name
                data['data_type'] = '10k'
                tenk_extractions.append(data)
        except Exception as e:
            print(f"⚠️ Erreur chargement {json_file}: {e}")
    
    print(f"✅ {len(tenk_extractions)} extractions 10-K chargées")
    return tenk_extractions


def load_company_universe() -> Dict[str, Any]:
    """
    Charge le Company Universe consolidé
    
    Returns:
        Dictionnaire avec les données Company Universe
    """
    company_universe_path = DATA_PATHS['company_universe']
    
    if not company_universe_path.exists():
        print(f"⚠️ Company Universe non trouvé: {company_universe_path}")
        return {}
    
    try:
        with open(company_universe_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            data['data_type'] = 'company_universe'
            print(f"✅ Company Universe chargé ({len(data.get('companies', []))} entreprises)")
            return data
    except Exception as e:
        print(f"⚠️ Erreur chargement Company Universe: {e}")
        return {}


def format_regulation_as_text(regulation_data: Dict[str, Any]) -> str:
    """Formate une extraction réglementaire en texte pour embedding"""
    parts = []
    
    if title := regulation_data.get('extracted_info', {}).get('title'):
        parts.append(f"Réglementation: {title}")
    
    if country := regulation_data.get('extracted_info', {}).get('country'):
        parts.append(f"Pays/Juridiction: {country}")
    
    if sectors := regulation_data.get('extracted_info', {}).get('affected_sectors', []):
        parts.append(f"Secteurs concernés: {', '.join(sectors)}")
    
    if entities := regulation_data.get('extracted_info', {}).get('affected_entities', []):
        parts.append(f"Entités mentionnées: {', '.join(entities[:10])}")  # Limiter pour taille
    
    if requirements := regulation_data.get('extracted_info', {}).get('key_requirements', []):
        parts.append(f"Exigences clés: {'; '.join(requirements[:5])}")
    
    if effective_date := regulation_data.get('extracted_info', {}).get('effective_date'):
        parts.append(f"Date d'entrée en vigueur: {effective_date}")
    
    return "\n".join(parts)


def format_10k_as_text(tenk_data: Dict[str, Any]) -> str:
    """Formate une extraction 10-K en texte pour embedding"""
    parts = []
    
    ticker = tenk_data.get('ticker', 'N/A')
    company_name = tenk_data.get('company_name', 'N/A')
    parts.append(f"Entreprise: {company_name} ({ticker})")
    
    # Géographie
    if geography := tenk_data.get('geography', {}):
        if regions := geography.get('regions', []):
            parts.append(f"Régions d'opération: {', '.join(regions)}")
        if countries := geography.get('countries', []):
            parts.append(f"Pays d'opération: {', '.join(countries[:10])}")
    
    # Segments
    if segments := tenk_data.get('segments', []):
        parts.append(f"Segments d'affaires: {', '.join(segments[:10])}")
    
    # Supply Chain
    if supply_chain := tenk_data.get('supply_chain', {}):
        if suppliers := supply_chain.get('key_suppliers', []):
            parts.append(f"Fournisseurs clés: {', '.join(suppliers[:5])}")
        if locations := supply_chain.get('manufacturing_locations', []):
            parts.append(f"Sites de production: {', '.join(locations[:5])}")
    
    return "\n".join(parts)


def format_company_universe_as_text(company_data: Dict[str, Any]) -> str:
    """Formate une entreprise du Company Universe en texte pour embedding"""
    parts = []
    
    ticker = company_data.get('ticker', 'N/A')
    company_name = company_data.get('company_name', 'N/A')
    parts.append(f"Entreprise: {company_name} ({ticker})")
    
    # Market Data
    if market_data := company_data.get('market_data', {}):
        if market_cap := market_data.get('market_cap'):
            parts.append(f"Market Cap: ${market_cap:,.0f}")
        if revenue := market_data.get('revenue'):
            parts.append(f"Revenue: ${revenue:,.0f}")
        if weight := market_data.get('weight'):
            parts.append(f"Poids S&P 500: {weight}%")
    
    # Data Points (géographie, segments)
    if data_points := company_data.get('data_points', {}):
        if geography := data_points.get('geography', {}):
            if regions := geography.get('regions', []):
                parts.append(f"Régions: {', '.join(regions[:5])}")
        if segments := data_points.get('segments', []):
            parts.append(f"Segments: {', '.join(segments[:5])}")
    
    return "\n".join(parts)


def create_documents_from_data(
    regulatory_data: List[Dict] = None,
    tenk_data: List[Dict] = None,
    company_universe: Dict = None
) -> List[Document]:
    """
    Crée des Documents LangChain à partir des données chargées
    
    Args:
        regulatory_data: Liste des extractions réglementaires
        tenk_data: Liste des extractions 10-K
        company_universe: Company Universe dict
    
    Returns:
        Liste de Documents LangChain avec métadonnées
    """
    documents = []
    
    # Documents réglementaires
    if regulatory_data:
        for reg in regulatory_data:
            text = format_regulation_as_text(reg)
            if text:
                doc = Document(
                    page_content=text,
                    metadata={
                        'type': 'regulation',
                        'source': reg.get('source_file', 'unknown'),
                        'title': reg.get('extracted_info', {}).get('title', ''),
                        'country': reg.get('extracted_info', {}).get('country', ''),
                    }
                )
                documents.append(doc)
    
    # Documents 10-K
    if tenk_data:
        for tenk in tenk_data:
            text = format_10k_as_text(tenk)
            if text:
                ticker = tenk.get('ticker', 'N/A')
                doc = Document(
                    page_content=text,
                    metadata={
                        'type': '10k',
                        'source': tenk.get('source_file', 'unknown'),
                        'ticker': ticker,
                        'company_name': tenk.get('company_name', ''),
                    }
                )
                documents.append(doc)
    
    # Documents Company Universe
    if company_universe and 'companies' in company_universe:
        for company in company_universe['companies']:
            text = format_company_universe_as_text(company)
            if text:
                ticker = company.get('ticker', 'N/A')
                doc = Document(
                    page_content=text,
                    metadata={
                        'type': 'company_universe',
                        'ticker': ticker,
                        'company_name': company.get('company_name', ''),
                    }
                )
                documents.append(doc)
    
    print(f"✅ {len(documents)} documents LangChain créés")
    return documents

