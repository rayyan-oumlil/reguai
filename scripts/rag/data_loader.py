"""
Data Loader pour RAG
Charge et prépare les données depuis S3 ou fichiers JSON locaux
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

# Import Document from langchain (compatible versions)
try:
    from langchain_core.documents import Document
except ImportError:
    try:
        from langchain.documents import Document
    except ImportError:
        from langchain.schema import Document

from scripts.rag.config import DATA_PATHS, RAG_CONFIG, CHUNKING_PATTERNS


def _get_s3_client():
    """Crée un client S3 si les credentials sont disponibles"""
    bucket_name = os.environ.get('S3_BUCKET_NAME')
    if not bucket_name:
        return None, None
    
    try:
        s3 = boto3.client('s3', region_name=os.environ.get('AWS_REGION', 'us-west-2'))
        return s3, bucket_name
    except Exception as e:
        print(f"⚠️ Erreur création client S3: {e}")
        return None, None


def _load_json_from_s3(s3_client, bucket_name: str, s3_key: str) -> Optional[Dict]:
    """Charge un fichier JSON depuis S3"""
    try:
        obj = s3_client.get_object(Bucket=bucket_name, Key=s3_key)
        data = json.loads(obj['Body'].read().decode('utf-8'))
        print(f"✅ Chargé depuis S3: s3://{bucket_name}/{s3_key}")
        return data
    except ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code != 'NoSuchKey':
            print(f"⚠️ Erreur S3 ({error_code}): {s3_key}")
        return None
    except Exception as e:
        print(f"⚠️ Erreur chargement S3 {s3_key}: {e}")
        return None


def _list_files_from_s3(s3_client, bucket_name: str, s3_prefix: str, suffix: str = ".json") -> List[str]:
    """Liste les fichiers dans un préfixe S3"""
    try:
        response = s3_client.list_objects_v2(Bucket=bucket_name, Prefix=s3_prefix)
        if 'Contents' not in response:
            return []
        
        files = [
            obj['Key'] for obj in response['Contents']
            if obj['Key'].endswith(suffix)
        ]
        return files
    except Exception as e:
        print(f"⚠️ Erreur list S3 {s3_prefix}: {e}")
        return []


def load_regulatory_extractions() -> List[Dict[str, Any]]:
    """
    Charge toutes les extractions réglementaires depuis S3 ou fichiers locaux
    
    Returns:
        Liste de dictionnaires avec les données extraites
    """
    extractions = []
    s3_client, bucket_name = _get_s3_client()
    s3_prefix = 'data/generated/extracted_directives/'
    
    # MÉTHODE 1: Depuis S3 (priorité)
    if s3_client and bucket_name:
        print(f"☁️ Chargement extractions réglementaires depuis S3: s3://{bucket_name}/{s3_prefix}")
        s3_files = _list_files_from_s3(s3_client, bucket_name, s3_prefix, suffix="_extracted.json")
        
        for s3_key in s3_files:
            data = _load_json_from_s3(s3_client, bucket_name, s3_key)
            if data:
                data['source_file'] = os.path.basename(s3_key)
                data['data_type'] = 'regulation'
                data['source'] = 'S3'
                extractions.append(data)
        
        if extractions:
            print(f"✅ {len(extractions)} extractions réglementaires chargées depuis S3")
            return extractions
    
    # MÉTHODE 2: Depuis fichiers locaux (fallback)
    regulatory_dir = DATA_PATHS['regulatory_extractions']
    if regulatory_dir.exists():
        print(f"📁 Chargement extractions réglementaires depuis local: {regulatory_dir}")
        for json_file in regulatory_dir.glob("*_extracted.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    data['source_file'] = json_file.name
                    data['data_type'] = 'regulation'
                    data['source'] = 'local'
                    extractions.append(data)
            except Exception as e:
                print(f"⚠️ Erreur chargement {json_file}: {e}")
    else:
        print(f"⚠️ Dossier réglementations non trouvé: {regulatory_dir}")
    
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


def load_impact_analysis() -> Dict[str, Any]:
    """
    Charge les résultats d'analyse d'impact (matching pairs)
    
    Returns:
        Dictionnaire avec les données d'impact analysis
    """
    impact_path = DATA_PATHS['impact_analysis']
    
    if not impact_path.exists():
        print(f"⚠️ Impact analysis non trouvé: {impact_path}")
        return {}
    
    try:
        with open(impact_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            data['data_type'] = 'impact_analysis'
            total_pairs = data.get('total_pairs', 0)
            print(f"✅ Impact analysis chargé ({total_pairs} paires d'analyse)")
            return data
    except Exception as e:
        print(f"⚠️ Erreur chargement Impact Analysis: {e}")
        return {}


def load_recommendations() -> Dict[str, Any]:
    """
    Charge les recommendations de trading
    
    Returns:
        Dictionnaire avec les recommendations
    """
    recommendations_path = DATA_PATHS['recommendations']
    
    if not recommendations_path.exists():
        print(f"⚠️ Recommendations non trouvé: {recommendations_path}")
        return {}
    
    try:
        with open(recommendations_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            data['data_type'] = 'recommendations'
            total_companies = data.get('total_companies_analyzed', 0)
            print(f"✅ Recommendations chargé ({total_companies} entreprises analysées)")
            return data
    except Exception as e:
        print(f"⚠️ Erreur chargement Recommendations: {e}")
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


def format_impact_analysis_as_text(impact_data: Dict[str, Any], regulation_id: str = None) -> str:
    """Formate une entrée d'impact analysis en texte pour embedding"""
    parts = []
    
    # Informations sur la réglementation
    if regulation_id and 'regulations' in impact_data:
        reg_data = impact_data['regulations'].get(regulation_id, {})
        if reg_data:
            if title := reg_data.get('regulation_title'):
                parts.append(f"Réglementation: {title}")
            if country := reg_data.get('regulation_country'):
                parts.append(f"Pays/Juridiction: {country}")
            if effective_date := reg_data.get('effective_date'):
                parts.append(f"Date d'entrée en vigueur: {effective_date}")
            
            # Parcourir les entreprises affectées
            if companies := reg_data.get('companies', []):
                parts.append(f"\nEntreprises exposées ({len(companies)}):")
                # Trier par score d'exposition décroissant pour mettre les plus importantes en premier
                sorted_companies = sorted(companies, key=lambda x: x.get('exposure_score', 0), reverse=True)
                for company in sorted_companies[:20]:  # Augmenter à 20 pour inclure plus d'entreprises
                    ticker = company.get('ticker', 'N/A')
                    company_name = company.get('company_name', 'N/A')
                    exposure = company.get('exposure_score', 0)
                    
                    # Inclure nom complet et ticker plusieurs fois pour meilleure recherche sémantique
                    # Format: "NVIDIA Corporation (NVDA)" pour que les recherches "Nvidia", "NVDA", "NVIDIA" fonctionnent
                    company_text = f"- {company_name} ({ticker}): Score d'exposition {exposure}/100"
                    
                    # Ajouter détails quantitatifs si disponibles
                    if quant_analysis := company.get('quantitative_analysis', {}):
                        # Chercher dans valuation_impact plutôt que directement dans quantitative_analysis
                        if valuation := company.get('valuation_impact', {}):
                            if tier1 := valuation.get('tier_1_cash_flow_impact', {}):
                                if fcf_impact := tier1.get('fcf_impact_per_share'):
                                    company_text += f", Impact FCF par action: ${fcf_impact:.4f}"
                                if fcf_pct := tier1.get('fcf_impact_percentage'):
                                    company_text += f", Impact FCF (%): {fcf_pct:.2f}%"
                            if tier3 := valuation.get('tier_3_dcf_valuation', {}):
                                if price_impact := tier3.get('price_impact_percentage'):
                                    company_text += f", Impact prix: {price_impact:.2f}%"
                    
                    # Ajouter score de risque final si disponible
                    if final_risk := company.get('final_risk_score', {}):
                        if risk_score := final_risk.get('final_risk_score'):
                            company_text += f", Score de risque final: {risk_score:.2f}/100"
                    
                    parts.append(company_text)
                    # Ajouter une ligne supplémentaire avec juste le nom pour améliorer la recherche sémantique
                    parts.append(f"  {company_name} - Ticker: {ticker}")
    
    return "\n".join(parts)


