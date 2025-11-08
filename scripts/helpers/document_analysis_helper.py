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

from scripts.processing.process_regulatory_document import RegulatoryDocumentProcessor  # type: ignore

# Try to import AWS helper for enhanced AWS services
try:
    from scripts.helpers.aws_services_helper import extract_with_aws_services, get_aws_helper  # type: ignore
    AWS_HELPER_AVAILABLE = True
except ImportError:
    AWS_HELPER_AVAILABLE = False
    # Définir des fonctions stub pour éviter les erreurs "unbound"
    def get_aws_helper() -> Any:  # type: ignore
        raise ImportError("AWS helper not available")
    def extract_with_aws_services(*args: Any, **kwargs: Any) -> Dict[str, Any]:  # type: ignore
        raise ImportError("AWS helper not available")
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
            pass  # Erreur cache silencieuse
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
        pass  # Erreur sauvegarde cache silencieuse


def extract_from_uploaded_file(uploaded_file: Any, use_cache: bool = True, 
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
        # Try to use AWS if available, but fallback to local mode automatically
        # Check if AWS credentials are available
        try:
            import boto3
            # Quick test - if this fails, AWS not available
            bedrock_client = boto3.client('bedrock', region_name='us-east-1')
            bedrock_client.list_foundation_models()  # Appel sans maxResults
            use_aws = True
        except Exception:
            use_aws = False
            print("ℹ️ AWS not available, using local fallback mode")
        
        processor = RegulatoryDocumentProcessor(use_aws=use_aws)
        result = processor.process_document(tmp_path)
        result['from_cache'] = False
        result['cache_source'] = 'local'
        result['filename'] = filename
        result['aws_used'] = use_aws
        
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
                           use_aws_services: bool = True, force_new_analysis: bool = False) -> Dict[str, Any]:
    """
    Extract regulatory information from a local file path.
    Uses AWS services (S3, Comprehend) if available and enabled.
    
    Args:
        file_path: Path to the document file
        use_cache: Whether to use cache if available (only if not force_new_analysis)
        use_aws_services: Whether to use AWS services (S3, Comprehend) if available
        force_new_analysis: If True, always re-analyze even if extraction exists (for raw files)
        
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
                    use_s3_cache=use_cache and not force_new_analysis
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
    
    # Si force_new_analysis=True, on ne vérifie PAS le cache (pour les fichiers bruts)
    if use_cache and not force_new_analysis:
        cached_result = check_cache(cache_key, filename)
        if cached_result:
            return {**cached_result, 'from_cache': True, 'cache_source': 'local'}
    
    try:
        # Try to use AWS if available, but fallback to local mode automatically
        try:
            import boto3
            # Quick test - if this fails, AWS not available
            bedrock_client = boto3.client('bedrock', region_name='us-east-1')
            bedrock_client.list_foundation_models()  # Appel sans maxResults
            use_aws = True
        except Exception:
            use_aws = False
            print("ℹ️ AWS not available, using local fallback mode")
        
        processor = RegulatoryDocumentProcessor(use_aws=use_aws)
        result = processor.process_document(file_path)
        result['from_cache'] = False
        result['cache_source'] = 'local'
        result['filename'] = filename
        result['aws_used'] = use_aws
        
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
            pass  # Erreur S3 silencieuse
    
    # Fallback to local cache
    if CACHE_DIR.exists():
        # First, load individual extraction files
        for json_file in CACHE_DIR.glob("*_extracted.json"):
            if json_file.name == 'all_directives_extracted.json':
                continue
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Include all extractions - if processing_status missing, assume completed
                    if data.get('processing_status') is None:
                        data['processing_status'] = 'completed'
                    # Only include if status is completed
                    if data.get('processing_status') == 'completed':
                        extractions.append({
                            'filename': json_file.stem.replace('_extracted', ''),
                            'path': str(json_file),
                            'data': data,
                            'source': 'local'
                        })
            except Exception as e:
                pass  # Erreur chargement fichier silencieuse
        
        # Also load from all_directives_extracted.json if individual files are missing
        consolidated_file = CACHE_DIR / 'all_directives_extracted.json'
        if consolidated_file.exists() and len(extractions) == 0:
            try:
                with open(consolidated_file, 'r', encoding='utf-8') as f:
                    all_data = json.load(f)
                for doc_id, data in all_data.items():
                    if isinstance(data, dict) and data.get('processing_status') != 'failed':
                        if data.get('processing_status') is None:
                            data['processing_status'] = 'completed'
                        if data.get('processing_status') == 'completed':
                            extractions.append({
                                'filename': doc_id,
                                'path': str(consolidated_file),
                                'data': data,
                                'source': 'local_consolidated'
                            })
            except Exception as e:
                pass  # Erreur chargement fichier silencieuse
    
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
        pass  # Erreur suppression silencieuse
        return False




def save_uploaded_file(uploaded_file, destination_dir: str = 'data/raw/directives', use_aws: bool = True) -> Dict[str, Any]:
    """
    Save an uploaded file to the documents directory.
    Optionally also uploads to AWS S3 if available.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        destination_dir: Directory to save the file locally
        use_aws: Whether to also upload to S3 if AWS is available
        
    Returns:
        Dictionary with save status and file path
    """
    try:
        # Reset file pointer to beginning in case it was read before
        uploaded_file.seek(0)
        
        # Get file content
        file_content = uploaded_file.read()
        
        # Reset file pointer again after reading
        uploaded_file.seek(0)
        
        # Create file path
        filename = uploaded_file.name
        
        # Try to upload to S3 first if AWS is available
        s3_path = None
        if use_aws and AWS_HELPER_AVAILABLE:
            try:
                helper = get_aws_helper()
                if helper.s3_bucket:
                    s3_path = helper.upload_to_s3_raw(file_content, filename)
                    if s3_path:
                        print(f"✅ Uploaded to S3: {s3_path}")
            except Exception as e:
                print(f"⚠️ S3 upload failed, saving locally only: {e}")
        
        # Save locally
        dest_path = Path(destination_dir)
        dest_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dest_path / filename
        
        # Handle duplicates - append number if file exists
        counter = 1
        original_file_path = file_path
        while file_path.exists():
            stem = original_file_path.stem
            suffix = original_file_path.suffix
            file_path = dest_path / f"{stem}_{counter}{suffix}"
            counter += 1
        
        # Save file locally
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        result = {
            'success': True,
            'file_path': str(file_path),
            'filename': file_path.name,
            'size': len(file_content)
        }
        
        # Add S3 path if uploaded
        if s3_path:
            result['s3_path'] = s3_path
            result['stored_in'] = 'local_and_s3'
        else:
            result['stored_in'] = 'local_only'
        
        return result
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def get_all_documents_with_status() -> List[Dict[str, Any]]:
    """
    Get all documents (raw + extracted) with their status.
    Loads from both data/raw/directives (raw files) and data/generated/extracted_directives (extracted JSON)
    
    Returns:
        List of documents with metadata including status, upload date, etc.
    """
    documents = []
    seen_document_ids = set()  # Track document_ids to avoid duplicates
    raw_files_with_extraction = set()  # Track raw files that have extractions
    
    # Load all extractions to map by document_id
    extractions = load_existing_extractions()
    extraction_by_doc_id = {}
    for ext in extractions:
        data = ext.get('data', {})
        doc_id = data.get('document_id', '')
        if doc_id:
            extraction_by_doc_id[doc_id] = ext
            # Also map by filename for easier matching
            ext_filename = ext.get('filename', '')
            if ext_filename and ext_filename not in extraction_by_doc_id:
                extraction_by_doc_id[ext_filename] = ext
    
    directives_path = Path('data/raw/directives')
    
    # FIRST: Process all extracted documents (analyzed documents take priority)
    # This ensures analyzed documents are shown, not raw files
    extracted_dir = Path('data/generated/extracted_directives')
    if extracted_dir.exists():
        for ext_file in sorted(extracted_dir.glob('*_extracted.json')):
            if ext_file.name == 'all_directives_extracted.json':
                continue
            
            try:
                with open(ext_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Check if processing is completed (if field exists)
                if 'processing_status' in data and data.get('processing_status') != 'completed':
                    continue
                
                doc_id = data.get('document_id', '')
                if not doc_id:
                    continue
                
                # Check if impact analysis exists (for 3-Tier status)
                impact_analysis_exists = False
                impact_dir = Path('data/generated/impact_analysis')
                if impact_dir.exists():
                    for impact_file in impact_dir.glob("*_impact.json"):
                        try:
                            with open(impact_file, 'r', encoding='utf-8') as f:
                                impact_data = json.load(f)
                            impact_doc_id = impact_data.get('document_id', '')
                            if impact_doc_id == doc_id:
                                impact_analysis_exists = True
                                break
                        except Exception:
                            continue
                
                # Find corresponding extraction
                extraction = extraction_by_doc_id.get(doc_id)
                if not extraction:
                    extraction = {
                        'filename': ext_file.stem.replace('_extracted', ''),
                        'path': str(ext_file),
                        'data': data,
                        'source': 'local'
                    }
                
                # Get extracted info
                extracted_info = data.get('extracted_info', {})
                title = extracted_info.get('title', doc_id)
                
                # Determine status
                if impact_analysis_exists:
                    status = 'analyzed_3tier'
                else:
                    status = 'analyzed'
                
                # Get file info (use extraction file date, or try to find raw file date)
                upload_date = datetime.fromtimestamp(ext_file.stat().st_mtime)
                if directives_path.exists():
                    # Try to find matching raw file to get its date
                    for raw_file in directives_path.glob('*'):
                        if raw_file.name == doc_id:
                            upload_date = datetime.fromtimestamp(raw_file.stat().st_mtime)
                            raw_files_with_extraction.add(raw_file.name)  # Mark as having extraction
                            break
                
                doc_entry = {
                    'filename': doc_id,  # Use document_id as filename for display
                    'path': str(ext_file),
                    'size': ext_file.stat().st_size,
                    'upload_date': upload_date,
                    'status': status,
                    'extraction': extraction,
                    'has_impact_analysis': impact_analysis_exists,
                    'document_id': doc_id,
                    'title': title,
                    'is_raw_file': False  # This is an extracted document
                }
                
                documents.append(doc_entry)
                seen_document_ids.add(doc_id)
                seen_document_ids.add(ext_file.stem.replace('_extracted', ''))
                
            except Exception as e:
                pass  # Erreur chargement fichier silencieuse
                continue
    
    # SECOND: Only add raw files that DON'T have an extraction
    # This prevents showing raw files when analyzed version exists
    if directives_path.exists():
        for doc_path in sorted(directives_path.glob('*')):
            if doc_path.suffix.lower() in ['.html', '.xml', '.pdf', '.txt'] and doc_path.name != 'README.md':
                raw_filename = doc_path.name
                
                # Skip if this raw file already has an extraction (already added above)
                if raw_filename in raw_files_with_extraction or raw_filename in seen_document_ids:
                    continue
                
                # Check if extraction exists by looking up in extraction_by_doc_id
                has_extraction = raw_filename in extraction_by_doc_id
                if has_extraction:
                    # This raw file has an extraction, skip it (already added above)
                    raw_files_with_extraction.add(raw_filename)
                    continue
                
                # This raw file has NO extraction, add it as "not_analyzed"
                upload_date = datetime.fromtimestamp(doc_path.stat().st_mtime)
                
                doc_entry = {
                    'filename': raw_filename,
                    'path': str(doc_path),
                    'size': doc_path.stat().st_size,
                    'upload_date': upload_date,
                    'status': 'not_analyzed',
                    'extraction': None,
                    'has_impact_analysis': False,
                    'document_id': raw_filename,
                    'is_raw_file': True  # Mark as raw file for display
                }
                
                documents.append(doc_entry)
                seen_document_ids.add(raw_filename)
                seen_document_ids.add(doc_path.stem)
    
    return documents

