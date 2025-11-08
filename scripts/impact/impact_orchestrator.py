#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Impact Orchestrator - Regulatory Document Impact Analysis

This script analyzes regulatory documents from the generated data folder using AWS Comprehend
and matches them with companies from the company universe, calculating exposure scores.

Usage:
    python impact_orchestrator.py --directives_dir <path> --company_universe <path> --output <path> --threshold <float>
    
Example:
    python impact_orchestrator.py --threshold 0.3
"""

import json
import os
import sys
import io
import argparse
import re
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class ImpactOrchestrator:
    """Orchestrates impact analysis of regulatory documents on companies"""
    
    def __init__(self, region_name: str = 'us-east-1'):
        """Initialize AWS Comprehend client"""
        self.region_name = region_name
        self.aws_available = False
        
        # Try to initialize AWS Comprehend client
        try:
            self.comprehend = boto3.client('comprehend', region_name=region_name)
            # Quick test - just creating client verifies credentials exist
            # Actual API call will be tested when needed
            self.aws_available = True
        except Exception:
            # AWS not available - will use fallback
            self.comprehend = None
            self.aws_available = False
        
        # Cache for Comprehend responses
        self._comprehend_cache = {}
        
    def load_company_universe(self, file_path: str) -> Dict[str, Any]:
        """Load company universe from JSON file"""
        print(f"📊 Loading company universe from {file_path}...")
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        print(f"✅ Loaded {len(data)} companies")
        return data
    
    def load_directives(self, directives_dir: str) -> List[Dict[str, Any]]:
        """Load all extracted directives from directory"""
        print(f"📄 Loading directives from {directives_dir}...")
        directives = []
        directives_path = Path(directives_dir)
        
        for file_path in directives_path.glob("*_extracted.json"):
            # Skip all_directives_extracted.json as it's a summary
            if file_path.name == "all_directives_extracted.json":
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                # Handle both single directive and dict of directives
                if isinstance(data, dict):
                    if 'document_id' in data:
                        # Single directive
                        directives.append(data)
                    else:
                        # Multiple directives in one file
                        for doc_id, doc_data in data.items():
                            if isinstance(doc_data, dict) and 'document_id' in doc_data:
                                directives.append(doc_data)
            except Exception as e:
                print(f"⚠️ Error loading {file_path}: {e}")
                continue
        
        print(f"✅ Loaded {len(directives)} directives")
        return directives
    
    def analyze_with_comprehend(self, text: str, document_id: str) -> Dict[str, Any]:
        """
        Analyze text using AWS Comprehend
        Returns entities, key phrases, sentiment, and syntax analysis
        Falls back to empty results if AWS is not available
        """
        # Check cache first
        if document_id in self._comprehend_cache:
            return self._comprehend_cache[document_id]
        
        # If AWS not available, return empty results
        if not self.aws_available or not self.comprehend:
            result = {
                'entities': [],
                'key_phrases': [],
                'sentiment': None,
                'total_chunks_analyzed': 0
            }
            self._comprehend_cache[document_id] = result
            return result
        
        # Comprehend has limits: 5000 chars per request
        MAX_CHARS = 5000
        all_entities = []
        all_key_phrases = []
        sentiments = []
        
        # Split text into chunks
        chunks = [text[i:i+MAX_CHARS] for i in range(0, len(text), MAX_CHARS)]
        # Limit to first 20 chunks to control costs
        chunks = chunks[:20]
        
        for i, chunk in enumerate(chunks):
            try:
                # Detect entities
                entities_response = self.comprehend.detect_entities(
                    Text=chunk,
                    LanguageCode='en'
                )
                all_entities.extend(entities_response['Entities'])
                
                # Detect key phrases
                phrases_response = self.comprehend.detect_key_phrases(
                    Text=chunk,
                    LanguageCode='en'
                )
                all_key_phrases.extend(phrases_response['KeyPhrases'])
                
                # Detect sentiment (only first chunk to save costs)
                if i == 0:
                    sentiment_response = self.comprehend.detect_sentiment(
                        Text=chunk,
                        LanguageCode='en'
                    )
                    sentiments.append(sentiment_response)
                    
            except (ClientError, Exception) as e:
                # If credentials expired or any error, return empty results
                result = {
                    'entities': [],
                    'key_phrases': [],
                    'sentiment': None,
                    'total_chunks_analyzed': 0
                }
                self._comprehend_cache[document_id] = result
                return result
        
        # Aggregate results
        result = {
            'entities': all_entities,
            'key_phrases': all_key_phrases,
            'sentiment': sentiments[0] if sentiments else None,
            'total_chunks_analyzed': len(chunks)
        }
        
        # Cache result
        self._comprehend_cache[document_id] = result
        
        return result
    
    def extract_text_from_directive(self, directive: Dict[str, Any]) -> str:
        """Extract text content from directive for Comprehend analysis"""
        text_parts = []
        
        # Extract from extracted_info
        extracted_info = directive.get('extracted_info', {})
        if isinstance(extracted_info, str):
            # Try to parse as JSON if it's a string
            try:
                extracted_info = json.loads(extracted_info)
            except:
                text_parts.append(extracted_info)
        elif isinstance(extracted_info, dict):
            # Extract text from various fields
            text_parts.append(extracted_info.get('title', ''))
            text_parts.append(extracted_info.get('scope', ''))
            text_parts.append(', '.join(extracted_info.get('affected_sectors', [])))
            text_parts.append(', '.join(extracted_info.get('affected_entities', [])))
            text_parts.append(', '.join(extracted_info.get('key_requirements', [])))
            
            # Add requirement details
            for req in extracted_info.get('key_requirement_details', []):
                text_parts.append(req.get('requirement', ''))
                text_parts.append(req.get('compliance_action', ''))
        
        # Add category
        category = directive.get('category', '')
        if category:
            text_parts.append(category)
        
        # Combine all text
        text = ' '.join([part for part in text_parts if part])
        
        # If we have raw content, append it (truncated)
        if isinstance(extracted_info, dict) and 'raw_content' in extracted_info:
            raw = extracted_info['raw_content']
            if isinstance(raw, str):
                # Take first 10000 chars of raw content
                text += ' ' + raw[:10000]
        
        return text
    
    def match_companies_to_bill(
        self, 
        directive: Dict[str, Any], 
        company_universe: Dict[str, Any],
        comprehend_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Match companies from universe to a regulatory bill/directive
        Returns list of matches with exposure scores
        """
        matches = []
        extracted_info = directive.get('extracted_info', {})
        
        # Parse extracted_info if it's a string
        if isinstance(extracted_info, str):
            try:
                extracted_info = json.loads(extracted_info)
            except:
                extracted_info = {}
        
        # Helper function to normalize list/string inputs
        def normalize_to_list(value, default=None):
            if value is None:
                return default if default is not None else []
            if isinstance(value, list):
                return value
            return [value] if value else []
        
        # Extract bill metadata
        bill_country = str(extracted_info.get('country', '')).upper()
        bill_sectors = [str(s).lower() for s in normalize_to_list(extracted_info.get('affected_sectors', []))]
        bill_entities = [str(e).lower() for e in normalize_to_list(extracted_info.get('affected_entities', []))]
        
        # Extract entities and phrases from Comprehend
        comprehend_entities = comprehend_results.get('entities', [])
        comprehend_phrases = comprehend_results.get('key_phrases', [])
        
        # Extract organization names from Comprehend
        org_names = [
            e['Text'].lower() 
            for e in comprehend_entities 
            if e['Type'] == 'ORGANIZATION' and e['Score'] > 0.7
        ]
        
        # Extract locations from Comprehend
        locations = [
            e['Text'].lower() 
            for e in comprehend_entities 
            if e['Type'] == 'LOCATION' and e['Score'] > 0.5
        ]
        
        # Extract key phrases
        key_phrases = [
            p['Text'].lower() 
            for p in comprehend_phrases 
            if p['Score'] > 0.7
        ]
        
        # Map country strings to standardized format
        country_mapping = {
            'USA': ['united states', 'usa', 'us', 'america', 'north america'],
            'EU': ['europe', 'european union', 'eu', 'european', 'emeai'],
            'China': ['china', 'chinese', 'peoples republic'],
            'Japan': ['japan', 'japanese'],
            'UK': ['united kingdom', 'uk', 'britain', 'british']
        }
        
        # Normalize bill country
        bill_country_normalized = None
        for country_code, aliases in country_mapping.items():
            if any(alias in bill_country.lower() for alias in aliases):
                bill_country_normalized = country_code
                break
        
        # Process each company
        for ticker, company_data in company_universe.items():
            exposure_factors = {
                'sector_match': 0.0,
                'geography_match': 0.0,
                'explicit_mention': 0.0,
                'supply_chain_match': 0.0,
                'regulatory_risk_match': 0.0,
                'segment_match': 0.0
            }
            
            market_data = company_data.get('market_data', {})
            data_points = company_data.get('data_points', {})
            
            # 1. Sector Matching (0-30 points)
            company_sector = str(market_data.get('sector', '')).lower()
            company_industry = str(market_data.get('industry', '')).lower()
            
            for bill_sector in bill_sectors:
                # Direct sector match
                if bill_sector in company_sector or company_sector in bill_sector:
                    exposure_factors['sector_match'] += 15.0
                # Industry match
                if bill_sector in company_industry or company_industry in bill_sector:
                    exposure_factors['sector_match'] += 10.0
                # Partial match (word overlap)
                bill_words = set(bill_sector.split())
                company_words = set((company_sector + ' ' + company_industry).split())
                if bill_words & company_words:
                    exposure_factors['sector_match'] += 5.0
            
            exposure_factors['sector_match'] = min(exposure_factors['sector_match'], 30.0)
            
            # 2. Geography Matching (0-25 points)
            geography = data_points.get('geography', {})
            company_countries = [c.lower() for c in geography.get('countries', [])]
            has_na = geography.get('has_na', False)
            has_eu = geography.get('has_eu', False)
            
            # Country code matching
            if bill_country_normalized:
                if bill_country_normalized == 'USA' and has_na:
                    exposure_factors['geography_match'] += 15.0
                elif bill_country_normalized == 'EU' and has_eu:
                    exposure_factors['geography_match'] += 15.0
                elif bill_country_normalized in ['China', 'Japan', 'UK']:
                    # Check specific country in company countries
                    country_name_map = {
                        'China': ['china', 'chinese'],
                        'Japan': ['japan', 'japanese'],
                        'UK': ['united kingdom', 'uk', 'britain', 'british']
                    }
                    for country_term in country_name_map.get(bill_country_normalized, []):
                        if any(country_term in c for c in company_countries):
                            exposure_factors['geography_match'] += 15.0
                            break
            
            # Location mentions from Comprehend
            for location in locations:
                for company_country in company_countries:
                    if location in company_country or company_country in location:
                        exposure_factors['geography_match'] += 5.0
                        break
            
            exposure_factors['geography_match'] = min(exposure_factors['geography_match'], 25.0)
            
            # 3. Explicit Company Mention (0-20 points)
            company_name = str(market_data.get('company_name', '')).lower()
            ticker_lower = str(ticker).lower()
            
            # Check if company name or ticker appears in org names from Comprehend
            for org_name in org_names:
                if ticker_lower in org_name or company_name in org_name:
                    exposure_factors['explicit_mention'] = 20.0
                    break
            
            # Check key phrases for company-related terms
            company_words = set(company_name.split())
            for phrase in key_phrases:
                if company_words & set(phrase.split()):
                    exposure_factors['explicit_mention'] += 10.0
                    break
            
            exposure_factors['explicit_mention'] = min(exposure_factors['explicit_mention'], 20.0)
            
            # 4. Segment Matching (0-10 points)
            segments = data_points.get('segments', [])
            segment_text = ' '.join([s.lower() for s in segments])
            
            for bill_sector in bill_sectors:
                bill_words = set(bill_sector.split())
                segment_words = set(segment_text.split())
                if bill_words & segment_words:
                    exposure_factors['segment_match'] += 5.0
            
            exposure_factors['segment_match'] = min(exposure_factors['segment_match'], 10.0)
            
            # 5. Supply Chain Match (0-10 points)
            supply_chain = data_points.get('supply_chain', {})
            dependencies_raw = supply_chain.get('dependencies', '')
            # Handle both string and list formats
            if isinstance(dependencies_raw, list):
                dependencies = ' '.join([str(d).lower() for d in dependencies_raw])
            else:
                dependencies = str(dependencies_raw).lower() if dependencies_raw else ''
            suppliers = ' '.join([s.lower() for s in supply_chain.get('key_suppliers', [])])
            
            supply_chain_text = dependencies + ' ' + suppliers
            
            for bill_sector in bill_sectors:
                if bill_sector in supply_chain_text:
                    exposure_factors['supply_chain_match'] += 5.0
            
            exposure_factors['supply_chain_match'] = min(exposure_factors['supply_chain_match'], 10.0)
            
            # 6. Regulatory Risk Match (0-5 points)
            regulatory_risks = data_points.get('regulatory_risks', [])
            risk_text = ' '.join([r.lower() for r in regulatory_risks])
            
            # Check if bill category aligns with existing regulatory risks
            category = str(directive.get('category', '')).lower()
            if any(keyword in category for keyword in ['environmental', 'tax', 'trade', 'privacy', 'labor', 'financial']):
                for risk in regulatory_risks:
                    risk_lower = risk.lower()
                    if any(keyword in risk_lower for keyword in ['environmental', 'tax', 'trade', 'privacy', 'labor', 'financial', 'regulation']):
                        exposure_factors['regulatory_risk_match'] = 5.0
                        break
            
            # Calculate total exposure score (0-100)
            total_score = sum(exposure_factors.values())
            
            # Only include if score > 0
            if total_score > 0:
                match = {
                    'ticker': ticker,
                    'company_name': market_data.get('company_name', ''),
                    'exposure_score': round(total_score, 2),
                    'exposure_factors': exposure_factors,
                    'sector': company_sector,
                    'industry': company_industry,
                    'has_geographic_match': exposure_factors['geography_match'] > 0,
                    'is_explicitly_mentioned': exposure_factors['explicit_mention'] > 0
                }
                matches.append(match)
        
        # Sort by exposure score (highest first)
        matches.sort(key=lambda x: x['exposure_score'], reverse=True)
        
        return matches
    
    def analyze_all_directives(
        self,
        directives: List[Dict[str, Any]],
        company_universe: Dict[str, Any],
        exposure_threshold: float = 0.0
    ) -> Dict[str, Any]:
        """
        Analyze all directives and match with companies
        Returns comprehensive analysis results
        """
        results = {
            'analysis_date': datetime.now().isoformat(),
            'total_directives': len(directives),
            'total_companies': len(company_universe),
            'exposure_threshold': exposure_threshold,
            'directive_analyses': []
        }
        
        for directive in directives:
            document_id = directive.get('document_id', 'unknown')
            print(f"\n📋 Analyzing: {document_id}")
            
            # Skip failed extractions
            if directive.get('processing_status') == 'failed':
                print(f"⚠️ Skipping failed directive: {document_id}")
                continue
            
            # Extract text for Comprehend
            text = self.extract_text_from_directive(directive)
            if not text or len(text) < 100:
                print(f"⚠️ Insufficient text for {document_id}")
                continue
            
            # Analyze with Comprehend
            try:
                comprehend_results = self.analyze_with_comprehend(text, document_id)
            except Exception as e:
                print(f"❌ Comprehend error for {document_id}: {e}")
                comprehend_results = {'entities': [], 'key_phrases': [], 'sentiment': None}
            
            # Match companies
            matches = self.match_companies_to_bill(directive, company_universe, comprehend_results)
            
            # Filter by threshold
            filtered_matches = [
                m for m in matches 
                if m['exposure_score'] >= exposure_threshold * 100  # Convert to 0-100 scale
            ]
            
            # Extract directive metadata
            extracted_info = directive.get('extracted_info', {})
            if isinstance(extracted_info, str):
                try:
                    extracted_info = json.loads(extracted_info)
                except:
                    extracted_info = {}
            
            # Store full analysis for this directive (with all matches)
            directive_analysis = {
                'document_id': document_id,
                'title': extracted_info.get('title', 'Unknown'),
                'country': extracted_info.get('country', 'Unknown'),
                'category': directive.get('category', 'Unknown'),
                'effective_date': extracted_info.get('effective_date'),
                'total_matches': len(matches),
                'filtered_matches': len(filtered_matches),
                'all_companies': filtered_matches,  # All companies above threshold
                'comprehend_summary': {
                    'entities_found': len(comprehend_results.get('entities', [])),
                    'key_phrases_found': len(comprehend_results.get('key_phrases', [])),
                    'sentiment': comprehend_results.get('sentiment', {}).get('Sentiment') if comprehend_results.get('sentiment') else None
                },
                'analysis_metadata': {
                    'analysis_date': datetime.now().isoformat(),
                    'exposure_threshold': exposure_threshold,
                    'total_companies_in_universe': len(company_universe)
                }
            }
            
            results['directive_analyses'].append({
                'document_id': document_id,
                'title': extracted_info.get('title', 'Unknown'),
                'total_matches': len(matches),
                'filtered_matches': len(filtered_matches),
                'top_companies': filtered_matches[:10]  # Top 10 for summary
            })
            
            # Store full analysis for individual file saving
            results['_full_analyses'] = results.get('_full_analyses', [])
            results['_full_analyses'].append(directive_analysis)
            
            print(f"✅ Found {len(matches)} company matches ({len(filtered_matches)} above threshold)")
        
        return results
    
    def save_results(self, results: Dict[str, Any], output_path: str):
        """Save analysis results - one file per directive plus a summary index"""
        output_file = Path(output_path)
        output_dir = output_file.parent
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Extract full analyses for individual file saving
        full_analyses = results.get('_full_analyses', [])
        
        # Save individual files for each directive
        saved_files = []
        for directive_analysis in full_analyses:
            document_id = directive_analysis['document_id']
            
            # Create safe filename from document_id
            safe_filename = self._create_safe_filename(document_id)
            individual_file = output_dir / f"{safe_filename}_impact.json"
            
            # Save individual directive impact analysis
            with open(individual_file, 'w', encoding='utf-8') as f:
                json.dump(directive_analysis, f, indent=2, ensure_ascii=False)
            
            saved_files.append({
                'document_id': document_id,
                'title': directive_analysis.get('title', 'Unknown'),
                'filename': individual_file.name,
                'total_matches': directive_analysis['total_matches'],
                'filtered_matches': directive_analysis['filtered_matches']
            })
            
            print(f"💾 Saved: {individual_file.name} ({directive_analysis['filtered_matches']} companies)")
        
        # Create summary index file
        summary_data = {
            'analysis_date': results.get('analysis_date', datetime.now().isoformat()),
            'total_directives': len(full_analyses),
            'total_companies': results['total_companies'],
            'exposure_threshold': results['exposure_threshold'],
            'directives': saved_files,
            'summary_stats': {
                'total_matches': sum(d['total_matches'] for d in full_analyses),
                'total_filtered_matches': sum(d['filtered_matches'] for d in full_analyses),
                'avg_companies_per_directive': sum(d['filtered_matches'] for d in full_analyses) / len(full_analyses) if full_analyses else 0
            }
        }
        
        # Save summary index
        summary_file = output_dir / 'impact_analysis_index.json'
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Summary index saved: {summary_file.name}")
        
        # Print summary
        print("\n" + "="*80)
        print("📊 ANALYSIS SUMMARY")
        print("="*80)
        print(f"Total Directives Analyzed: {len(full_analyses)}")
        print(f"Total Companies in Universe: {results['total_companies']}")
        print(f"Exposure Threshold: {results['exposure_threshold']*100:.1f}%")
        print(f"Individual Files Saved: {len(saved_files)}")
        
        total_matches = sum(d['total_matches'] for d in full_analyses)
        total_filtered = sum(d['filtered_matches'] for d in full_analyses)
        
        print(f"Total Company-Directive Matches: {total_matches}")
        print(f"Matches Above Threshold: {total_filtered}")
        
        print("\n📋 Per-Directive Summary:")
        for directive in saved_files:
            print(f"  • {directive['filename']}")
            print(f"    {directive['filtered_matches']}/{directive['total_matches']} matches above threshold")
            print(f"    Title: {directive['title'][:70]}")
    
    def _create_safe_filename(self, document_id: str) -> str:
        """Create a safe filename from document_id"""
        # Remove or replace problematic characters
        safe_name = document_id
        
        # Remove file extensions if present
        safe_name = safe_name.replace('.html', '').replace('.xml', '').replace('.pdf', '')
        
        # Replace problematic characters
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', safe_name)
        safe_name = re.sub(r'[^\w\s-]', '_', safe_name)
        
        # Replace spaces with underscores
        safe_name = safe_name.replace(' ', '_')
        
        # Limit length
        if len(safe_name) > 100:
            safe_name = safe_name[:100]
        
        # Remove trailing underscores
        safe_name = safe_name.rstrip('_')
        
        return safe_name


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Impact Orchestrator - Analyze regulatory document impact on companies'
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
        default='data/generated/impact_analysis/impact_analysis.json',
        help='Output directory path (individual files will be saved here, plus an index file)'
    )
    parser.add_argument(
        '--threshold',
        type=float,
        default=0.1,
        help='Exposure score threshold (0.0-1.0, default: 0.1 = 10% exposure)'
    )
    parser.add_argument(
        '--region',
        type=str,
        default='us-east-1',
        help='AWS region for Comprehend (default: us-east-1)'
    )
    
    args = parser.parse_args()
    
    # Validate threshold
    if not 0.0 <= args.threshold <= 1.0:
        print("❌ Threshold must be between 0.0 and 1.0")
        return 1
    
    # Initialize orchestrator
    orchestrator = ImpactOrchestrator(region_name=args.region)
    
    # Load data
    company_universe = orchestrator.load_company_universe(args.company_universe)
    directives = orchestrator.load_directives(args.directives_dir)
    
    if not directives:
        print("❌ No directives found to analyze")
        return 1
    
    # Analyze
    results = orchestrator.analyze_all_directives(
        directives,
        company_universe,
        exposure_threshold=args.threshold
    )
    
    # Save results
    orchestrator.save_results(results, args.output)
    
    return 0


if __name__ == '__main__':
    exit(main())

