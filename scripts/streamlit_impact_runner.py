"""
Streamlit Impact Runner - Run Impact Analysis from Streamlit UI

Provides functions to run impact analysis pipeline directly from Streamlit
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import time


def list_available_regulations(extracted_directives_dir: str = 'data/generated/extracted_directives/') -> List[Dict[str, str]]:
    """
    List available regulatory extraction files
    
    Args:
        extracted_directives_dir: Directory containing extracted directives
        
    Returns:
        List of available regulations with metadata
    """
    regulations = []
    directives_path = Path(extracted_directives_dir)
    
    for file_path in directives_path.glob("*_extracted.json"):
        # Skip all_directives_extracted.json as it's a summary
        if file_path.name == "all_directives_extracted.json":
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Extract metadata
            if isinstance(data, dict):
                if 'document_id' in data:
                    # Single directive
                    extracted_info = data.get('extracted_info', {})
                    regulations.append({
                        'filename': file_path.name,
                        'title': extracted_info.get('title', 'N/A'),
                        'country': extracted_info.get('country', 'N/A'),
                        'category': data.get('category', 'N/A'),
                        'document_id': data.get('document_id', file_path.name)
                    })
        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}")
            continue
    
    return regulations


def run_impact_pipeline(
    selected_regulation: str,
    exposure_threshold: float = 0.3,
    enable_quant_engine: bool = True,
    limit_pairs: Optional[int] = None,
    high_risk_threshold: float = 60.0,
    low_risk_threshold: float = 30.0
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Run complete impact analysis pipeline
    
    Args:
        selected_regulation: Filename of selected regulation
        exposure_threshold: Threshold for matching (0.0-1.0)
        enable_quant_engine: Enable 3-tier valuation analysis
        limit_pairs: Limit number of pairs to process (for testing)
        high_risk_threshold: High risk threshold for recommendations
        low_risk_threshold: Low risk threshold for recommendations
        
    Returns:
        Tuple of (success, message, results_dict)
    """
    success = False
    message = ""
    results = None
    
    try:
        # Step 1: Create matching pairs with selected regulation
        message += "🔍 Creating matching pairs...\n"
        cmd1 = [
            sys.executable,
            "scripts/impact_orchestrator.py",
            "--directives_dir", "data/generated/extracted_directives",
            "--company_universe", "data/generated/company_universe/company_universe.json",
            "--output", "data/generated/impact_analysis/matching_pairs.json",
            "--threshold", str(exposure_threshold)
        ]
        
        result1 = subprocess.run(
            cmd1,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result1.returncode != 0:
            message += f"❌ Step 1 failed: {result1.stderr[:500]}\n"
            return success, message, results
        
        message += f"✅ Step 1 complete: {result1.stdout[-200:]}\n\n"
        
        # Step 2: Run impact calculator with quant engine
        if enable_quant_engine:
            message += "📊 Running 3-tier valuation analysis...\n"
            cmd2 = [
                sys.executable,
                "scripts/impact_calculator.py",
                "--quant-engine",
                "--threshold", str(exposure_threshold)
            ]
            
            if limit_pairs:
                cmd2.extend(["--limit-pairs", str(limit_pairs)])
            
            result2 = subprocess.run(
                cmd2,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            if result2.returncode != 0:
                message += f"❌ Step 2 failed: {result2.stderr[:500]}\n"
                return success, message, results
            
            message += f"✅ Step 2 complete: {result2.stdout[-200:]}\n\n"
        
        # Step 3: Generate recommendations
        message += "🤖 Generating recommendations with Bedrock...\n"
        cmd3 = [
            sys.executable,
            "scripts/recommendation_generator.py",
            "--high-risk-threshold", str(high_risk_threshold),
            "--low-risk-threshold", str(low_risk_threshold)
        ]
        
        result3 = subprocess.run(
            cmd3,
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout
        )
        
        if result3.returncode != 0:
            message += f"⚠️ Step 3 failed (non-critical): {result3.stderr[:500]}\n"
            # Don't fail overall if recommendations fail
        else:
            message += f"✅ Step 3 complete: {result3.stdout[-200:]}\n\n"
        
        # Load results
        try:
            with open('data/generated/impact_analysis/matching_pairs.json', 'r') as f:
                results = json.load(f)
                message += f"✅ Loaded {results.get('total_pairs', 0)} matching pairs\n"
        except Exception as e:
            message += f"⚠️ Could not load results: {e}\n"
        
        success = True
        message += "\n🎉 Analysis complete!"
        
    except subprocess.TimeoutExpired:
        message += "\n❌ Analysis timed out. Please try with fewer companies or higher thresholds."
        success = False
        
    except Exception as e:
        message += f"\n❌ Unexpected error: {str(e)[:500]}"
        success = False
    
    return success, message, results


def get_pipeline_status() -> Dict[str, Any]:
    """
    Check status of impact analysis pipeline
    
    Returns:
        Dictionary with status information
    """
    status = {
        'has_matching_pairs': False,
        'has_recommendations': False,
        'has_quant_analysis': False,
        'pair_count': 0,
        'recommendation_count': 0,
        'last_modified': None
    }
    
    # Check matching pairs
    pairs_path = Path('data/generated/impact_analysis/matching_pairs.json')
    if pairs_path.exists():
        status['has_matching_pairs'] = True
        status['last_modified'] = pairs_path.stat().st_mtime
        
        try:
            with open(pairs_path, 'r') as f:
                pairs_data = json.load(f)
                status['pair_count'] = pairs_data.get('total_pairs', 0)
                status['has_quant_analysis'] = pairs_data.get('has_quantitative_analysis', False)
                status['has_dcf_valuation'] = pairs_data.get('has_dcf_valuation', False)
        except:
            pass
    
    # Check recommendations
    rec_path = Path('data/generated/recommendations/recommendations.json')
    if rec_path.exists():
        status['has_recommendations'] = True
        
        try:
            with open(rec_path, 'r') as f:
                rec_data = json.load(f)
                status['recommendation_count'] = (
                    rec_data.get('summary', {}).get('reduce_recommendations_count', 0) +
                    rec_data.get('summary', {}).get('increase_recommendations_count', 0)
                )
        except:
            pass
    
    return status

