"""
Helper functions for AWS services integration in Streamlit app.
Uses S3, Comprehend, DynamoDB, and Bedrock for optimal processing.
"""

import json
import hashlib
import tempfile
import os
import boto3
from pathlib import Path
from typing import Dict, Any, Optional, List
from botocore.exceptions import ClientError
import streamlit as st

# Try to import UploadedFile
try:
    from streamlit.runtime.uploaded_file_manager import UploadedFile
except ImportError:
    UploadedFile = type(None)


class AWSServicesHelper:
    """Helper class for AWS services integration"""
    
    def __init__(self, region_name='us-east-1', s3_bucket: Optional[str] = None):
        """
        Initialize AWS services clients
        
        Args:
            region_name: AWS region
            s3_bucket: S3 bucket name for cache storage (if None, uses local cache)
        """
        self.region_name = region_name
        self.s3_bucket = s3_bucket
        
        # Initialize AWS clients
        self.s3 = boto3.client('s3', region_name=region_name)
        self.comprehend = boto3.client('comprehend', region_name=region_name)
        self.bedrock = boto3.client('bedrock-runtime', region_name=region_name)
        
        # Try to initialize DynamoDB (optional)
        try:
            self.dynamodb = boto3.resource('dynamodb', region_name=region_name)
            self.dynamodb_available = True
        except Exception:
            self.dynamodb_available = False
            print("⚠️ DynamoDB not available, using S3-only metadata storage")
        
        # S3 prefix for cache
        self.s3_cache_prefix = "processed/extractions/"
        self.s3_raw_prefix = "raw/regulations/"
        
    def get_cache_key(self, file_content: bytes, filename: str) -> str:
        """Generate a cache key from file content"""
        hash_obj = hashlib.md5(file_content)
        hash_obj.update(filename.encode())
        return hash_obj.hexdigest()
    
    def check_s3_cache(self, cache_key: str, filename: str) -> Optional[Dict[str, Any]]:
        """Check if extraction result exists in S3 cache"""
        if not self.s3_bucket:
            return None
            
        cache_key_s3 = f"{self.s3_cache_prefix}{cache_key}_{filename.replace(' ', '_')}.json"
        
        try:
            response = self.s3.get_object(Bucket=self.s3_bucket, Key=cache_key_s3)
            cached_data = json.loads(response['Body'].read())
            return cached_data
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                return None
            else:
                print(f"⚠️ Error reading S3 cache: {e}")
                return None
    
    def save_to_s3_cache(self, cache_key: str, filename: str, result: Dict[str, Any]):
        """Save extraction result to S3 cache"""
        if not self.s3_bucket:
            return
            
        cache_key_s3 = f"{self.s3_cache_prefix}{cache_key}_{filename.replace(' ', '_')}.json"
        
        try:
            self.s3.put_object(
                Bucket=self.s3_bucket,
                Key=cache_key_s3,
                Body=json.dumps(result, indent=2, ensure_ascii=False),
                ContentType='application/json'
            )
        except Exception as e:
            print(f"⚠️ Error saving to S3 cache: {e}")
    
    def upload_to_s3_raw(self, file_content: bytes, filename: str) -> Optional[str]:
        """Upload document to S3 raw storage"""
        if not self.s3_bucket:
            return None
            
        s3_key = f"{self.s3_raw_prefix}{filename}"
        
        try:
            self.s3.put_object(
                Bucket=self.s3_bucket,
                Key=s3_key,
                Body=file_content,
                ContentType='application/octet-stream'
            )
            return f"s3://{self.s3_bucket}/{s3_key}"
        except Exception as e:
            print(f"⚠️ Error uploading to S3: {e}")
            return None
    
    def prefilter_with_comprehend(self, text: str, max_length: int = 50000) -> str:
        """
        Use Comprehend to pre-filter text and extract relevant sections.
        This reduces the tokens sent to Bedrock (cost optimization).
        
        Args:
            text: Full document text
            max_length: Maximum length for Comprehend API (5000 chars per request)
            
        Returns:
            Filtered text with relevant sections
        """
        if len(text) <= max_length:
            # Text is short enough, use full text
            return text
        
        print(f"🔍 Pre-filtering {len(text):,} chars with Comprehend...")
        
        # Split text into chunks for Comprehend (5000 char limit)
        chunk_size = 5000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        all_entities = []
        all_sentiments = []
        
        for i, chunk in enumerate(chunks[:10]):  # Limit to first 10 chunks for cost control
            try:
                # Detect entities
                entities_response = self.comprehend.detect_entities(
                    Text=chunk,
                    LanguageCode='en'
                )
                
                # Detect sentiment
                sentiment_response = self.comprehend.detect_sentiment(
                    Text=chunk[:5000],  # Comprehend limit
                    LanguageCode='en'
                )
                
                # Filter relevant entities
                relevant_entities = [
                    e for e in entities_response['Entities']
                    if e['Type'] in ['ORGANIZATION', 'LOCATION', 'DATE', 'EVENT']
                    and e['Score'] > 0.7  # High confidence
                ]
                
                all_entities.extend(relevant_entities)
                
                # Keep track of sentiment
                if sentiment_response['Sentiment'] in ['NEGATIVE', 'MIXED']:
                    all_sentiments.append(i)
                    
            except Exception as e:
                print(f"⚠️ Comprehend error on chunk {i}: {e}")
                continue
        
        # Identify chunks with relevant entities
        relevant_chunk_indices = set()
        for entity in all_entities:
            # Find which chunk contains this entity
            for idx, chunk in enumerate(chunks):
                if entity['Text'] in chunk:
                    relevant_chunk_indices.add(idx)
                    break
        
        # Also include chunks around relevant ones (context)
        expanded_indices = set(relevant_chunk_indices)
        for idx in relevant_chunk_indices:
            if idx > 0:
                expanded_indices.add(idx - 1)
            if idx < len(chunks) - 1:
                expanded_indices.add(idx + 1)
        
        # Combine relevant chunks
        if expanded_indices:
            filtered_text = '\n\n'.join([chunks[i] for i in sorted(expanded_indices)])
            reduction = (1 - len(filtered_text) / len(text)) * 100
            print(f"✅ Comprehend filtered: {len(text):,} → {len(filtered_text):,} chars ({reduction:.1f}% reduction)")
            return filtered_text
        else:
            # No relevant entities found, return first chunks (document might be relevant anyway)
            print("⚠️ No highly relevant entities found, using first 30% of document")
            return text[:int(len(text) * 0.3)]
    
    def extract_with_bedrock_haiku(self, text: str, prompt_template: str) -> Dict[str, Any]:
        """
        Use Claude Haiku (cheaper) for simple extractions
        
        Args:
            text: Text to extract from
            prompt_template: Prompt template with {document_text} placeholder
            
        Returns:
            Extracted information as dict
        """
        prompt = prompt_template.format(document_text=text[:200000])  # Haiku limit
        
        try:
            response = self.bedrock.invoke_model(
                modelId='us.anthropic.claude-3-haiku-20240307-v1:0',
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 4000,
                    'messages': [{'role': 'user', 'content': prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            content = result['content'][0]['text']
            
            # Try to parse as JSON
            try:
                if content.startswith('```'):
                    content = content.split('```')[1]
                    if content.startswith('json'):
                        content = content[4:].strip()
                return json.loads(content)
            except json.JSONDecodeError:
                return {'raw_content': content}
                
        except Exception as e:
            print(f"❌ Bedrock Haiku error: {e}")
            raise
    
    def extract_with_bedrock_sonnet(self, text: str, prompt_template: str) -> Dict[str, Any]:
        """
        Use Claude Sonnet (better quality) for complex extractions
        
        Args:
            text: Text to extract from
            prompt_template: Prompt template with {document_text} placeholder
            
        Returns:
            Extracted information as dict
        """
        prompt = prompt_template.format(document_text=text)
        
        try:
            response = self.bedrock.invoke_model(
                modelId='us.anthropic.claude-3-5-sonnet-20241022-v2:0',
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 4000,
                    'messages': [{'role': 'user', 'content': prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            content = result['content'][0]['text']
            
            # Try to parse as JSON
            try:
                if content.startswith('```'):
                    content = content.split('```')[1]
                    if content.startswith('json'):
                        content = content[4:].strip()
                return json.loads(content)
            except json.JSONDecodeError:
                return {'raw_content': content}
                
        except Exception as e:
            print(f"❌ Bedrock Sonnet error: {e}")
            raise
    
    def save_metadata_to_dynamodb(self, document_id: str, metadata: Dict[str, Any]):
        """Save extraction metadata to DynamoDB (optional)"""
        if not self.dynamodb_available or not self.s3_bucket:
            return
        
        table_name = 'reguai-extractions-metadata'
        
        try:
            table = self.dynamodb.Table(table_name)
            table.put_item(Item={
                'document_id': document_id,
                'status': metadata.get('processing_status', 'unknown'),
                'category': metadata.get('category', 'unknown'),
                'processed_date': metadata.get('processed_date', ''),
                's3_key': metadata.get('s3_key', ''),
                'metadata': metadata
            })
        except Exception as e:
            # Table might not exist, that's okay
            print(f"⚠️ DynamoDB save failed (table might not exist): {e}")
    
    def list_s3_extractions(self) -> List[Dict[str, Any]]:
        """List all extractions from S3"""
        if not self.s3_bucket:
            return []
        
        extractions = []
        
        try:
            response = self.s3.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix=self.s3_cache_prefix
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('.json'):
                        try:
                            file_obj = self.s3.get_object(
                                Bucket=self.s3_bucket,
                                Key=obj['Key']
                            )
                            data = json.loads(file_obj['Body'].read())
                            extractions.append({
                                'filename': obj['Key'].split('/')[-1],
                                's3_key': obj['Key'],
                                'data': data,
                                'last_modified': obj['LastModified'].isoformat()
                            })
                        except Exception as e:
                            print(f"⚠️ Error loading {obj['Key']}: {e}")
        except Exception as e:
            print(f"⚠️ Error listing S3: {e}")
        
        return extractions


# Global instance (can be configured via environment variables)
_aws_helper = None


def get_aws_helper() -> AWSServicesHelper:
    """Get or create AWS helper instance"""
    global _aws_helper
    
    if _aws_helper is None:
        # Try to get S3 bucket from environment or config
        s3_bucket = os.environ.get('S3_BUCKET_NAME') or os.environ.get('AWS_S3_BUCKET')
        region = os.environ.get('AWS_REGION', 'us-east-1')
        
        # Try to detect from SageMaker Studio Project if available
        if not s3_bucket:
            try:
                from sagemaker_studio import Project
                project = Project()
                s3_root = project.s3.root  # Ex: s3://bucket-name/path/
                if s3_root and s3_root.startswith('s3://'):
                    # Extract bucket name from s3://bucket/path format
                    bucket_from_project = s3_root.replace('s3://', '').split('/')[0]
                    if bucket_from_project:
                        s3_bucket = bucket_from_project
                        print(f"✅ Bucket S3 détecté depuis SageMaker Project: {s3_bucket}")
                        # Also try to detect region from project if available
                        try:
                            region = project.region if hasattr(project, 'region') else region
                        except:
                            pass
            except ImportError:
                pass  # SageMaker Studio not available
            except Exception as e:
                print(f"⚠️ Could not detect S3 from SageMaker Project: {e}")
        
        # If no bucket configured, use None (will fallback to local cache)
        _aws_helper = AWSServicesHelper(
            region_name=region,
            s3_bucket=s3_bucket
        )
        
        if s3_bucket:
            print(f"✅ AWS Helper configuré avec bucket: {s3_bucket} (région: {region})")
        else:
            print("ℹ️ AWS Helper configuré sans S3 bucket (utilisera cache local)")
    
    return _aws_helper


def extract_with_aws_services(uploaded_file_or_path, use_comprehend_prefilter: bool = True, 
                              use_s3_cache: bool = True) -> Dict[str, Any]:
    """
    Extract regulatory information using AWS services (S3, Comprehend, Bedrock)
    
    Args:
        uploaded_file_or_path: Either UploadedFile or file path string
        use_comprehend_prefilter: Whether to use Comprehend for pre-filtering
        use_s3_cache: Whether to use S3 for cache
        
    Returns:
        Dictionary with extraction results
    """
    helper = get_aws_helper()
    
    # Read file content
    if isinstance(uploaded_file_or_path, str):
        # Local file path
        with open(uploaded_file_or_path, 'rb') as f:
            file_content = f.read()
        filename = os.path.basename(uploaded_file_or_path)
    else:
        # UploadedFile
        file_content = uploaded_file_or_path.read()
        filename = uploaded_file_or_path.name
    
    # Generate cache key
    cache_key = helper.get_cache_key(file_content, filename)
    
    # Check S3 cache first
    if use_s3_cache:
        cached_result = helper.check_s3_cache(cache_key, filename)
        if cached_result:
            return {**cached_result, 'from_cache': True, 'cache_source': 'S3'}
    
    # Upload to S3 raw storage (optional, for audit trail)
    s3_path = None
    if helper.s3_bucket:
        s3_path = helper.upload_to_s3_raw(file_content, filename)
    
    # Extract text (simplified - assumes HTML/XML/text, not PDF)
    try:
        from bs4 import BeautifulSoup
        if filename.endswith(('.html', '.xml')):
            text = BeautifulSoup(file_content.decode('utf-8'), 'html.parser').get_text(separator='\n')
        else:
            text = file_content.decode('utf-8')
    except:
        text = file_content.decode('utf-8', errors='ignore')
    
    # Pre-filter with Comprehend if enabled
    if use_comprehend_prefilter and len(text) > 10000:
        text = helper.prefilter_with_comprehend(text)
    
    # Extract with Bedrock (using processor from existing code)
    # For now, we'll use the existing processor but could enhance it
    import sys
    import os
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    
    from scripts.process_regulatory_document import RegulatoryDocumentProcessor
    
    # Create temp file for processor
    file_extension = Path(filename).suffix.lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as tmp_file:
        tmp_file.write(file_content)
        tmp_path = tmp_file.name
    
    try:
        processor = RegulatoryDocumentProcessor()
        result = processor.process_document(tmp_path)
        
        # Add AWS metadata
        result['from_cache'] = False
        result['cache_source'] = 'S3' if use_s3_cache else 'local'
        result['s3_path'] = s3_path
        result['filename'] = filename
        result['used_comprehend'] = use_comprehend_prefilter and len(text) > 10000
        
        # Save to S3 cache
        if use_s3_cache:
            helper.save_to_s3_cache(cache_key, filename, result)
        
        # Save metadata to DynamoDB
        helper.save_metadata_to_dynamodb(filename, result)
        
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

