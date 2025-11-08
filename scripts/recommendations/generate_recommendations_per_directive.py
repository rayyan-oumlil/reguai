#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate recommendations per directive from individual impact analysis files
"""
import json
import sys
import io
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Fix encoding for Windows console
if sys.platform == 'win32':
    if not isinstance(sys.stdout, io.TextIOWrapper):
        try:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')
        except (AttributeError, ValueError):
            pass

# Import recommendation generator
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.recommendations.recommendation_generator import RecommendationGenerator  # type: ignore


def load_individual_impact_file(impact_file: Path) -> Optional[Dict[str, Any]]:
    """Load individual impact analysis file"""
    try:
        with open(impact_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"⚠️ Error loading {impact_file.name}: {e}")
        return None


def convert_impact_file_to_matching_pairs_format(impact_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert individual impact file format to matching_pairs format for recommendation generator"""
    reg_id = impact_data.get('document_id', 'unknown')
    
    # Extract all companies (they may or may not have DCF analysis)
    # If they have DCF, use it; otherwise use exposure_score for recommendations
    all_companies = impact_data.get('all_companies', [])
    
    # Format as matching_pairs structure
    matching_pairs_format = {
        'regulations': {
            reg_id: {
                'regulation_id': reg_id,
                'regulation_title': impact_data.get('title', 'Unknown'),
                'regulation_country': impact_data.get('country', 'N/A'),
                'regulatory_category': impact_data.get('category', 'N/A'),
                'effective_date': impact_data.get('effective_date'),
                'total_companies_matched': len(all_companies),
                'companies': all_companies
            }
        }
    }
    
    return matching_pairs_format


def main():
    """Generate recommendations for each directive"""
    impact_analysis_dir = Path('data/generated/impact_analysis')
    recommendations_dir = Path('data/generated/recommendations')
    recommendations_dir.mkdir(parents=True, exist_ok=True)
    
    # Load matching_pairs.json (has complete Tier 2/3 data)
    matching_pairs_path = impact_analysis_dir / 'matching_pairs.json'
    
    if not matching_pairs_path.exists():
        print("❌ matching_pairs.json not found")
        return 1
    
    print(f"📂 Loading from matching_pairs.json")
    
    # Load matching pairs data
    try:
        with open(matching_pairs_path, 'r', encoding='utf-8') as f:
            matching_pairs_data = json.load(f)
    except Exception as e:
        print(f"❌ Error loading matching_pairs.json: {e}")
        return 1
    
    if 'regulations' not in matching_pairs_data:
        print("❌ Invalid format in matching_pairs.json")
        return 1
    
    # Initialize recommendation generator
    generator = RecommendationGenerator(region_name='us-east-1')
    
    # Note: Generator will use fallback justifications if AWS is not available
    if not generator.aws_available:
        print("⚠️  AWS Bedrock not available - will use automatic fallback justifications")
        print("💡 Recommendations will be generated based on risk scores without Bedrock")
    
    # Generate recommendations for each directive
    all_recommendations = {}
    
    for reg_id, reg_data in matching_pairs_data.get('regulations', {}).items():
        print(f"\n{'='*80}")
        print(f"📋 Processing: {reg_id}")
        print(f"{'='*80}")
        
        reg_title = reg_data.get('regulation_title', reg_id)
        
        # Check if there are companies
        companies = reg_data.get('companies', [])
        if not companies:
            print(f"⚠️ No companies found for {reg_id}, skipping")
            continue
        
        # Filter companies with DCF analysis (have final_risk_score and valuation_impact)
        companies_with_dcf = [c for c in companies if c.get('final_risk_score') and c.get('valuation_impact')]
        
        if not companies_with_dcf:
            print(f"⚠️ No companies with DCF analysis in {reg_id}, skipping")
            continue
        
        print(f"✅ Found {len(companies_with_dcf)} companies with DCF analysis out of {len(companies)} total")
        
        # Create matching_pairs format for this directive
        matching_pairs_format = {
            'regulations': {
                reg_id: {
                    'regulation_id': reg_id,
                    'regulation_title': reg_title,
                    'regulation_country': reg_data.get('regulation_country', 'N/A'),
                    'companies': companies_with_dcf
                }
            }
        }
        
        # Generate recommendations for this directive
        try:
            recommendations = generator.generate_recommendations(
                matching_pairs_format,
                output_path=None  # Don't save yet, we'll save per directive
            )
            
            # Add regulation context
            recommendations['regulation_id'] = reg_id
            recommendations['regulation_title'] = reg_title
            
            # Save individual recommendation file
            safe_reg_id = reg_id.replace('/', '_').replace('\\', '_').replace(' ', '_')
            rec_file = recommendations_dir / f"{safe_reg_id}_recommendations.json"
            
            with open(rec_file, 'w', encoding='utf-8') as f:
                json.dump(recommendations, f, indent=2, ensure_ascii=False)
            
            print(f"💾 Saved recommendations to: {rec_file.name}")
            all_recommendations[reg_id] = recommendations
            
        except Exception as e:
            print(f"❌ Error generating recommendations for {reg_id}: {e}")
            continue
    
    # Create aggregated recommendations file
    if all_recommendations:
        aggregated = {
            'generated_at': datetime.now().isoformat(),
            'total_directives': len(all_recommendations),
            'recommendations_by_directive': all_recommendations,
            'summary': {
                'total_reduce': sum(len(r.get('recommendations', {}).get('reduce', [])) for r in all_recommendations.values()),
                'total_increase': sum(len(r.get('recommendations', {}).get('increase', [])) for r in all_recommendations.values())
            }
        }
        
        aggregated_file = recommendations_dir / 'all_recommendations.json'
        with open(aggregated_file, 'w', encoding='utf-8') as f:
            json.dump(aggregated, f, indent=2, ensure_ascii=False)
        
        print(f"\n{'='*80}")
        print(f"✅ Generated recommendations for {len(all_recommendations)} directive(s)")
        print(f"💾 Aggregated file: {aggregated_file.name}")
        print(f"{'='*80}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

