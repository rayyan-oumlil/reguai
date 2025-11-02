#!/usr/bin/env python3
"""
Impact Calculator - Architecture 3-Tiers de Valuation

Tier 1 : Impact Orchestrator & Matching Pairs
- Coordonne le processus d'analyse d'impact réglementaire
- Crée des paires regulation-company avec score d'exposition

Tier 2 : Quant Engine (Traitement Multi-Sources)
- Company Universe DB → FinancialDataProcessor (SageMaker FinBERT)
- Regulation Table → RegulatoryDataProcessor (SageMaker LegalBERT)  
- Yahoo Finance API → MarketDataEnricher

Tier 3 : DCF Valuation & Final Risk Score
- FCF Impact: Impact sur Free Cash Flow per share
- Risk Premium: Ajustement du taux d'actualisation
- DCF Valuation: Impact sur valorisation et prix action

Usage:
    python impact_calculator.py --directives_dir <path> --company_universe <path> --output <path>
    python impact_calculator.py --quant-engine  # Enable Tier 2 + Tier 3 analysis
"""

import json
import os
import argparse
import re
import math
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from difflib import SequenceMatcher
import boto3
from botocore.exceptions import ClientError
import yfinance as yf
import pandas as pd
from dateutil.parser import parse as parse_date


class ImpactOrchestrator:
    """
    Orchestrateur principal qui coordonne le processus d'analyse d'impact
    Architecture Tier 1 : Orchestration
    """
    
    def __init__(self, region_name: str = 'us-east-1'):
        """Initialize AWS Comprehend client for entity detection"""
        self.comprehend = boto3.client('comprehend', region_name=region_name)
        self.region_name = region_name
        self._comprehend_cache = {}
    
    def load_company_universe(self, file_path: str) -> Dict[str, Any]:
        """Load company universe from JSON file"""
        print(f"📊 Loading company universe from {file_path}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data)} companies")
        return data
    
    def load_regulatory_documents(self, directives_dir: str) -> List[Dict[str, Any]]:
        """Load all extracted regulatory documents"""
        print(f"📄 Loading regulatory documents from {directives_dir}...")
        directives = []
        directives_path = Path(directives_dir)
        
        for file_path in directives_path.glob("*_extracted.json"):
            if file_path.name == "all_directives_extracted.json":
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                if isinstance(data, dict):
                    if 'document_id' in data:
                        directives.append(data)
                    else:
                        for doc_id, doc_data in data.items():
                            if isinstance(doc_data, dict) and 'document_id' in doc_data:
                                directives.append(doc_data)
            except Exception as e:
                print(f"⚠️ Error loading {file_path}: {e}")
                continue
        
        print(f"✅ Loaded {len(directives)} regulatory documents")
        return directives
    
    def analyze_with_comprehend(self, text: str, document_id: str) -> Dict[str, Any]:
        """Analyze text using AWS Comprehend for entity detection"""
        if document_id in self._comprehend_cache:
            return self._comprehend_cache[document_id]
        
        MAX_CHARS = 5000
        all_entities = []
        all_key_phrases = []
        
        chunks = [text[i:i+MAX_CHARS] for i in range(0, len(text), MAX_CHARS)]
        chunks = chunks[:20]  # Limit to control costs
        
        print(f"🔍 Analyzing {len(chunks)} chunks with Comprehend...")
        
        for i, chunk in enumerate(chunks):
            try:
                entities_response = self.comprehend.detect_entities(
                    Text=chunk,
                    LanguageCode='en'
                )
                all_entities.extend(entities_response['Entities'])
                
                phrases_response = self.comprehend.detect_key_phrases(
                    Text=chunk,
                    LanguageCode='en'
                )
                all_key_phrases.extend(phrases_response['KeyPhrases'])
                    
            except ClientError as e:
                if e.response['Error']['Code'] == 'TextSizeLimitExceededException':
                    continue
                else:
                    print(f"⚠️ Comprehend error on chunk {i}: {e}")
                    continue
        
        result = {
            'entities': all_entities,
            'key_phrases': all_key_phrases,
            'total_chunks_analyzed': len(chunks)
        }
        
        self._comprehend_cache[document_id] = result
        return result
    
    def extract_text_from_document(self, directive: Dict[str, Any]) -> str:
        """Extract text content from regulatory document for Comprehend"""
        text_parts = []
        
        extracted_info = directive.get('extracted_info', {})
        if isinstance(extracted_info, str):
            try:
                extracted_info = json.loads(extracted_info)
            except:
                text_parts.append(extracted_info)
        elif isinstance(extracted_info, dict):
            text_parts.append(extracted_info.get('title', ''))
            text_parts.append(extracted_info.get('scope', ''))
            text_parts.append(', '.join(extracted_info.get('affected_sectors', [])))
            text_parts.append(', '.join(extracted_info.get('affected_entities', [])))
            text_parts.append(', '.join(extracted_info.get('key_requirements', [])))
            
            for req in extracted_info.get('key_requirement_details', []):
                text_parts.append(req.get('requirement', ''))
                text_parts.append(req.get('compliance_action', ''))
        
        category = directive.get('category', '')
        if category:
            text_parts.append(category)
        
        text = ' '.join([part for part in text_parts if part])
        
        if isinstance(extracted_info, dict) and 'raw_content' in extracted_info:
            raw = extracted_info['raw_content']
            if isinstance(raw, str):
                text += ' ' + raw[:10000]
        
        return text
    
    def orchestrate_analysis(
        self,
        regulatory_documents: List[Dict[str, Any]],
        company_universe: Dict[str, Any],
        exposure_threshold: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Main orchestration method - coordinates the entire impact analysis
        Returns list of matching pairs (regulation, company, exposure_score)
        """
        matching_pairs = []
        
        for directive in regulatory_documents:
            document_id = directive.get('document_id', 'unknown')
            print(f"\n📋 Processing: {document_id}")
            
            if directive.get('processing_status') == 'failed':
                print(f"⚠️ Skipping failed directive: {document_id}")
                continue
            
            # Extract text for Comprehend
            text = self.extract_text_from_document(directive)
            if not text or len(text) < 100:
                print(f"⚠️ Insufficient text for {document_id}")
                continue
            
            # Analyze with Comprehend
            try:
                comprehend_results = self.analyze_with_comprehend(text, document_id)
            except Exception as e:
                print(f"❌ Comprehend error: {e}")
                comprehend_results = {'entities': [], 'key_phrases': []}
            
            # Create matching pairs using MatchingPairsEngine
            matcher = MatchingPairsEngine()
            pairs = matcher.create_matching_pairs(
                directive=directive,
                company_universe=company_universe,
                comprehend_results=comprehend_results,
                exposure_threshold=exposure_threshold
            )
            
            matching_pairs.extend(pairs)
            print(f"✅ Created {len(pairs)} matching pairs for {document_id}")
        
        return matching_pairs


class MatchingPairsEngine:
    """
    Moteur de matching qui crée des paires regulation-company
    Architecture Tier 2 : Matching Logic
    """
    
    def __init__(self):
        """Initialize matching engine"""
        self.country_mapping = self._initialize_country_mapping()
        self.sector_keywords = self._initialize_sector_keywords()
    
    def _initialize_country_mapping(self) -> Dict[str, List[str]]:
        """Initialize country name mappings for geographic matching"""
        return {
            'USA': ['united states', 'usa', 'us', 'america', 'north america', 'united states of america'],
            'EU': ['europe', 'european union', 'eu', 'european', 'emeai', 'european economic area'],
            'China': ['china', 'chinese', 'peoples republic', 'peoples republic of china', 'prc'],
            'Japan': ['japan', 'japanese'],
            'UK': ['united kingdom', 'uk', 'britain', 'british', 'great britain'],
            'Canada': ['canada', 'canadian'],
            'Germany': ['germany', 'german', 'deutschland'],
            'France': ['france', 'french'],
            'Italy': ['italy', 'italian'],
            'Spain': ['spain', 'spanish'],
            'Netherlands': ['netherlands', 'dutch', 'holland'],
            'India': ['india', 'indian'],
            'Brazil': ['brazil', 'brazilian'],
            'Mexico': ['mexico', 'mexican'],
            'Australia': ['australia', 'australian'],
            'South Korea': ['south korea', 'korea', 'korean', 'republic of korea'],
        }
    
    def _initialize_sector_keywords(self) -> Dict[str, List[str]]:
        """Initialize sector keyword mappings"""
        return {
            'Technology': ['technology', 'tech', 'software', 'hardware', 'it', 'information technology', 'digital', 'ai', 'artificial intelligence'],
            'Financial Services': ['financial', 'finance', 'banking', 'bank', 'insurance', 'investment', 'capital', 'credit'],
            'Healthcare': ['healthcare', 'health', 'medical', 'pharmaceutical', 'pharma', 'biotech', 'biotechnology', 'hospital'],
            'Energy': ['energy', 'oil', 'gas', 'petroleum', 'renewable', 'solar', 'wind', 'nuclear', 'power', 'electric'],
            'Consumer': ['consumer', 'retail', 'consumer goods', 'e-commerce', 'online marketplace', 'commerce'],
            'Manufacturing': ['manufacturing', 'manufacture', 'industrial', 'production', 'factory'],
            'Transportation': ['transportation', 'transport', 'logistics', 'shipping', 'aviation', 'airline'],
            'Telecommunications': ['telecommunications', 'telecom', 'communication', 'wireless', 'mobile'],
            'Real Estate': ['real estate', 'property', 'construction', 'building'],
            'Utilities': ['utilities', 'utility', 'water', 'electric utility', 'gas utility'],
        }
    
    def create_matching_pairs(
        self,
        directive: Dict[str, Any],
        company_universe: Dict[str, Any],
        comprehend_results: Dict[str, Any],
        exposure_threshold: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Crée des paires regulation-company en croisant toutes les données
        
        Args:
            directive: Document réglementaire avec données extraites
            company_universe: Dictionnaire des entreprises (ticker -> données)
            comprehend_results: Résultats de l'analyse Comprehend
            exposure_threshold: Seuil minimum d'exposition (0.0-1.0)
        
        Returns:
            Liste de paires {regulation_id, company_ticker, exposure_score, matching_details}
        """
        pairs = []
        
        # Extract regulatory document data
        regulatory_data = self._extract_regulatory_data(directive, comprehend_results)
        
        # Extract organization names from Comprehend for name matching
        org_names = [
            e['Text'].lower() 
            for e in comprehend_results.get('entities', [])
            if e['Type'] == 'ORGANIZATION' and e['Score'] > 0.7
        ]
        locations = [
            e['Text'].lower() 
            for e in comprehend_results.get('entities', [])
            if e['Type'] == 'LOCATION' and e['Score'] > 0.5
        ]
        
        # Process each company
        for ticker, company_data in company_universe.items():
            # Extract company data
            company_profile = self._extract_company_profile(company_data)
            
            # Perform matching across all dimensions
            matching_results = self._perform_comprehensive_matching(
                regulatory_data=regulatory_data,
                company_profile=company_profile,
                org_names=org_names,
                locations=locations,
                ticker=ticker
            )
            
            # Calculate exposure score (0-100)
            exposure_score = self._calculate_exposure_score(matching_results)
            
            # Only include pairs above threshold
            if exposure_score >= exposure_threshold * 100:
                pair = {
                    'regulation_id': regulatory_data['document_id'],
                    'regulation_title': regulatory_data.get('title', 'Unknown'),
                    'regulation_country': regulatory_data.get('country', 'Unknown'),
                    'company_ticker': ticker,
                    'company_name': company_profile['company_name'],
                    'exposure_score': round(exposure_score, 2),
                    'matching_details': matching_results,
                    'regulatory_category': regulatory_data.get('category', 'Unknown'),
                    'effective_date': regulatory_data.get('effective_date')
                }
                pairs.append(pair)
        
        # Sort by exposure score (highest first)
        pairs.sort(key=lambda x: x['exposure_score'], reverse=True)
        
        return pairs
    
    def _extract_regulatory_data(
        self,
        directive: Dict[str, Any],
        comprehend_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Extract structured data from regulatory document"""
        extracted_info = directive.get('extracted_info', {})
        if isinstance(extracted_info, str):
            try:
                extracted_info = json.loads(extracted_info)
            except:
                extracted_info = {}
        
        # Normalize list inputs
        def normalize_to_list(value, default=None):
            if value is None:
                return default if default is not None else []
            if isinstance(value, list):
                return value
            return [value] if value else []
        
        affected_sectors = [str(s).lower() for s in normalize_to_list(extracted_info.get('affected_sectors', []))]
        affected_entities = [str(e).lower() for e in normalize_to_list(extracted_info.get('affected_entities', []))]
        
        # Extract geographic scope
        country = str(extracted_info.get('country', '')).upper()
        geographic_scope = [country] if country else []
        
        # Extract from Comprehend locations
        locations = [
            e['Text'].lower() 
            for e in comprehend_results.get('entities', [])
            if e['Type'] == 'LOCATION' and e['Score'] > 0.5
        ]
        geographic_scope.extend(locations)
        
        # Extract measures (taxes, restrictions, thresholds)
        measures = []
        if extracted_info.get('monetary_thresholds'):
            for t in extracted_info.get('monetary_thresholds', []):
                if isinstance(t, dict):
                    measures.append(f"threshold: {t.get('amount', 0)} {t.get('currency', '')}")
                else:
                    measures.append(f"threshold: {str(t)}")
        
        if extracted_info.get('penalties'):
            for p in extracted_info.get('penalties', []):
                if isinstance(p, dict):
                    measures.append(f"penalty: {p.get('type', '')}")
                else:
                    measures.append(f"penalty: {str(p)}")
        
        if extracted_info.get('key_requirements'):
            measures.extend([str(r).lower() for r in extracted_info.get('key_requirements', [])])
        
        return {
            'document_id': directive.get('document_id', 'unknown'),
            'title': extracted_info.get('title', 'Unknown'),
            'country': extracted_info.get('country', 'Unknown'),
            'category': directive.get('category', 'Unknown'),
            'effective_date': extracted_info.get('effective_date'),
            'affected_sectors': affected_sectors,
            'affected_entities': affected_entities,
            'geographic_scope': geographic_scope,
            'measures': measures,
            'key_requirements': [str(r).lower() for r in extracted_info.get('key_requirements', [])]
        }
    
    def _extract_company_profile(self, company_data: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured company profile from company universe data"""
        market_data = company_data.get('market_data', {})
        data_points = company_data.get('data_points', {})
        
        geography = data_points.get('geography', {})
        supply_chain = data_points.get('supply_chain', {})
        
        # Handle dependencies (can be string or list)
        dependencies_raw = supply_chain.get('dependencies', '')
        if isinstance(dependencies_raw, list):
            dependencies = ' '.join([str(d).lower() for d in dependencies_raw])
        else:
            dependencies = str(dependencies_raw).lower() if dependencies_raw else ''
        
        return {
            'company_name': str(market_data.get('company_name', '')),
            'ticker': str(market_data.get('ticker', '')),
            'sector': str(market_data.get('sector', '')).lower(),
            'industry': str(market_data.get('industry', '')).lower(),
            'geographic_operations': {
                'countries': [str(c).lower() for c in geography.get('countries', [])],
                'regions': [str(r).lower() for r in geography.get('regions', [])],
                'has_na': geography.get('has_na', False),
                'has_eu': geography.get('has_eu', False)
            },
            'business_segments': [str(s).lower() for s in data_points.get('segments', [])],
            'supply_chain': {
                'dependencies': dependencies,
                'key_suppliers': [str(s).lower() for s in supply_chain.get('key_suppliers', [])],
                'manufacturing_locations': [str(l).lower() for l in supply_chain.get('manufacturing_locations', [])]
            },
            'financial_metrics': {
                'revenue': market_data.get('revenue'),
                'free_cash_flow': market_data.get('free_cash_flow'),
                'market_cap': market_data.get('market_cap')
            },
            'regulatory_risks': [str(r).lower() for r in data_points.get('regulatory_risks', [])]
        }
    
    def _perform_comprehensive_matching(
        self,
        regulatory_data: Dict[str, Any],
        company_profile: Dict[str, Any],
        org_names: List[str],
        locations: List[str],
        ticker: str
    ) -> Dict[str, Any]:
        """
        Effectue le matching complet sur toutes les dimensions
        Returns matching details with scores per dimension
        """
        matching_details = {
            'by_country': self._match_by_country(regulatory_data, company_profile),
            'by_sector': self._match_by_sector(regulatory_data, company_profile),
            'by_name': self._match_by_name(company_profile, org_names, ticker),
            'by_dependencies': self._match_by_dependencies(regulatory_data, company_profile),
            'by_segments': self._match_by_segments(regulatory_data, company_profile),
            'by_regulatory_risk': self._match_by_regulatory_risk(regulatory_data, company_profile)
        }
        
        return matching_details
    
    def _match_by_country(
        self,
        regulatory_data: Dict[str, Any],
        company_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Matching par pays : Si entreprise opère dans pays mentionné dans réglementation
        """
        match_score = 0.0
        matched_countries = []
        match_type = None
        
        reg_country = regulatory_data.get('country', '').upper()
        reg_geographic_scope = regulatory_data.get('geographic_scope', [])
        company_geo = company_profile['geographic_operations']
        company_countries = company_geo['countries']
        
        # Normalize country names
        reg_country_normalized = None
        for country_code, aliases in self.country_mapping.items():
            if any(alias in reg_country.lower() for alias in aliases):
                reg_country_normalized = country_code
                break
        
        # Check if company operates in regulated country
        if reg_country_normalized:
            if reg_country_normalized == 'USA' and company_geo.get('has_na'):
                match_score = 25.0
                matched_countries.append('USA')
                match_type = 'region_na'
            elif reg_country_normalized == 'EU' and company_geo.get('has_eu'):
                match_score = 25.0
                matched_countries.append('EU')
                match_type = 'region_eu'
            else:
                # Check specific country match
                country_name_map = {
                    'China': ['china', 'chinese'],
                    'Japan': ['japan', 'japanese'],
                    'UK': ['united kingdom', 'uk', 'britain'],
                    'Canada': ['canada', 'canadian'],
                    'Germany': ['germany', 'german'],
                    'France': ['france', 'french']
                }
                for country_term in country_name_map.get(reg_country_normalized, []):
                    if any(country_term in c for c in company_countries):
                        match_score = 20.0
                        matched_countries.append(reg_country_normalized)
                        match_type = 'country_specific'
                        break
        
        # Check geographic scope from Comprehend
        for location in reg_geographic_scope:
            location_lower = location.lower()
            for company_country in company_countries:
                if location_lower in company_country or company_country in location_lower:
                    if location not in matched_countries:
                        match_score += 5.0
                        matched_countries.append(location)
                        if not match_type:
                            match_type = 'location_mention'
        
        return {
            'matched': match_score > 0,
            'score': min(match_score, 25.0),
            'matched_countries': matched_countries,
            'match_type': match_type
        }
    
    def _match_by_sector(
        self,
        regulatory_data: Dict[str, Any],
        company_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Matching par secteur : Si entreprise dans secteur impacté par réglementation
        """
        match_score = 0.0
        matched_sectors = []
        
        reg_sectors = regulatory_data.get('affected_sectors', [])
        company_sector = company_profile['sector']
        company_industry = company_profile['industry']
        
        # Direct sector match
        for reg_sector in reg_sectors:
            reg_sector_lower = reg_sector.lower()
            
            # Exact match
            if reg_sector_lower == company_sector or reg_sector_lower == company_industry:
                match_score += 20.0
                matched_sectors.append(reg_sector)
            # Contains match
            elif reg_sector_lower in company_sector or company_sector in reg_sector_lower:
                match_score += 15.0
                matched_sectors.append(reg_sector)
            # Industry match
            elif reg_sector_lower in company_industry or company_industry in reg_sector_lower:
                match_score += 10.0
                matched_sectors.append(reg_sector)
            # Word overlap
            else:
                reg_words = set(reg_sector_lower.split())
                company_words = set((company_sector + ' ' + company_industry).split())
                common_words = reg_words & company_words
                if common_words and len(common_words) >= 2:
                    match_score += 5.0
                    matched_sectors.append(reg_sector)
        
        return {
            'matched': match_score > 0,
            'score': min(match_score, 30.0),
            'matched_sectors': list(set(matched_sectors))
        }
    
    def _match_by_name(
        self,
        company_profile: Dict[str, Any],
        org_names: List[str],
        ticker: str
    ) -> Dict[str, Any]:
        """
        Matching par nom : Si entreprise directement mentionnée (fuzzy matching)
        """
        match_score = 0.0
        matched_names = []
        match_type = None
        
        company_name = company_profile['company_name'].lower()
        ticker_lower = ticker.lower()
        
        # Split company name into words
        company_name_words = set(company_name.split())
        
        # Check exact matches first
        for org_name in org_names:
            org_lower = org_name.lower()
            
            # Exact match
            if company_name in org_lower or org_lower in company_name:
                match_score = 20.0
                matched_names.append(org_name)
                match_type = 'exact'
                break
            
            # Ticker match
            if ticker_lower in org_lower:
                match_score = 20.0
                matched_names.append(org_name)
                match_type = 'ticker'
                break
            
            # Fuzzy matching using SequenceMatcher
            similarity = SequenceMatcher(None, company_name, org_lower).ratio()
            if similarity > 0.8:
                match_score = 18.0
                matched_names.append(org_name)
                match_type = 'fuzzy'
            elif similarity > 0.6:
                match_score = 12.0
                matched_names.append(org_name)
                match_type = 'fuzzy_partial'
            
            # Word overlap matching
            org_words = set(org_lower.split())
            common_words = company_name_words & org_words
            if len(common_words) >= 3:  # At least 3 common words
                match_score = max(match_score, 10.0)
                matched_names.append(org_name)
                if not match_type:
                    match_type = 'word_overlap'
        
        return {
            'matched': match_score > 0,
            'score': min(match_score, 20.0),
            'matched_names': matched_names,
            'match_type': match_type
        }
    
    def _match_by_dependencies(
        self,
        regulatory_data: Dict[str, Any],
        company_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Matching par dépendances : Si chaîne d'approvisionnement affectée
        """
        match_score = 0.0
        matched_dependencies = []
        
        reg_sectors = regulatory_data.get('affected_sectors', [])
        reg_requirements = regulatory_data.get('key_requirements', [])
        supply_chain = company_profile['supply_chain']
        
        # Combine all supply chain text
        supply_chain_text = (
            supply_chain['dependencies'] + ' ' +
            ' '.join(supply_chain['key_suppliers']) + ' ' +
            ' '.join(supply_chain['manufacturing_locations'])
        ).lower()
        
        # Check if regulatory sectors/requirements affect supply chain
        all_reg_keywords = ' '.join(reg_sectors + reg_requirements).lower()
        
        # Word overlap
        supply_words = set(supply_chain_text.split())
        reg_words = set(all_reg_keywords.split())
        common_words = supply_words & reg_words
        
        if len(common_words) >= 3:
            match_score = 10.0
            matched_dependencies = list(common_words)[:5]  # Top 5 common words
        
        # Direct sector mention in supply chain
        for reg_sector in reg_sectors:
            if reg_sector in supply_chain_text:
                match_score = max(match_score, 8.0)
                matched_dependencies.append(reg_sector)
        
        return {
            'matched': match_score > 0,
            'score': min(match_score, 10.0),
            'matched_dependencies': matched_dependencies
        }
    
    def _match_by_segments(
        self,
        regulatory_data: Dict[str, Any],
        company_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Matching par segments d'affaires"""
        match_score = 0.0
        matched_segments = []
        
        reg_sectors = regulatory_data.get('affected_sectors', [])
        segments = company_profile['business_segments']
        segments_text = ' '.join(segments).lower()
        
        for reg_sector in reg_sectors:
            reg_sector_lower = reg_sector.lower()
            for segment in segments:
                segment_lower = segment.lower()
                if reg_sector_lower in segment_lower or segment_lower in reg_sector_lower:
                    match_score += 5.0
                    matched_segments.append(segment)
        
        return {
            'matched': match_score > 0,
            'score': min(match_score, 10.0),
            'matched_segments': list(set(matched_segments))
        }
    
    def _match_by_regulatory_risk(
        self,
        regulatory_data: Dict[str, Any],
        company_profile: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Matching par risques réglementaires existants"""
        match_score = 0.0
        matched_risks = []
        
        reg_category = str(regulatory_data.get('category', '')).lower()
        company_risks = company_profile['regulatory_risks']
        
        # Extract keywords from regulation category
        category_keywords = ['environmental', 'tax', 'trade', 'privacy', 'labor', 'financial', 'regulation']
        
        # Check if regulation category matches company's existing risks
        for keyword in category_keywords:
            if keyword in reg_category:
                for risk in company_risks:
                    risk_lower = risk.lower()
                    if keyword in risk_lower or 'regulation' in risk_lower:
                        match_score = 5.0
                        matched_risks.append(risk)
                        break
        
        return {
            'matched': match_score > 0,
            'score': match_score,
            'matched_risks': matched_risks
        }
    
    def _calculate_exposure_score(self, matching_results: Dict[str, Any]) -> float:
        """
        Calculate total exposure score (0-100) based on all matching dimensions
        """
        scores = {
            'by_country': matching_results['by_country']['score'],
            'by_sector': matching_results['by_sector']['score'],
            'by_name': matching_results['by_name']['score'],
            'by_dependencies': matching_results['by_dependencies']['score'],
            'by_segments': matching_results['by_segments']['score'],
            'by_regulatory_risk': matching_results['by_regulatory_risk']['score']
        }
        
        total_score = sum(scores.values())
        return min(total_score, 100.0)  # Cap at 100


# ============================================================================
# TIER 2: QUANT ENGINE - Multi-Source Processing Architecture
# ============================================================================

class FinancialDataProcessor:
    """
    FinancialDataProcessor - SageMaker FinBERT Integration
    Company Universe DB → SageMaker FinBERT (ou traitement financier)
    
    Analyze company financial data (FCF, Revenue, etc.) to assess
    financial capacity and resilience to regulatory impacts.
    """
    
    def __init__(self, use_sagemaker: bool = False, region_name: str = 'us-east-1'):
        """
        Initialize Financial Data Processor
        
        Args:
            use_sagemaker: Whether to use SageMaker endpoint (future enhancement)
            region_name: AWS region for SageMaker
        """
        self.use_sagemaker = use_sagemaker
        self.region_name = region_name
        
        if use_sagemaker:
            # TODO: Initialize SageMaker runtime client for FinBERT
            # self.sagemaker = boto3.client('sagemaker-runtime', region_name=region_name)
            pass
    
    def analyze_company_financials(
        self,
        company_data: Dict[str, Any],
        regulatory_measures: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze company financial capacity and resilience
        
        Args:
            company_data: Company data from universe
            regulatory_measures: List of regulatory measures (taxes, fines, thresholds)
            
        Returns:
            Financial analysis with resilience scores and impact capacity
        """
        market_data = company_data.get('market_data', {})
        
        # Extract key financial metrics
        revenue = market_data.get('revenue', 0) or 0
        fcf = market_data.get('free_cash_flow', 0) or 0
        net_income = market_data.get('net_income', 0) or 0
        market_cap = market_data.get('market_cap', 0) or 0
        cash_conversion = market_data.get('cash_conversion', 0) or 0
        
        # Calculate financial resilience metrics
        liquidity_ratio = abs(fcf) / revenue if revenue > 0 else 0
        profitability_ratio = net_income / revenue if revenue > 0 else 0
        
        # Assess capacity to absorb regulatory costs
        regulatory_cost_capacity = self._estimate_regulatory_cost_capacity(
            fcf, net_income, regulatory_measures
        )
        
        # Financial health score (0-100)
        health_score = self._calculate_financial_health_score(
            liquidity_ratio,
            profitability_ratio,
            cash_conversion
        )
        
        return {
            'revenue': revenue,
            'free_cash_flow': fcf,
            'net_income': net_income,
            'market_cap': market_cap,
            'liquidity_ratio': round(liquidity_ratio, 4),
            'profitability_ratio': round(profitability_ratio, 4),
            'cash_conversion': round(cash_conversion, 4),
            'regulatory_cost_capacity': regulatory_cost_capacity,
            'financial_health_score': round(health_score, 2),
            'can_absorb_impact': health_score >= 50,
            'financial_strength': self._get_strength_category(health_score)
        }
    
    def _estimate_regulatory_cost_capacity(
        self,
        fcf: float,
        net_income: float,
        regulatory_measures: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Estimate company capacity to absorb regulatory costs"""
        # Calculate maximum one-time cost (based on FCF)
        max_one_time = abs(fcf) if fcf > 0 else abs(net_income) * 0.5
        
        # Calculate annual cost capacity (based on net income)
        annual_capacity = abs(net_income) * 0.1 if net_income > 0 else 0
        
        # Assess measures vs capacity
        total_potential_cost = 0
        affordable_measures = 0
        impact_measures = []
        
        for measure in regulatory_measures:
            measure_cost = self._extract_cost_from_measure(measure)
            if measure_cost:
                total_potential_cost += measure_cost
                impact_measures.append({
                    'description': measure.get('description', ''),
                    'estimated_cost': measure_cost
                })
                
                # Check if affordable
                if measure_cost <= max_one_time or measure_cost <= annual_capacity:
                    affordable_measures += 1
        
        cost_coverage = (affordable_measures / len(regulatory_measures) * 100) if regulatory_measures else 100
        
        return {
            'max_one_time_cost': max_one_time,
            'annual_capacity': annual_capacity,
            'total_potential_cost': total_potential_cost,
            'cost_coverage_ratio': round(cost_coverage, 2),
            'affordable_measures': affordable_measures,
            'total_measures': len(regulatory_measures),
            'impact_measures': impact_measures
        }
    
    def _extract_cost_from_measure(self, measure: Dict[str, Any]) -> Optional[float]:
        """Extract cost estimate from regulatory measure"""
        # Check various formats
        if 'amount' in measure:
            return float(measure['amount'])
        elif 'estimated_cost' in measure:
            return float(measure['estimated_cost'])
        elif 'fine' in measure:
            return float(measure.get('fine', 0))
        return None
    
    def _calculate_financial_health_score(
        self,
        liquidity_ratio: float,
        profitability_ratio: float,
        cash_conversion: float
    ) -> float:
        """Calculate overall financial health score (0-100)"""
        # Normalize ratios to 0-100 scale
        liquidity_score = min(liquidity_ratio * 1000, 100)  # 0.1 = 100 score
        profitability_score = min(profitability_ratio * 500, 100)  # 0.2 = 100 score
        cash_conversion_score = min(cash_conversion * 100, 100)
        
        # Weighted average
        health_score = (
            liquidity_score * 0.3 +
            profitability_score * 0.4 +
            cash_conversion_score * 0.3
        )
        
        return max(0, min(100, health_score))
    
    def _get_strength_category(self, health_score: float) -> str:
        """Categorize financial strength"""
        if health_score >= 75:
            return 'Strong'
        elif health_score >= 50:
            return 'Moderate'
        elif health_score >= 25:
            return 'Weak'
        else:
            return 'Critical'


class RegulatoryDataProcessor:
    """
    RegulatoryDataProcessor - SageMaker LegalBERT Integration
    Regulation Table → SageMaker LegalBERT (ou traitement juridique)
    
    Analyze regulatory document extracts to quantify severity and impact.
    """
    
    def __init__(self, use_sagemaker: bool = False, region_name: str = 'us-east-1'):
        """
        Initialize Regulatory Data Processor
        
        Args:
            use_sagemaker: Whether to use SageMaker endpoint (future enhancement)
            region_name: AWS region for SageMaker
        """
        self.use_sagemaker = use_sagemaker
        self.region_name = region_name
        
        if use_sagemaker:
            # TODO: Initialize SageMaker runtime client for LegalBERT
            # self.sagemaker = boto3.client('sagemaker-runtime', region_name=region_name)
            pass
    
    def analyze_regulatory_impact(
        self,
        directive: Dict[str, Any],
        comprehend_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze regulatory requirements and quantify impact severity
        
        Args:
            directive: Regulatory document with extracted info
            comprehend_results: AWS Comprehend analysis results
            
        Returns:
            Regulatory impact analysis with severity scores
        """
        extracted_info = directive.get('extracted_info', {})
        
        # Parse extracted_info if needed
        if isinstance(extracted_info, str):
            try:
                extracted_info = json.loads(extracted_info)
            except:
                extracted_info = {}
        
        # Extract regulatory measures
        monetary_thresholds = extracted_info.get('monetary_thresholds', [])
        penalties_raw = extracted_info.get('penalties', [])
        key_requirements = extracted_info.get('key_requirements', [])
        reporting_requirements = extracted_info.get('reporting_requirements', [])
        
        # Handle both list and dict formats for penalties
        if isinstance(penalties_raw, dict):
            penalties_list = [penalties_raw] if penalties_raw else []
        else:
            penalties_list = penalties_raw if isinstance(penalties_raw, list) else []
        
        # Calculate severity scores
        financial_severity = self._calculate_financial_severity(monetary_thresholds, penalties_list)
        operational_severity = self._calculate_operational_severity(key_requirements)
        compliance_complexity = self._calculate_compliance_complexity(reporting_requirements, key_requirements)
        
        # Overall impact severity (0-100)
        overall_severity = self._calculate_overall_severity(
            financial_severity,
            operational_severity,
            compliance_complexity
        )
        
        # Extract sentiment from Comprehend
        sentiment = comprehend_results.get('sentiment', {})
        sentiment_score = self._sentiment_to_score(sentiment)
        
        return {
            'monetary_thresholds_count': len(monetary_thresholds),
            'penalties_count': len(penalties_list),
            'requirements_count': len(key_requirements),
            'reporting_requirements_count': len(reporting_requirements),
            'financial_severity': round(financial_severity, 2),
            'operational_severity': round(operational_severity, 2),
            'compliance_complexity': round(compliance_complexity, 2),
            'overall_severity': round(overall_severity, 2),
            'sentiment_score': round(sentiment_score, 2),
            'regulatory_classification': self._classify_regulation(overall_severity),
            'measures': {
                'monetary_thresholds': monetary_thresholds,
                'penalties': penalties_list,
                'key_requirements': key_requirements
            }
        }
    
    def _calculate_financial_severity(
        self,
        monetary_thresholds: List[Dict[str, Any]],
        penalties: List[Dict[str, Any]]
    ) -> float:
        """Calculate severity based on monetary impacts (0-100)"""
        if not monetary_thresholds and not penalties:
            return 0
        
        # Extract and sum all amounts
        total_amount = 0
        
        for threshold in monetary_thresholds:
            if 'amount' in threshold:
                amount = self._normalize_amount(threshold['amount'])
                total_amount += amount
        
        for penalty in penalties:
            if 'amount' in penalty:
                amount = self._normalize_amount(penalty['amount'])
                total_amount += amount
        
        # Convert to severity score (logarithmic scale)
        # 1M = 25, 10M = 50, 100M = 75, 1B = 100
        if total_amount == 0:
            return 0
        
        severity = min(math.log10(total_amount / 1000 + 1) * 50, 100)
        return severity
    
    def _calculate_operational_severity(self, key_requirements: List[str]) -> float:
        """Calculate severity based on operational complexity (0-100)"""
        if not key_requirements:
            return 0
        
        # Keywords indicating high operational impact
        severe_keywords = [
            'restriction', 'prohibition', 'ban', 'cease',
            'compliance', 'mandatory', 'required', 'must',
            'penalty', 'fine', 'sanction'
        ]
        
        severity_score = 0
        for req in key_requirements:
            req_lower = str(req).lower()
            keyword_count = sum(1 for keyword in severe_keywords if keyword in req_lower)
            severity_score += keyword_count * 5  # 5 points per keyword
        
        return min(severity_score, 100)
    
    def _calculate_compliance_complexity(
        self,
        reporting_requirements: List[Dict[str, Any]],
        key_requirements: List[str]
    ) -> float:
        """Calculate complexity based on compliance burden (0-100)"""
        complexity = 0
        
        # Reporting requirements add complexity
        complexity += len(reporting_requirements) * 10
        
        # Multiple requirements add complexity
        complexity += len(key_requirements) * 3
        
        return min(complexity, 100)
    
    def _calculate_overall_severity(
        self,
        financial_severity: float,
        operational_severity: float,
        compliance_complexity: float
    ) -> float:
        """Calculate overall regulatory severity"""
        return (financial_severity * 0.5 + operational_severity * 0.3 + compliance_complexity * 0.2)
    
    def _sentiment_to_score(self, sentiment: Dict[str, Any]) -> float:
        """Convert Comprehend sentiment to severity score"""
        if not sentiment:
            return 50  # Neutral
        
        sentiment_type = sentiment.get('Sentiment', 'NEUTRAL')
        confidence = sentiment.get('SentimentScore', {})
        
        # Negative sentiment = higher severity
        if sentiment_type == 'NEGATIVE':
            base_score = 75
        elif sentiment_type == 'MIXED':
            base_score = 60
        elif sentiment_type == 'POSITIVE':
            base_score = 40
        else:
            base_score = 50
        
        # Adjust based on confidence
        max_confidence = max(confidence.values()) if confidence else 0.5
        score_adjustment = (max_confidence - 0.5) * 20  # -10 to +10
        
        return base_score + score_adjustment
    
    def _classify_regulation(self, severity: float) -> str:
        """Classify regulation by severity"""
        if severity >= 75:
            return 'High Impact'
        elif severity >= 50:
            return 'Moderate Impact'
        elif severity >= 25:
            return 'Low Impact'
        else:
            return 'Minimal Impact'
    
    def _normalize_amount(self, amount: Any) -> float:
        """Normalize amount to float, handling various formats"""
        try:
            if isinstance(amount, (int, float)):
                return float(amount)
            elif isinstance(amount, str):
                # Remove currency symbols and commas
                cleaned = re.sub(r'[^\d.]+', '', amount)
                return float(cleaned)
            return 0.0
        except:
            return 0.0


class MarketDataEnricher:
    """
    MarketDataEnricher - Yahoo Finance API Integration
    Yahoo Finance API → Market Data Processor
    
    Enrich company analysis with real-time market data (prices, volatility).
    """
    
    def __init__(self, cache_duration_hours: int = 24):
        """
        Initialize Market Data Enricher
        
        Args:
            cache_duration_hours: Duration for caching market data
        """
        self.cache_duration_hours = cache_duration_hours
        self._market_data_cache = {}
        self._last_update = {}
    
    def enrich_with_market_data(
        self,
        ticker: str,
        exposure_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Enrich company data with real-time market information
        
        Args:
            ticker: Company ticker symbol
            exposure_date: Date of regulatory exposure (for historical analysis)
            
        Returns:
            Market data enrichment (volatility, recent trends, etc.)
        """
        # Check cache
        cache_key = ticker
        if cache_key in self._market_data_cache:
            cache_time = self._last_update.get(cache_key, datetime.min)
            if (datetime.now() - cache_time).total_seconds() < self.cache_duration_hours * 3600:
                return self._market_data_cache[cache_key]
        
        try:
            # Fetch market data using yfinance
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Get recent price history (1 year)
            hist = stock.history(period='1y')
            
            # Calculate volatility metrics
            if len(hist) > 0:
                returns = hist['Close'].pct_change()
                volatility = returns.std() * math.sqrt(252)  # Annualized volatility
                
                # Recent trend
                recent_days = 30
                recent_prices = hist.tail(recent_days)['Close']
                price_change_pct = ((recent_prices.iloc[-1] - recent_prices.iloc[0]) / recent_prices.iloc[0]) * 100
                
                # Volume analysis
                avg_volume = hist['Volume'].mean()
                recent_volume = hist.tail(20)['Volume'].mean()
                volume_trend = 'high' if recent_volume > avg_volume * 1.5 else 'normal'
            else:
                volatility = 0
                price_change_pct = 0
                volume_trend = 'unknown'
            
            market_data = {
                'current_price': info.get('currentPrice'),
                'market_cap': info.get('marketCap'),
                'volume': info.get('volume'),
                'beta': info.get('beta', 1.0),
                'volatility_annual': round(volatility, 4),
                'price_change_30d': round(price_change_pct, 2),
                'volume_trend': volume_trend,
                'risk_level': self._assess_risk_level(volatility),
                'timestamp': datetime.now().isoformat()
            }
            
            # Cache result
            self._market_data_cache[cache_key] = market_data
            self._last_update[cache_key] = datetime.now()
            
            return market_data
            
        except Exception as e:
            print(f"⚠️ Error fetching market data for {ticker}: {e}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def _assess_risk_level(self, volatility: float) -> str:
        """Assess market risk level based on volatility"""
        if volatility >= 0.40:
            return 'Very High'
        elif volatility >= 0.30:
            return 'High'
        elif volatility >= 0.20:
            return 'Moderate'
        elif volatility >= 0.10:
            return 'Low'
        else:
            return 'Very Low'


class QuantEngine:
    """
    Quant Engine - Orchestrator for Multi-Source Processing
    Coordinates financial, regulatory, and market data analysis
    
    Pipeline:
    1. FinancialDataProcessor: Analyze company financials
    2. RegulatoryDataProcessor: Analyze regulatory measures
    3. MarketDataEnricher: Add real-time market context
    """
    
    def __init__(
        self,
        use_sagemaker: bool = False,
        region_name: str = 'us-east-1',
        enable_dcf: bool = True
    ):
        """
        Initialize Quant Engine
        
        Args:
            use_sagemaker: Whether to use SageMaker models
            region_name: AWS region
            enable_dcf: Enable Tier 3 DCF valuation analysis
        """
        self.financial_processor = FinancialDataProcessor(use_sagemaker, region_name)
        self.regulatory_processor = RegulatoryDataProcessor(use_sagemaker, region_name)
        self.market_enricher = MarketDataEnricher()
        self.enable_dcf = enable_dcf
        
        if enable_dcf:
            self.dcf_engine = DCFValuationEngine()
            self.risk_scorer = FinalRiskScorer()
    
    def process_matching_pair(
        self,
        matching_pair: Dict[str, Any],
        company_universe: Dict[str, Any],
        regulatory_documents: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Process a single matching pair through multi-source pipeline
        
        Args:
            matching_pair: Single regulation-company match from Tier 1
            company_universe: Company universe data
            regulatory_documents: All regulatory documents
            
        Returns:
            Enriched pair with quantitative analysis
        """
        ticker = matching_pair['company_ticker']
        regulation_id = matching_pair['regulation_id']
        
        # Get company data
        company_data = company_universe.get(ticker, {})
        
        # Get regulatory document
        regulatory_doc = None
        for doc in regulatory_documents:
            if doc.get('document_id') == regulation_id:
                regulatory_doc = doc
                break
        
        if not regulatory_doc:
            return matching_pair  # Return as-is if document not found
        
        # Step 1: Analyze financial capacity
        extracted_info = regulatory_doc.get('extracted_info', {})
        if isinstance(extracted_info, str):
            try:
                extracted_info = json.loads(extracted_info)
            except:
                extracted_info = {}
        
        # Handle both list and dict formats for penalties
        penalties_raw = extracted_info.get('penalties', [])
        if isinstance(penalties_raw, dict):
            # Convert dict to list format
            penalties_list = [penalties_raw] if penalties_raw else []
        else:
            penalties_list = penalties_raw if isinstance(penalties_raw, list) else []
        
        regulatory_measures = [
            *extracted_info.get('monetary_thresholds', []),
            *penalties_list
        ]
        
        financial_analysis = self.financial_processor.analyze_company_financials(
            company_data,
            regulatory_measures
        )
        
        # Step 2: Analyze regulatory impact
        # We need comprehend_results, use empty dict for now (ideally pass from Tier 1)
        regulatory_analysis = self.regulatory_processor.analyze_regulatory_impact(
            regulatory_doc,
            {}  # Comprehend results would be passed from Tier 1
        )
        
        # Step 3: Enrich with market data
        market_data = self.market_enricher.enrich_with_market_data(ticker)
        
        # Step 4-5: Tier 3 DCF Valuation (if enabled)
        valuation_impact = {}
        final_risk_score = {}
        
        if self.enable_dcf:
            # Tier 3: Calculate DCF valuation impact
            valuation_impact = self.dcf_engine.calculate_valuation_impact(
                company_data,
                financial_analysis,
                regulatory_analysis,
                market_data,
                financial_analysis.get('regulatory_cost_capacity', {}),
                matching_pair.get('exposure_score', 0)
            )
            
            # Final Risk Score: Combine all tiers
            final_risk_score = self.risk_scorer.calculate_final_risk_score(
                matching_pair,
                {
                    'impact_assessment': self._calculate_quantitative_impact(
                        financial_analysis,
                        regulatory_analysis,
                        market_data
                    ),
                    'regulatory_analysis': regulatory_analysis
                },
                valuation_impact,
                company_data
            )
        
        # Combine all analyses
        enriched_pair = {
            **matching_pair,
            'quantitative_analysis': {
                'financial_analysis': financial_analysis,
                'regulatory_analysis': regulatory_analysis,
                'market_data': market_data
            },
            'impact_assessment': self._calculate_quantitative_impact(
                financial_analysis,
                regulatory_analysis,
                market_data
            )
        }
        
        # Add Tier 3 analysis if enabled
        if valuation_impact:
            enriched_pair['valuation_impact'] = valuation_impact
        
        # Add final risk score if enabled
        if final_risk_score:
            enriched_pair['final_risk_score'] = final_risk_score
        
        return enriched_pair
    
    def _calculate_quantitative_impact(
        self,
        financial_analysis: Dict[str, Any],
        regulatory_analysis: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate overall quantitative impact score"""
        # Combine scores from all sources
        financial_score = financial_analysis.get('financial_health_score', 50)
        regulatory_severity = regulatory_analysis.get('overall_severity', 50)
        
        # Inverse relationship: High regulatory severity + Low financial health = High impact
        impact_score = (100 - financial_score) * 0.4 + regulatory_severity * 0.6
        
        # Risk classification
        if impact_score >= 75:
            risk_level = 'Critical'
        elif impact_score >= 60:
            risk_level = 'High'
        elif impact_score >= 40:
            risk_level = 'Moderate'
        else:
            risk_level = 'Low'
        
        return {
            'quantitative_impact_score': round(impact_score, 2),
            'risk_level': risk_level,
            'factors': {
                'financial_vulnerability': round(100 - financial_score, 2),
                'regulatory_severity': round(regulatory_severity, 2)
            }
        }


# ============================================================================
# TIER 3: DCF VALUATION - Financial Impact Assessment
# ============================================================================

class DCFValuationEngine:
    """
    DCF Valuation Engine - Financial Impact Assessment
    
    Calculates regulatory impact on company valuation using DCF methodology:
    - Tier 1: Cash Flow Impact
    - Tier 2: Risk Premium Adjustment
    - Tier 3: DCF Valuation & Price Impact
    """
    
    def __init__(self):
        """Initialize DCF Valuation Engine"""
        pass
    
    def calculate_valuation_impact(
        self,
        company_data: Dict[str, Any],
        financial_analysis: Dict[str, Any],
        regulatory_analysis: Dict[str, Any],
        market_data: Dict[str, Any],
        regulatory_cost_capacity: Dict[str, Any],
        exposure_score: float
    ) -> Dict[str, Any]:
        """
        Calculate valuation impact across 3 tiers
        
        Args:
            company_data: Company data from universe
            financial_analysis: Financial analysis from Quant Engine
            regulatory_analysis: Regulatory analysis from Quant Engine
            market_data: Market data from Quant Engine
            regulatory_cost_capacity: Cost capacity analysis
            exposure_score: Tier 1 exposure score (0-100)
            
        Returns:
            Valuation impact analysis
        """
        # Tier 1: Calculate Cash Flow Impact
        fcf_impact = self._calculate_fcf_impact(
            company_data,
            financial_analysis,
            regulatory_analysis,
            regulatory_cost_capacity
        )
        
        # Tier 2: Calculate Risk Premium Adjustment
        discount_rate_adjustment = self._calculate_discount_rate_adjustment(
            regulatory_analysis,
            market_data,
            financial_analysis,
            exposure_score
        )
        
        # Tier 3: Calculate DCF Valuation Impact
        dcf_valuation = self._calculate_dcf_valuation(
            company_data,
            fcf_impact,
            discount_rate_adjustment,
            market_data
        )
        
        return {
            'tier_1_cash_flow_impact': fcf_impact,
            'tier_2_discount_rate_adjustment': discount_rate_adjustment,
            'tier_3_dcf_valuation': dcf_valuation
        }
    
    def _calculate_fcf_impact(
        self,
        company_data: Dict[str, Any],
        financial_analysis: Dict[str, Any],
        regulatory_analysis: Dict[str, Any],
        regulatory_cost_capacity: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Tier 1: Map regulatory measures to financial drivers and calculate P&L impact
        
        Maps regulatory measures → Financial Statement Line Items:
        - Carbon tax → COGS increase
        - R&D mandate → R&D expense increase
        - Import tariff → COGS increase
        - Data localization → CAPEX/OPEX increase
        - Product ban → Revenue decrease
        - Subsidy → Tax expense decrease
        - Emission caps → Compliance cost increase
        """
        # Get financial metrics
        fcf = financial_analysis.get('free_cash_flow', 0)
        revenue = financial_analysis.get('revenue', 0)
        market_cap = financial_analysis.get('market_cap', 0)
        net_income = financial_analysis.get('net_income', 0)
        
        # Estimate shares outstanding
        shares_outstanding = market_cap / 100 if market_cap > 0 else 1
        
        # Extract regulatory measures
        monetary_thresholds = regulatory_analysis.get('measures', {}).get('monetary_thresholds', [])
        penalties = regulatory_analysis.get('measures', {}).get('penalties', [])
        key_requirements = regulatory_analysis.get('measures', {}).get('key_requirements', [])
        
        # Map measures to financial drivers
        financial_impacts = self._map_regulatory_measures_to_financial_impact(
            monetary_thresholds,
            penalties,
            key_requirements,
            revenue,
            financial_analysis,
            company_data
        )
        
        # Calculate total annualized FCF impact
        annual_fcf_impact = sum(
            impact.get('annual_impact', 0) 
            for impact in financial_impacts
        )
        
        # Per-share impact
        fcf_per_share_impact = annual_fcf_impact / shares_outstanding if shares_outstanding > 0 else 0
        
        # Current FCF per share
        fcf_per_share = fcf / shares_outstanding if shares_outstanding > 0 else 0
        
        # Relative impact as % of current FCF
        if fcf_per_share != 0:
            fcf_impact_percentage = (fcf_per_share_impact / abs(fcf_per_share)) * 100
        else:
            fcf_impact_percentage = 0
        
        return {
            'annual_fcf_impact': round(annual_fcf_impact, 2),
            'fcf_impact_per_share': round(fcf_per_share_impact, 4),
            'fcf_impact_percentage': round(fcf_impact_percentage, 2),
            'current_fcf_per_share': round(fcf_per_share, 4),
            'financial_driver_impacts': financial_impacts,
            'exposure_base': revenue,
            'total_measures_analyzed': len(monetary_thresholds) + len(penalties) + len(key_requirements)
        }
    
    def _map_regulatory_measures_to_financial_impact(
        self,
        monetary_thresholds: List[Dict[str, Any]],
        penalties: List[Dict[str, Any]],
        key_requirements: List[str],
        revenue: float,
        financial_analysis: Dict[str, Any],
        company_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Map regulatory measures to financial statement impacts
        
        Financial Impact = Exposure Base × Impact Magnitude × Adjustment Factor
        """
        impacts = []
        
        # Process monetary thresholds (taxes, fees, etc.)
        for threshold in monetary_thresholds:
            impact = self._calculate_measure_impact(threshold, revenue, 'threshold')
            if impact:
                impacts.append(impact)
        
        # Process penalties (fines, sanctions)
        for penalty in penalties:
            impact = self._calculate_measure_impact(penalty, revenue, 'penalty')
            if impact:
                impacts.append(impact)
        
        # Process key requirements (operational mandates)
        for requirement in key_requirements:
            impact = self._calculate_requirement_impact(
                requirement,
                revenue,
                financial_analysis,
                company_data
            )
            if impact:
                impacts.append(impact)
        
        return impacts
    
    def _calculate_measure_impact(
        self,
        measure: Dict[str, Any],
        exposure_base: float,
        measure_type: str
    ) -> Optional[Dict[str, Any]]:
        """Calculate financial impact for a specific regulatory measure"""
        # Extract amount
        amount = self._normalize_amount(measure.get('amount', 0))
        if amount == 0:
            return None
        
        # Determine financial driver based on measure type
        if measure_type == 'penalty':
            # Penalties → Operating expense
            driver = 'operating_expense'
        elif 'tax' in str(measure.get('type', '')).lower():
            # Taxes → Tax expense or COGS depending on type
            driver = 'tax_expense'
        else:
            # Default to operating expense
            driver = 'operating_expense'
        
        # Adjustment factor (implementation timeline, probability)
        # Assume 100% probability for now, can be enhanced
        adjustment_factor = 1.0
        
        # Calculate annualized impact
        annual_impact = -amount  # Negative = cost
        
        return {
            'measure_type': measure_type,
            'financial_driver': driver,
            'amount': amount,
            'annual_impact': annual_impact * adjustment_factor,
            'description': measure.get('description', ''),
            'adjustment_factor': adjustment_factor
        }
    
    def _calculate_requirement_impact(
        self,
        requirement: str,
        revenue: float,
        financial_analysis: Dict[str, Any],
        company_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Calculate financial impact for operational requirements"""
        req_lower = str(requirement).lower()
        impact_magnitude = 0
        driver = None
        
        # Map keywords to financial drivers and estimate impact
        # Order matters: more specific first
        req_words = req_lower.split()
        
        # More specific matches
        if any(word in req_words for word in ['localization', 'data center', 'infrastructure']):
            driver = 'capital_expenditure'
            impact_magnitude = 0.001
        elif any(word in req_words for word in ['rd', 'research', 'development', 'innovation']):
            driver = 'rd_expense'
            impact_magnitude = 0.005
        elif any(word in req_words for word in ['emission', 'carbon', 'environmental']):
            driver = 'operating_expense'
            impact_magnitude = 0.002
        elif any(word in req_words for word in ['security', 'cybersecurity', 'protection']):
            driver = 'operating_expense'
            impact_magnitude = 0.0015
        elif any(word in req_words for word in ['audit', 'reporting', 'compliance']):
            driver = 'operating_expense'
            impact_magnitude = 0.001
        elif any(word in req_words for word in ['transparency', 'disclosure', 'information']):
            # General compliance requirements
            driver = 'operating_expense'
            impact_magnitude = 0.0005
        elif any(word in req_words for word in ['monitoring', 'verification', 'review']):
            driver = 'operating_expense'
            impact_magnitude = 0.0008
        
        # Default: minimal impact for unrecognized requirements
        if driver is None:
            driver = 'operating_expense'
            impact_magnitude = 0.0003  # 0.03% of revenue
        
        # Calculate impact
        annual_impact = -revenue * impact_magnitude
        
        return {
            'measure_type': 'requirement',
            'financial_driver': driver,
            'impact_magnitude': impact_magnitude,
            'annual_impact': annual_impact,
            'description': requirement,
            'adjustment_factor': 1.0
        }
    
    def _normalize_amount(self, amount: Any) -> float:
        """Normalize amount to float, handling various formats"""
        try:
            if isinstance(amount, (int, float)):
                return float(amount)
            elif isinstance(amount, str):
                # Remove currency symbols and commas
                cleaned = re.sub(r'[^\d.]+', '', amount)
                return float(cleaned)
            return 0.0
        except:
            return 0.0
    
    def _calculate_discount_rate_adjustment(
        self,
        regulatory_analysis: Dict[str, Any],
        market_data: Dict[str, Any],
        financial_analysis: Dict[str, Any],
        exposure_score: float
    ) -> Dict[str, Any]:
        """
        Tier 2: Multi-Factor Risk Premium Adjustment
        
        Calculates risk premium based on:
        1. Regulation Severity → Base risk premium
        2. Company Resilience → Resilience penalty
        3. Exposure Concentration → Concentration risk
        """
        # Base CAPM discount rate
        risk_free_rate = 0.03  # 3% risk-free rate
        market_risk_premium = 0.06  # 6% market risk premium
        beta = market_data.get('beta', 1.0)
        base_discount_rate = risk_free_rate + beta * market_risk_premium
        
        # Factor 1: Regulation Severity → Base Risk Premium
        severity_adj = self._calculate_severity_risk_premium(regulatory_analysis)
        
        # Factor 2: Company Resilience → Resilience Penalty
        resilience_penalty = self._calculate_resilience_penalty(financial_analysis)
        
        # Factor 3: Exposure Concentration → Concentration Risk
        concentration_risk = self._calculate_concentration_risk(exposure_score)
        
        # Total risk premium adjustment
        total_risk_premium = severity_adj + resilience_penalty + concentration_risk
        
        # Apply sanity check: cap at 5%
        total_risk_premium = min(total_risk_premium, 0.05)
        
        # Adjusted discount rate
        adjusted_discount_rate = base_discount_rate + total_risk_premium
        
        # Discount rate change in basis points
        discount_rate_change_bps = total_risk_premium * 10000
        
        return {
            'base_discount_rate': round(base_discount_rate * 100, 2),
            'risk_premium_components': {
                'severity_adjustment': round(severity_adj * 100, 2),
                'resilience_penalty': round(resilience_penalty * 100, 2),
                'concentration_risk': round(concentration_risk * 100, 2)
            },
            'total_risk_premium': round(total_risk_premium * 100, 2),
            'adjusted_discount_rate': round(adjusted_discount_rate * 100, 2),
            'discount_rate_change_bps': round(discount_rate_change_bps, 0),
            'wacc_components': {
                'risk_free_rate': round(risk_free_rate * 100, 2),
                'market_risk_premium': round(market_risk_premium * 100, 2),
                'beta': round(beta, 3)
            }
        }
    
    def _calculate_severity_risk_premium(self, regulatory_analysis: Dict[str, Any]) -> float:
        """Factor 1: Regulation Severity → Risk Premium Adjustment"""
        severity = regulatory_analysis.get('overall_severity', 0)
        
        # Classify severity and assign risk premium
        if severity >= 75:
            # SEVERE: Existential threat
            risk_premium = 0.02  # +2.0%
        elif severity >= 60:
            # HIGH: Strategic business impact
            risk_premium = 0.01  # +1.0%
        elif severity >= 40:
            # MEDIUM: Material ongoing costs
            risk_premium = 0.005  # +0.5%
        elif severity >= 20:
            # LOW: Minor compliance costs
            risk_premium = 0.0025  # +0.25%
        else:
            # MINIMAL
            risk_premium = 0.0
        
        return risk_premium
    
    def _calculate_resilience_penalty(self, financial_analysis: Dict[str, Any]) -> float:
        """Factor 2: Company Resilience → Resilience Penalty"""
        # Get financial metrics
        liquidity_ratio = financial_analysis.get('liquidity_ratio', 0)
        cash_conversion = financial_analysis.get('cash_conversion', 0)
        profitability_ratio = financial_analysis.get('profitability_ratio', 0)
        
        # Simulate debt/EBITDA (we don't have direct access, estimate from ratios)
        # Higher profitability = lower debt ratio assumption
        estimated_debt_ebitda = max(0, 3 - (profitability_ratio * 10))  # Rough proxy
        
        # Calculate resilience score (0-1 scale)
        # Normalize: liquidity (higher is better), debt (lower is better), profitability (higher is better)
        liquidity_normalized = min(liquidity_ratio * 10, 1.0)  # 0.1 = 1.0
        debt_normalized = max(0, 1 - (estimated_debt_ebitda / 5))  # <5 = 1.0, >5 = 0
        profitability_normalized = min(profitability_ratio * 5, 1.0)  # 0.2 = 1.0
        
        resilience_score = (
            liquidity_normalized * 0.3 +
            debt_normalized * 0.3 +
            profitability_normalized * 0.4
        )
        
        # Resilience penalty = (1 - Resilience Score) × 0.005
        resilience_penalty = (1 - resilience_score) * 0.005
        
        return resilience_penalty
    
    def _calculate_concentration_risk(self, exposure_score: float) -> float:
        """Factor 3: Exposure Concentration → Concentration Risk"""
        # Concentration Risk = (Exposure Score / 100) × 0.01
        concentration_risk = (exposure_score / 100) * 0.01
        return concentration_risk
    
    def _calculate_dcf_valuation(
        self,
        company_data: Dict[str, Any],
        fcf_impact: Dict[str, Any],
        discount_rate_adjustment: Dict[str, Any],
        market_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Tier 3: Two-Stage DCF Valuation Engine
        
        Simplified model:
        Step 1: Baseline valuation (pre-regulation)
        Step 2: Impact-adjusted valuation  
        Step 3: Price impact calculation with component breakdown
        """
        # Extract FCF per share data
        current_fcf_per_share = fcf_impact.get('current_fcf_per_share', 0)
        fcf_impact_per_share = fcf_impact.get('fcf_impact_per_share', 0)
        
        # Extract discount rates
        base_discount_rate = discount_rate_adjustment.get('base_discount_rate', 0) / 100
        adjusted_discount_rate = discount_rate_adjustment.get('adjusted_discount_rate', 0) / 100
        
        # DCF assumptions
        growth_rate = 0.03  # 3% perpetual growth
        
        # Validate inputs
        if base_discount_rate <= growth_rate:
            base_discount_rate = growth_rate + 0.01  # Sanity: ensure discount > growth
        if adjusted_discount_rate <= growth_rate:
            adjusted_discount_rate = growth_rate + 0.01
        
        # Sanity check: Negative FCF per share breaks Gordon Growth Model
        # In this case, use FCF percentage impact as proxy for valuation impact
        if current_fcf_per_share <= 0:
            # Cannot apply DCF with negative FCF, fall back to FCF impact percentage
            fcf_impact_percentage = fcf_impact.get('fcf_impact_percentage', 0)
            
            # Assume similar impact on valuation
            price_impact_percentage = abs(fcf_impact_percentage) * 0.5  # Conservative mapping
            
            return {
                'price_impact_percentage': -round(price_impact_percentage, 2),
                'component_breakdown': {
                    'cash_flow_impact_pct': round(fcf_impact_percentage, 2),
                    'multiple_compression_pct': round((adjusted_discount_rate - base_discount_rate) * -100, 2),
                    'interaction_effects_pct': 0.0
                },
                'baseline_valuation': {
                    'fcf_per_share': round(current_fcf_per_share, 4),
                    'discount_rate': round(base_discount_rate * 100, 2),
                    'method': 'Cannot apply DCF (negative FCF)'
                },
                'adjusted_valuation': {
                    'fcf_per_share': round(current_fcf_per_share + fcf_impact_per_share, 4),
                    'discount_rate': round(adjusted_discount_rate * 100, 2),
                    'method': 'FCF impact percentage proxy'
                },
                'assumptions': {
                    'growth_rate_percent': 3.0,
                    'valuation_model': 'FCF impact proxy (negative FCF)',
                    'note': 'Gordon Growth not applicable for negative FCF'
                }
            }
        
        # Step 1: Baseline Valuation (Pre-Regulation)
        # Gordon Growth Model: FCF × (1 + g) / (r - g)
        baseline_terminal_value = current_fcf_per_share * (1 + growth_rate) / (base_discount_rate - growth_rate)
        baseline_present_value = baseline_terminal_value / (1 + base_discount_rate)  # Simplified 1-year
        
        # Step 2: Impact-Adjusted Valuation
        new_fcf_per_share = current_fcf_per_share + fcf_impact_per_share
        adjusted_terminal_value = new_fcf_per_share * (1 + growth_rate) / (adjusted_discount_rate - growth_rate)
        adjusted_present_value = adjusted_terminal_value / (1 + adjusted_discount_rate)  # Simplified 1-year
        
        # Step 3: Price Impact Calculation
        if baseline_present_value > 0:
            price_impact_percentage = ((adjusted_present_value - baseline_present_value) / baseline_present_value) * 100
        else:
            price_impact_percentage = 0
        
        # Component Breakdown
        # Cash Flow Impact: How FCF change affects valuation (holding discount rate constant)
        if current_fcf_per_share != 0:
            fcf_only_impact_pct = ((new_fcf_per_share - current_fcf_per_share) / current_fcf_per_share) * 100
        else:
            fcf_only_impact_pct = 0
        
        # Multiple Compression: How discount rate change affects multiple (holding FCF constant)
        baseline_multiplier = (1 + growth_rate) / (base_discount_rate - growth_rate)
        adjusted_multiplier = (1 + growth_rate) / (adjusted_discount_rate - growth_rate)
        multiple_compression_pct = ((adjusted_multiplier - baseline_multiplier) / baseline_multiplier) * 100
        
        # Interaction Effects: Remaining impact
        interaction_pct = price_impact_percentage - fcf_only_impact_pct - multiple_compression_pct
        
        # Component breakdown
        component_breakdown = {
            'cash_flow_impact_pct': round(fcf_only_impact_pct, 2),
            'multiple_compression_pct': round(multiple_compression_pct, 2),
            'interaction_effects_pct': round(interaction_pct, 2)
        }
        
        return {
            'price_impact_percentage': round(price_impact_percentage, 2),
            'component_breakdown': component_breakdown,
            'baseline_valuation': {
                'fcf_per_share': round(current_fcf_per_share, 4),
                'discount_rate': round(base_discount_rate * 100, 2),
                'terminal_value': round(baseline_terminal_value, 2),
                'present_value': round(baseline_present_value, 2)
            },
            'adjusted_valuation': {
                'fcf_per_share': round(new_fcf_per_share, 4),
                'discount_rate': round(adjusted_discount_rate * 100, 2),
                'terminal_value': round(adjusted_terminal_value, 2),
                'present_value': round(adjusted_present_value, 2)
            },
            'valuation_multipliers': {
                'baseline': round(baseline_multiplier, 2),
                'adjusted': round(adjusted_multiplier, 2),
                'compression': round(multiple_compression_pct, 2)
            },
            'assumptions': {
                'growth_rate_percent': 3.0,
                'valuation_model': 'Gordon Growth (simplified)'
            }
        }


class FinalRiskScorer:
    """
    Final Risk Scorer - Combines all tiers into synthetic risk score
    
    Combines:
    - Exposure score (from Tier 1)
    - Quantitative impact (from Tier 2)
    - Valuation impact (from Tier 3)
    - Portfolio weight in S&P 500
    """
    
    def __init__(self):
        """Initialize Final Risk Scorer"""
        pass
    
    def calculate_final_risk_score(
        self,
        matching_pair: Dict[str, Any],
        quantitative_analysis: Dict[str, Any],
        valuation_impact: Dict[str, Any],
        company_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Calculate final synthetic risk score (0-100)
        
        Args:
            matching_pair: Tier 1 matching pair with exposure score
            quantitative_analysis: Tier 2 quantitative analysis
            valuation_impact: Tier 3 valuation impact
            company_data: Company data from universe
            
        Returns:
            Final risk score with breakdown
        """
        # Extract scores from each tier
        exposure_score = matching_pair.get('exposure_score', 0)
        quantitative_impact = quantitative_analysis.get('impact_assessment', {}).get('quantitative_impact_score', 0)
        price_impact = valuation_impact.get('tier_3_dcf_valuation', {}).get('price_impact_percentage', 0)
        
        # Get portfolio weight
        market_data = company_data.get('market_data', {})
        sp500_weight = market_data.get('sp500_weight', 0)
        
        # Normalize price impact to 0-100 scale
        # Assume max price impact is -50% to +50%, normalize to 0-100
        normalized_price_impact = abs(price_impact) * 2  # Scale to 0-100
        normalized_price_impact = min(normalized_price_impact, 100)
        
        # Portfolio significance weight (companies with higher S&P weight matter more)
        portfolio_weight_multiplier = 1.0 + (sp500_weight * 10)  # Scale portfolio weight
        
        # Final risk score calculation (weighted average)
        # Components:
        # - Exposure (30%): How much the company is exposed
        # - Quantitative Impact (40%): How severe the financial impact is
        # - Valuation Impact (30%): How much the stock price is affected
        
        final_risk_score = (
            exposure_score * 0.3 +
            quantitative_impact * 0.4 +
            normalized_price_impact * 0.3
        ) * portfolio_weight_multiplier
        
        # Cap at 100
        final_risk_score = min(final_risk_score, 100)
        
        # Risk classification
        if final_risk_score >= 75:
            risk_category = 'Critical'
        elif final_risk_score >= 60:
            risk_category = 'High'
        elif final_risk_score >= 40:
            risk_category = 'Moderate'
        elif final_risk_score >= 20:
            risk_category = 'Low'
        else:
            risk_category = 'Minimal'
        
        return {
            'final_risk_score': round(final_risk_score, 2),
            'risk_category': risk_category,
            'risk_components': {
                'exposure_score': round(exposure_score, 2),
                'quantitative_impact_score': round(quantitative_impact, 2),
                'price_impact_normalized': round(normalized_price_impact, 2),
                'portfolio_weight': sp500_weight
            },
            'portfolio_adjustment': {
                'multiplier': round(portfolio_weight_multiplier, 3),
                'reasoning': 'Higher S&P 500 weight increases systemic risk'
            },
            'risk_factors': {
                'geographic_exposure': matching_pair.get('matching_details', {}).get('by_country', {}).get('matched', False),
                'sector_dependency': matching_pair.get('matching_details', {}).get('by_sector', {}).get('matched', False),
                'regulatory_sensitivity': quantitative_analysis.get('regulatory_analysis', {}).get('overall_severity', 0) > 50,
                'sp500_weight': sp500_weight
            }
        }


def save_matching_pairs(pairs: List[Dict[str, Any]], output_path: str):
    """Save matching pairs to JSON file"""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Check if pairs are enriched with quantitative analysis
    has_quantitative = any('quantitative_analysis' in pair for pair in pairs)
    has_dcf = any('valuation_impact' in pair for pair in pairs)
    has_final_risk = any('final_risk_score' in pair for pair in pairs)
    
    # Group pairs by regulation
    pairs_by_regulation = {}
    for pair in pairs:
        reg_id = pair['regulation_id']
        if reg_id not in pairs_by_regulation:
            pairs_by_regulation[reg_id] = {
                'regulation_id': reg_id,
                'regulation_title': pair['regulation_title'],
                'regulation_country': pair['regulation_country'],
                'regulatory_category': pair['regulatory_category'],
                'effective_date': pair.get('effective_date'),
                'total_companies_matched': 0,
                'companies': []
            }
        
        # Build company entry
        company_entry = {
            'ticker': pair['company_ticker'],
            'company_name': pair['company_name'],
            'exposure_score': pair['exposure_score'],
            'matching_details': pair['matching_details']
        }
        
        # Add quantitative analysis if present
        if 'quantitative_analysis' in pair:
            company_entry['quantitative_analysis'] = pair['quantitative_analysis']
        
        # Add impact assessment if present
        if 'impact_assessment' in pair:
            company_entry['impact_assessment'] = pair['impact_assessment']
        
        # Add Tier 3 DCF valuation impact if present
        if 'valuation_impact' in pair:
            company_entry['valuation_impact'] = pair['valuation_impact']
        
        # Add final risk score if present
        if 'final_risk_score' in pair:
            company_entry['final_risk_score'] = pair['final_risk_score']
        
        pairs_by_regulation[reg_id]['companies'].append(company_entry)
        pairs_by_regulation[reg_id]['total_companies_matched'] += 1
    
    # Create summary
    summary = {
        'analysis_date': datetime.now().isoformat(),
        'total_pairs': len(pairs),
        'total_regulations': len(pairs_by_regulation),
        'has_quantitative_analysis': has_quantitative,
        'has_dcf_valuation': has_dcf,
        'has_final_risk_score': has_final_risk,
        'regulations': pairs_by_regulation,
        'summary_stats': {
            'avg_exposure_score': sum(p['exposure_score'] for p in pairs) / len(pairs) if pairs else 0,
            'max_exposure_score': max((p['exposure_score'] for p in pairs), default=0),
            'min_exposure_score': min((p['exposure_score'] for p in pairs), default=0)
        }
    }
    
    # Add quantitative stats if available
    if has_quantitative:
        impact_scores = [
            p.get('impact_assessment', {}).get('quantitative_impact_score', 0)
            for p in pairs
            if 'impact_assessment' in p
        ]
        if impact_scores:
            summary['summary_stats']['quantitative'] = {
                'avg_impact_score': sum(impact_scores) / len(impact_scores),
                'max_impact_score': max(impact_scores),
                'min_impact_score': min(impact_scores)
            }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Saved {len(pairs)} matching pairs to: {output_path}")
    print(f"   - {len(pairs_by_regulation)} regulations analyzed")
    print(f"   - Average exposure score: {summary['summary_stats']['avg_exposure_score']:.2f}")
    if has_quantitative and 'quantitative' in summary['summary_stats']:
        print(f"   - Average quantitative impact: {summary['summary_stats']['quantitative']['avg_impact_score']:.2f}")
        print(f"   - Includes Tier 2: Quant Engine analysis ✅")
    if has_dcf:
        print(f"   - Includes Tier 3: DCF Valuation analysis ✅")
    if has_final_risk:
        final_risk_scores = [p.get('final_risk_score', {}).get('final_risk_score', 0) for p in pairs if 'final_risk_score' in p]
        if final_risk_scores:
            print(f"   - Average final risk score: {sum(final_risk_scores) / len(final_risk_scores):.2f} ✅")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Impact Calculator - 3-Tier Valuation Architecture',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--directives_dir',
        type=str,
        default='data/generated/extracted_directives',
        help='Directory containing extracted directives JSON files'
    )
    parser.add_argument(
        '--company_universe',
        type=str,
        default='data/generated/company_universe/company_universe.json',
        help='Path to company universe JSON file'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/generated/impact_analysis/matching_pairs.json',
        help='Output path for matching pairs results'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.1,
        help='Exposure score threshold (0.0-1.0, default: 0.1 = 10 percent exposure)'
    )
    parser.add_argument(
        '--region',
        type=str,
        default='us-east-1',
        help='AWS region for Comprehend (default: us-east-1)'
    )
    parser.add_argument(
        '--quant-engine',
        action='store_true',
        help='Enable Tier 2: Quant Engine (multi-source processing with financial/regulatory/market analysis)'
    )
    parser.add_argument(
        '--limit-pairs',
        type=int,
        default=None,
        help='Limit number of pairs to process (useful for testing Quant Engine)'
    )
    
    args = parser.parse_args()
    
    if not 0.0 <= args.threshold <= 1.0:
        print("❌ Threshold must be between 0.0 and 1.0")
        return 1
    
    # Initialize orchestrator
    orchestrator = ImpactOrchestrator(region_name=args.region)
    
    # Load data
    company_universe = orchestrator.load_company_universe(args.company_universe)
    regulatory_documents = orchestrator.load_regulatory_documents(args.directives_dir)
    
    if not regulatory_documents:
        print("❌ No regulatory documents found to analyze")
        return 1
    
    # Tier 1: Orchestrate analysis (Matching Pairs)
    print("\n" + "="*80)
    print("🚀 TIER 1: Impact Orchestrator & Matching Pairs")
    print("="*80)
    matching_pairs = orchestrator.orchestrate_analysis(
        regulatory_documents,
        company_universe,
        exposure_threshold=args.threshold
    )
    
    # Apply limit if specified
    if args.limit_pairs:
        matching_pairs = matching_pairs[:args.limit_pairs]
        print(f"📊 Limited to first {args.limit_pairs} pairs for testing")
    
    # Tier 2: Quant Engine (optional)
    if args.quant_engine:
        print("\n" + "="*80)
        print("🔬 TIER 2: Quant Engine - Multi-Source Processing")
        print("="*80)
        
        # Initialize Quant Engine
        quant_engine = QuantEngine(use_sagemaker=False, region_name=args.region)
        
        # Process pairs through Quant Engine
        print(f"📈 Processing {len(matching_pairs)} pairs through Quant Engine...")
        enriched_pairs = []
        
        for i, pair in enumerate(matching_pairs):
            if (i + 1) % 10 == 0:
                print(f"   Progress: {i+1}/{len(matching_pairs)} pairs processed...")
            
            try:
                enriched_pair = quant_engine.process_matching_pair(
                    pair,
                    company_universe,
                    regulatory_documents
                )
                enriched_pairs.append(enriched_pair)
            except Exception as e:
                print(f"⚠️ Error processing pair {i+1}: {e}")
                enriched_pairs.append(pair)  # Keep original if enrichment fails
        
        matching_pairs = enriched_pairs
        print(f"✅ Quant Engine processing complete")
    
    # Save results
    save_matching_pairs(matching_pairs, args.output)
    
    return 0


if __name__ == '__main__':
    exit(main())