def format_recommendation_as_text(rec_data: Dict[str, Any]) -> str:
    """Formate une recommendation en texte pour embedding"""
    parts = []
    
    ticker = rec_data.get('ticker', 'N/A')
    company_name = rec_data.get('company_name', 'N/A')
    recommendation = rec_data.get('recommendation', 'N/A')
    risk_score = rec_data.get('current_risk_score', 0)
    risk_category = rec_data.get('risk_category', 'Unknown')
    
    parts.append(f"Recommendation pour {company_name} ({ticker}): {recommendation}")
    parts.append(f"Score de risque: {risk_score:.2f}/100 ({risk_category})")
    
    # Métriques
    if metrics := rec_data.get('metrics', {}):
        if exposure := metrics.get('exposure_score'):
            parts.append(f"Score d'exposition: {exposure}/100")
        if fcf_impact := metrics.get('fcf_impact_per_share'):
            parts.append(f"Impact FCF par action: ${fcf_impact:.4f}")
        if fcf_pct := metrics.get('fcf_impact_percentage'):
            parts.append(f"Impact FCF (%): {fcf_pct:.2f}%")
        if price_impact := metrics.get('price_impact_percentage'):
            parts.append(f"Impact prix: {price_impact:.2f}%")
        if discount_rate := metrics.get('discount_rate_change_bps'):
            parts.append(f"Changement taux d'actualisation: {discount_rate} bps")
    
    # Contexte réglementaire
    if reg_context := rec_data.get('regulatory_context', {}):
        if regulation := reg_context.get('regulation'):
            parts.append(f"\nRéglementation concernée: {regulation}")
        if region := reg_context.get('region'):
            parts.append(f"Région: {region}")
    
    # Justification
    if justification := rec_data.get('justification'):
        parts.append(f"\nJustification: {justification[:500]}")  # Limiter à 500 caractères
    
    return "\n".join(parts)


