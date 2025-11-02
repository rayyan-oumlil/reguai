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
from typing import Dict, Any, Optional, List
from datetime import datetime

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
        # Add upload timestamp if not present
        if 'upload_timestamp' not in result:
            result['upload_timestamp'] = datetime.now().isoformat()
        
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


def generate_filename_from_extraction(result: Dict[str, Any], original_extension: str = '.html') -> str:
    """
    Generate a clean filename from extraction results.
    Format: Title_Country_Date.ext
    
    Args:
        result: Extraction result dictionary
        original_extension: Original file extension
        
    Returns:
        Cleaned filename
    """
    extracted_info = result.get('extracted_info', {})
    
    # Get title (clean it up)
    title = extracted_info.get('title', 'Untitled')
    if isinstance(title, str):
        # Remove common prefixes and clean
        title = title.replace('DIRECTIVE', '').replace('REGULATION', '').strip()
        title = title[:50]  # Limit length
    
    # Get country
    country = extracted_info.get('country', '')
    if isinstance(country, str):
        country = country[:20].strip()
    
    # Get date
    date = extracted_info.get('effective_date', '')
    if isinstance(date, str):
        date = date[:10].strip()  # YYYY-MM-DD format
    
    # Build filename
    parts = [p for p in [title, country, date] if p]
    filename = '_'.join(parts)
    
    # Clean filename (remove invalid characters)
    filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_')).strip()
    filename = filename.replace(' ', '_')
    
    # Add extension
    if not original_extension.startswith('.'):
        original_extension = '.' + original_extension
    
    return filename + original_extension


def delete_extraction(extraction_path: str, source: str = 'local') -> bool:
    """
    Delete an extraction result.
    
    Args:
        extraction_path: Path to the extraction file (local) or S3 key
        source: 'local' or 'S3'
        
    Returns:
        True if successful, False otherwise
    """
    try:
        if source == 'S3' and AWS_HELPER_AVAILABLE:
            helper = get_aws_helper()
            if helper.s3_bucket:
                helper.s3.delete_object(Bucket=helper.s3_bucket, Key=extraction_path)
                return True
        elif source == 'local':
            path = Path(extraction_path)
            if path.exists():
                path.unlink()
                return True
        return False
    except Exception as e:
        print(f"⚠️ Error deleting extraction: {e}")
        return False


def get_hidden_documents() -> List[str]:
    """Get list of hidden document filenames from config"""
    config_path = Path("data/generated/.hidden_documents.json")
    if config_path.exists():
        try:
            with open(config_path, 'r') as f:
                return json.load(f).get('hidden', [])
        except:
            return []
    return []


def toggle_document_visibility(filename: str, hide: bool = True):
    """Hide or show a document in the available documents list"""
    config_path = Path("data/generated/.hidden_documents.json")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    hidden_docs = get_hidden_documents()
    
    if hide and filename not in hidden_docs:
        hidden_docs.append(filename)
    elif not hide and filename in hidden_docs:
        hidden_docs.remove(filename)
    
    try:
        with open(config_path, 'w') as f:
            json.dump({'hidden': hidden_docs}, f, indent=2)
    except Exception as e:
        print(f"⚠️ Error updating hidden documents: {e}")


def save_uploaded_file(uploaded_file, destination_dir: str = 'data/raw/directives') -> Dict[str, Any]:
    """
    Save an uploaded file to the documents directory.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        destination_dir: Directory to save the file
        
    Returns:
        Dictionary with save status and file path
    """
    try:
        # Create destination directory if it doesn't exist
        dest_path = Path(destination_dir)
        dest_path.mkdir(parents=True, exist_ok=True)
        
        # Get file content
        file_content = uploaded_file.read()
        
        # Create file path
        filename = uploaded_file.name
        file_path = dest_path / filename
        
        # Handle duplicates - append number if file exists
        counter = 1
        original_file_path = file_path
        while file_path.exists():
            stem = original_file_path.stem
            suffix = original_file_path.suffix
            file_path = dest_path / f"{stem}_{counter}{suffix}"
            counter += 1
        
        # Save file
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return {
            'success': True,
            'file_path': str(file_path),
            'filename': file_path.name,
            'size': len(file_content)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_all_documents_with_status() -> List[Dict[str, Any]]:
    """
    Get all documents (raw + extracted) with their status.
    
    Returns:
        List of documents with metadata including status, upload date, etc.
    """
    documents = []
    
    # Get all raw documents
    directives_path = Path('data/raw/directives')
    if directives_path.exists():
        for doc_path in sorted(directives_path.glob('*')):
            if doc_path.suffix.lower() in ['.html', '.xml', '.pdf', '.txt'] and doc_path.name != 'README.md':
                # Check if it has been analyzed
                extraction = None
                extractions = load_existing_extractions()
                
                for ext in extractions:
                    # Match by checking if the extraction filename contains the document name
                    if doc_path.stem in ext['filename'] or ext['filename'] in doc_path.stem:
                        extraction = ext
                        break
                
                # Get upload/modification date
                upload_date = datetime.fromtimestamp(doc_path.stat().st_mtime)
                
                documents.append({
                    'filename': doc_path.name,
                    'path': str(doc_path),
                    'size': doc_path.stat().st_size,
                    'upload_date': upload_date,
                    'status': 'analyzed' if extraction else 'not_analyzed',
                    'extraction': extraction,
                    'is_hidden': doc_path.name in get_hidden_documents()
                })
    
    return documents

