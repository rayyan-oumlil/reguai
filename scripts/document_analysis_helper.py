"""
Helper functions for document analysis page ("Analyse de Documents") in Streamlit app.
Handles cache management and integration with RegulatoryDocumentProcessor.
Supports both local cache and AWS S3 cache with Comprehend pre-filtering.

Ce module est spécifiquement utilisé par la page "📄 Analyse de Documents".
"""

import json
import hashlib
import tempfile
import os
from pathlib import Path
from typing import Dict, Any, Optional

# Try to import UploadedFile
try:
    from streamlit.runtime.uploaded_file_manager import UploadedFile
except ImportError:
    UploadedFile = type(None)

# Import the processor class
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from scripts.process_regulatory_document import RegulatoryDocumentProcessor

# Try to import AWS helper for enhanced AWS services
try:
    from scripts.aws_services_helper import extract_with_aws_services, get_aws_helper
    AWS_HELPER_AVAILABLE = True
except ImportError:
    AWS_HELPER_AVAILABLE = False
    print("⚠️ AWS helper not available, using local cache only")


# Cache directory for extracted documents (fallback)
CACHE_DIR = Path("data/generated/extracted_directives")
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def get_cache_key(file_content: bytes, filename: str) -> str:
    """Generate a cache key from file content"""
    hash_obj = hashlib.md5(file_content)
    hash_obj.update(filename.encode())
    return hash_obj.hexdigest()


def get_cache_path(cache_key: str, filename: str) -> Path:
    """Get the cache file path for a document"""
    safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).rstrip()
    cache_filename = f"{cache_key[:8]}_{safe_filename}_extracted.json"
    return CACHE_DIR / cache_filename


def check_cache(cache_key: str, filename: str) -> Optional[Dict[str, Any]]:
    """Check if extraction result exists in local cache"""
    cache_path = get_cache_path(cache_key, filename)
    if cache_path.exists():
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached_data = json.load(f)
            return cached_data
        except Exception as e:
            print(f"⚠️ Error reading cache: {e}")
    return None


def save_to_cache(cache_key: str, filename: str, result: Dict[str, Any]):
    """Save extraction result to local cache"""
    cache_path = get_cache_path(cache_key, filename)
    try:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error saving to cache: {e}")


def extract_from_uploaded_file(uploaded_file: UploadedFile, use_cache: bool = True, 
                               use_aws_services: bool = True) -> Dict[str, Any]:
    """
    Extract regulatory information from a Streamlit uploaded file.
    Uses AWS services (S3, Comprehend) if available and enabled.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        use_cache: Whether to use cache if available
        use_aws_services: Whether to use AWS services (S3, Comprehend) if available
        
    Returns:
        Dictionary with extraction results
    """
    # Try AWS services first if available and enabled
    if use_aws_services and AWS_HELPER_AVAILABLE:
        try:
            helper = get_aws_helper()
            # Only use AWS if S3 bucket is configured
            if helper.s3_bucket:
                return extract_with_aws_services(
                    uploaded_file,
                    use_comprehend_prefilter=True,
                    use_s3_cache=use_cache
                )
        except Exception as e:
            print(f"⚠️ AWS services failed, falling back to local: {e}")
    
    # Fallback to local processing
    file_content = uploaded_file.read()
    filename = uploaded_file.name
    file_extension = Path(filename).suffix.lower()
    
    cache_key = get_cache_key(file_content, filename)
    
    if use_cache:
        cached_result = check_cache(cache_key, filename)
        if cached_result:
            return {**cached_result, 'from_cache': True, 'cache_source': 'local'}
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(file_content)
        tmp_path = tmp_file.name
    
    try:
        processor = RegulatoryDocumentProcessor()
        result = processor.process_document(tmp_path)
        result['from_cache'] = False
        result['cache_source'] = 'local'
        result['filename'] = filename
        
        if use_cache:
            save_to_cache(cache_key, filename, result)
        
        return result
        
    except Exception as e:
        return {
            'document_id': filename,
            'processing_status': 'failed',
            'error': str(e),
            'from_cache': False
        }
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def extract_from_local_file(file_path: str, use_cache: bool = True, 
                           use_aws_services: bool = True) -> Dict[str, Any]:
    """
    Extract regulatory information from a local file path.
    Uses AWS services (S3, Comprehend) if available and enabled.
    
    Args:
        file_path: Path to the document file
        use_cache: Whether to use cache if available
        use_aws_services: Whether to use AWS services (S3, Comprehend) if available
        
    Returns:
        Dictionary with extraction results
    """
    # Try AWS services first if available and enabled
    if use_aws_services and AWS_HELPER_AVAILABLE:
        try:
            helper = get_aws_helper()
            if helper.s3_bucket:
                return extract_with_aws_services(
                    file_path,
                    use_comprehend_prefilter=True,
                    use_s3_cache=use_cache
                )
        except Exception as e:
            print(f"⚠️ AWS services failed, falling back to local: {e}")
    
    # Fallback to local processing
    filename = os.path.basename(file_path)
    
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()
    except Exception as e:
        return {
            'document_id': filename,
            'processing_status': 'failed',
            'error': f"Cannot read file: {str(e)}",
            'from_cache': False
        }
    
    cache_key = get_cache_key(file_content, filename)
    
    if use_cache:
        cached_result = check_cache(cache_key, filename)
        if cached_result:
            return {**cached_result, 'from_cache': True, 'cache_source': 'local'}
    
    try:
        processor = RegulatoryDocumentProcessor()
        result = processor.process_document(file_path)
        result['from_cache'] = False
        result['cache_source'] = 'local'
        result['filename'] = filename
        
        if use_cache:
            save_to_cache(cache_key, filename, result)
        
        return result
        
    except Exception as e:
        return {
            'document_id': filename,
            'processing_status': 'failed',
            'error': str(e),
            'from_cache': False
        }


def load_existing_extractions() -> list:
    """Load all existing extraction results from cache directory or S3"""
    extractions = []
    
    # Try to load from S3 if available
    if AWS_HELPER_AVAILABLE:
        try:
            helper = get_aws_helper()
            if helper.s3_bucket:
                s3_extractions = helper.list_s3_extractions()
                for ext in s3_extractions:
                    extractions.append({
                        'filename': ext['filename'],
                        'path': ext['s3_key'],
                        'data': ext['data'],
                        'source': 'S3'
                    })
                return extractions
        except Exception as e:
            print(f"⚠️ Error loading from S3: {e}")
    
    # Fallback to local cache
    if CACHE_DIR.exists():
        for json_file in CACHE_DIR.glob("*_extracted.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    extractions.append({
                        'filename': json_file.stem.replace('_extracted', ''),
                        'path': str(json_file),
                        'data': data,
                        'source': 'local'
                    })
            except Exception as e:
                print(f"⚠️ Error loading {json_file}: {e}")
    
    return extractions