def create_documents_from_data(
    regulatory_data: List[Dict] = None,
    tenk_data: List[Dict] = None,
    company_universe: Dict = None,
    impact_analysis: Dict = None,
    recommendations: Dict = None
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
    
    # Documents Impact Analysis - Créer un document par entreprise pour meilleure recherche
    if impact_analysis and 'regulations' in impact_analysis:
        # Option 1: Un document par régulation (approche originale)
        for reg_id, reg_data in impact_analysis['regulations'].items():
            text = format_impact_analysis_as_text(impact_analysis, reg_id)
            if text:
                doc = Document(
                    page_content=text,
                    metadata={
                        'type': 'impact_analysis',
                        'regulation_id': reg_id,
                        'regulation_title': reg_data.get('regulation_title', ''),
                        'regulation_country': reg_data.get('regulation_country', ''),
                        'total_companies_matched': reg_data.get('total_companies_matched', 0),
                    }
                )
                documents.append(doc)
        
        # Option 2: Créer aussi des documents individuels par entreprise pour meilleure recherche ciblée
        # Cela permet de trouver facilement une entreprise spécifique comme Nvidia
        for reg_id, reg_data in impact_analysis['regulations'].items():
            if companies := reg_data.get('companies', []):
                for company in companies[:25]:  # Limiter à 25 pour éviter trop de documents
                    ticker = company.get('ticker', 'N/A')
                    company_name = company.get('company_name', 'N/A')
                    
                    # Créer un document focalisé sur cette entreprise
                    company_parts = []
                    company_parts.append(f"Analyse d'impact réglementaire pour {company_name} (ticker: {ticker})")
                    company_parts.append(f"Entreprise: {company_name}")
                    company_parts.append(f"Ticker: {ticker}")
                    
                    if reg_title := reg_data.get('regulation_title'):
                        company_parts.append(f"Réglementation: {reg_title}")
                    if reg_country := reg_data.get('regulation_country'):
                        company_parts.append(f"Pays/Juridiction: {reg_country}")
                    
                    exposure = company.get('exposure_score', 0)
                    company_parts.append(f"Score d'exposition: {exposure}/100")
                    
                    # Détails quantitatifs
                    if quant_analysis := company.get('quantitative_analysis', {}):
                        if fcf_analysis := quant_analysis.get('financial_analysis', {}):
                            if fcf := fcf_analysis.get('free_cash_flow'):
                                company_parts.append(f"Free Cash Flow: ${fcf:,.0f}")
                            if revenue := fcf_analysis.get('revenue'):
                                company_parts.append(f"Revenue: ${revenue:,.0f}")
                            if market_cap := fcf_analysis.get('market_cap'):
                                company_parts.append(f"Market Cap: ${market_cap:,.0f}")
                        
                        if valuation := company.get('valuation_impact', {}):
                            if tier1 := valuation.get('tier_1_cash_flow_impact', {}):
                                if fcf_impact := tier1.get('fcf_impact_per_share'):
                                    company_parts.append(f"Impact FCF par action: ${fcf_impact:.4f}")
                                if fcf_pct := tier1.get('fcf_impact_percentage'):
                                    company_parts.append(f"Impact FCF (%): {fcf_pct:.2f}%")
                            if tier3 := valuation.get('tier_3_dcf_valuation', {}):
                                if price_impact := tier3.get('price_impact_percentage'):
                                    company_parts.append(f"Impact prix: {price_impact:.2f}%")
                    
                    # Score de risque final
                    if final_risk := company.get('final_risk_score', {}):
                        if risk_score := final_risk.get('final_risk_score'):
                            company_parts.append(f"Score de risque final: {risk_score:.2f}/100")
                        if risk_cat := final_risk.get('risk_category'):
                            company_parts.append(f"Catégorie de risque: {risk_cat}")
                    
                    company_text = "\n".join(company_parts)
                    if company_text:
                        doc = Document(
                            page_content=company_text,
                            metadata={
                                'type': 'impact_analysis',
                                'regulation_id': reg_id,
                                'regulation_title': reg_data.get('regulation_title', ''),
                                'ticker': ticker,
                                'company_name': company_name,
                                'exposure_score': exposure,
                            }
                        )
                        documents.append(doc)
    
    # Documents Recommendations
    if recommendations and 'recommendations' in recommendations:
        # Recommendations REDUCE
        if 'reduce' in recommendations['recommendations']:
            for rec in recommendations['recommendations']['reduce']:
                text = format_recommendation_as_text(rec)
                if text:
                    ticker = rec.get('ticker', 'N/A')
                    doc = Document(
                        page_content=text,
                        metadata={
                            'type': 'recommendations',
                            'recommendation_type': 'REDUCE',
                            'ticker': ticker,
                            'company_name': rec.get('company_name', ''),
                            'risk_score': rec.get('current_risk_score', 0),
                        }
                    )
                    documents.append(doc)
        
        # Recommendations INCREASE
        if 'increase' in recommendations['recommendations']:
            for rec in recommendations['recommendations']['increase']:
                text = format_recommendation_as_text(rec)
                if text:
                    ticker = rec.get('ticker', 'N/A')
                    doc = Document(
                        page_content=text,
                        metadata={
                            'type': 'recommendations',
                            'recommendation_type': 'INCREASE',
                            'ticker': ticker,
                            'company_name': rec.get('company_name', ''),
                            'risk_score': rec.get('current_risk_score', 0),
                        }
                    )
                    documents.append(doc)
    
    print(f"✅ {len(documents)} documents LangChain créés")
    return documents

