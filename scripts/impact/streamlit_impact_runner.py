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


def estimate_pairs_and_time(
    selected_regulation: str | List[str],
    exposure_threshold: float,
    enable_quant_engine: bool = True
) -> Dict[str, Any]:
    """
    Estimate number of pairs and execution time before running pipeline
    
    Args:
        selected_regulation: Regulation filename(s) or "all"
        exposure_threshold: Exposure threshold
        enable_quant_engine: Whether quant engine will be enabled
        
    Returns:
        Dictionary with estimates
    """
    # Load company universe to get total companies
    try:
        company_universe_path = Path('data/generated/company_universe/company_universe.json')
        if company_universe_path.exists():
            with open(company_universe_path, 'r') as f:
                company_universe = json.load(f)
                total_companies = len(company_universe) if isinstance(company_universe, dict) else 0
        else:
            total_companies = 500  # Default S&P 500 estimate
    except:
        total_companies = 500
    
    # Estimate pairs based on threshold
    # Rough heuristic: lower threshold = more pairs
    if exposure_threshold <= 0.1:
        estimated_pairs = int(total_companies * 0.8)  # 80% match rate
    elif exposure_threshold <= 0.3:
        estimated_pairs = int(total_companies * 0.5)  # 50% match rate
    elif exposure_threshold <= 0.5:
        estimated_pairs = int(total_companies * 0.3)  # 30% match rate
    else:
        estimated_pairs = int(total_companies * 0.1)  # 10% match rate
    
    # Estimate time based on pairs and options
    # Rough estimates:
    # - Tier 1: ~0.5s per pair
    # - Tier 2: ~2s per pair (market data + quant)
    # - Tier 3: ~5s per pair (DCF + Bedrock)
    
    tier1_time = estimated_pairs * 0.5
    
    if enable_quant_engine:
        tier2_time = estimated_pairs * 2.0
        tier3_time = estimated_pairs * 5.0  # Bedrock calls
        total_seconds = tier1_time + tier2_time + tier3_time
    else:
        total_seconds = tier1_time
    
    # Convert to minutes
    total_minutes = total_seconds / 60
    
    return {
        'estimated_pairs': estimated_pairs,
        'estimated_time_seconds': total_seconds,
        'estimated_time_minutes': round(total_minutes, 1),
        'estimated_time_formatted': f"{int(total_minutes)}m {int((total_minutes % 1) * 60)}s",
        'total_companies': total_companies,
        'exposure_threshold': exposure_threshold
    }


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
    
    if not directives_path.exists():
        print(f"⚠️ Directory does not exist: {directives_path}")
        return regulations
    
    # Find all extracted JSON files
    json_files = list(directives_path.glob("*_extracted.json"))
    print(f"📁 Found {len(json_files)} JSON files in {directives_path}")
    
    for file_path in json_files:
        # Skip all_directives_extracted.json as it's a summary
        if file_path.name == "all_directives_extracted.json":
            continue
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Extract metadata - only include completed extractions
            if isinstance(data, dict):
                # Check if processing is completed
                if data.get('processing_status') != 'completed':
                    print(f"⚠️ Skipping {file_path.name}: processing_status = {data.get('processing_status')}")
                    continue
                    
                if 'document_id' in data:
                    # Single directive
                    extracted_info = data.get('extracted_info', {})
                    title = extracted_info.get('title', 'N/A')
                    
                    # If no title in extracted_info, try document_id
                    if title == 'N/A' or not title:
                        title = data.get('document_id', file_path.name)
                        # Clean up title
                        if title.endswith('.xml') or title.endswith('.html'):
                            title = title.rsplit('.', 1)[0]
                    
                    regulations.append({
                        'filename': file_path.name,
                        'title': title,
                        'country': extracted_info.get('country', 'N/A'),
                        'category': data.get('category', 'N/A'),
                        'document_id': data.get('document_id', file_path.name)
                    })
                    print(f"✅ Added: {title} ({file_path.name})")
        except Exception as e:
            print(f"⚠️ Error reading {file_path}: {e}")
            continue
    
    print(f"📋 Total regulations found: {len(regulations)}")
    return regulations


def run_impact_pipeline(
    selected_regulation: str | List[str],
    exposure_threshold: float = 0.3,
    enable_quant_engine: bool = True,
    limit_pairs: Optional[int] = None,
    high_risk_threshold: float = 60.0,
    low_risk_threshold: float = 30.0
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Run complete impact analysis pipeline
    
    Args:
        selected_regulation: Filename of selected regulation or list of filenames, or "all"
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
        # Use absolute paths for better Windows compatibility
        script_dir = Path(__file__).parent.parent
        cmd1 = [
            sys.executable,
            str(script_dir / "scripts" / "impact_orchestrator.py"),
            "--directives_dir", str(script_dir / "data" / "generated" / "extracted_directives"),
            "--company_universe", str(script_dir / "data" / "generated" / "company_universe" / "company_universe.json"),
            "--output", str(script_dir / "data" / "generated" / "impact_analysis" / "matching_pairs.json"),
            "--threshold", str(exposure_threshold)
        ]
        
        result1 = subprocess.run(
            cmd1,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',  # Replace encoding errors instead of failing
            timeout=300  # 5 minutes timeout
        )
        
        if result1.returncode != 0:
            message += f"❌ Step 1 failed: {result1.stderr[:500]}\n"
            return success, message, results
        
        message += f"✅ Step 1 complete: {result1.stdout[-200:]}\n\n"
        
        # Step 2: Run impact calculator with quant engine
        if enable_quant_engine:
            message += "📊 Running 3-tier valuation analysis...\n"
            script_dir = Path(__file__).parent.parent
            cmd2 = [
                sys.executable,
                str(script_dir / "scripts" / "impact_calculator.py"),
                "--quant-engine",
                "--threshold", str(exposure_threshold)
            ]
            
            if limit_pairs:
                cmd2.extend(["--limit-pairs", str(limit_pairs)])
            
            result2 = subprocess.run(
                cmd2,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=600  # 10 minutes timeout
            )
            
            if result2.returncode != 0:
                message += f"❌ Step 2 failed: {result2.stderr[:500]}\n"
                return success, message, results
            
            message += f"✅ Step 2 complete: {result2.stdout[-200:]}\n\n"
        
        # Step 3: Generate recommendations per directive (only if AWS available)
        # Check AWS availability first
        try:
            import boto3
            # Quick test to see if AWS credentials are available
            test_client = boto3.client('bedrock', region_name='us-east-1')
            test_client.list_foundation_models()
            aws_available = True
        except Exception:
            aws_available = False
        
        if aws_available:
            message += "🤖 Generating recommendations per directive...\n"
            script_dir = Path(__file__).parent.parent
            cmd3 = [
                sys.executable,
                str(script_dir / "scripts" / "generate_recommendations_per_directive.py")
            ]
            
            result3 = subprocess.run(
                cmd3,
                capture_output=True,
                text=True,
                encoding='utf-8',
                errors='replace',
                timeout=300  # 5 minutes timeout
            )
            
            if result3.returncode != 0:
                message += f"⚠️ Step 3 warning (recommendations per directive): {result3.stderr[:500]}\n"
            else:
                message += f"✅ Step 3 complete: Generated recommendations per directive\n\n"
        else:
            message += "⚠️ AWS credentials not available - skipping recommendations generation (visualization mode only)\n\n"
        
        # Load results
        try:
            script_dir = Path(__file__).parent.parent
            results_path = script_dir / "data" / "generated" / "impact_analysis" / "matching_pairs.json"
            with open(results_path, 'r', encoding='utf-8') as f:
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
    
    # Check matching pairs (use absolute path)
    script_dir = Path(__file__).parent.parent
    pairs_path = script_dir / 'data' / 'generated' / 'impact_analysis' / 'matching_pairs.json'
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
    
    # Check recommendations (use absolute path)
    script_dir = Path(__file__).parent.parent
    rec_path = script_dir / 'data' / 'generated' / 'recommendations' / 'recommendations.json'
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

