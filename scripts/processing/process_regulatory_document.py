#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regulatory Document Processing Script
Can be run standalone or invoked by AWS Lambda when new regulatory files are added.

Usage:
    python process_regulatory_document.py --file_path <path_to_document> --output_dir <output_directory>
    
Lambda Event Format:
    {
        "file_path": "s3://bucket/path/to/document.html",
        "output_bucket": "output-bucket-name",
        "output_prefix": "extracted_directives/"
    }
"""

import boto3
import json
import os
import sys
import io
import argparse
from typing import Dict, Any, Optional
from pathlib import Path
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup
from transformers import AutoTokenizer, AutoModel
import torch

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class RegulatoryDocumentProcessor:
    """Process regulatory documents using AWS Textract, LegalBERT, and Bedrock"""
    
    def __init__(self, region_name='us-east-1', use_aws=True):
        """
        Initialize processor
        
        Args:
            region_name: AWS region
            use_aws: If False, skip AWS initialization (use local fallback only)
        """
        self.use_aws = use_aws
        self.aws_available = False
        
        if use_aws:
            try:
                # Try to initialize AWS clients (will fail if no credentials)
                self.bedrock = boto3.client('bedrock-runtime', region_name=region_name)
                self.textract = boto3.client('textract', region_name=region_name)
                self.s3 = boto3.client('s3', region_name=region_name)
                
                # Test if credentials work (quick test)
                try:
                    # Just test if we can list foundation models (lightweight call)
                    bedrock_client = boto3.client('bedrock', region_name=region_name)
                    bedrock_client.list_foundation_models()  # Appel sans maxResults
                    self.aws_available = True
                    print("✅ AWS credentials detected and working")
                except Exception:
                    print("⚠️ AWS credentials not available or expired, using local fallback only")
                    self.aws_available = False
            except Exception as e:
                print(f"⚠️ AWS initialization failed: {e}")
                print("   Using local fallback mode (no AWS required)")
                self.aws_available = False
                # Create dummy clients to avoid errors (won't be used)
                self.bedrock = None
                self.textract = None
                self.s3 = None
        else:
            print("🔧 Local mode: AWS disabled, using fallback methods only")
            self.aws_available = False
            self.bedrock = None
            self.textract = None
            self.s3 = None
        
        # Bedrock model configuration (align with notebook behavior)
        # Primary model: Claude Sonnet 4.5 (can require an inference profile depending on account setup)
        self.model_id_primary = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-sonnet-4-5-20250929-v1:0')
        # Optional inference profile ARN for models that require one
        self.inference_profile_arn = os.getenv('BEDROCK_INFERENCE_PROFILE_ARN')
        # Safe fallback widely available on-demand
        self.model_id_fallback = 'us.anthropic.claude-3-5-sonnet-20241022-v2:0'
        
        # Load LegalBERT for legal document classification
        print("📚 Loading LegalBERT model for legal analysis...")
        self.legal_tokenizer = AutoTokenizer.from_pretrained("nlpaueb/legal-bert-base-uncased")
        self.legal_model = AutoModel.from_pretrained("nlpaueb/legal-bert-base-uncased")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.legal_model.to(self.device)
        print("✅ LegalBERT model loaded successfully")

    def _invoke_bedrock(self, prompt: str, max_tokens: int = 1000):
        """Invoke Bedrock with fallback handling for inference-profile-only models."""
        # If AWS not available, immediately raise to trigger fallback
        if not self.aws_available or not self.bedrock:
            raise Exception("AWS Bedrock not available - using fallback")
        
        payload = {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': max_tokens,
            'messages': [{'role': 'user', 'content': prompt}]
        }
        # First try the primary model id
        try:
            return self.bedrock.invoke_model(modelId=self.model_id_primary, body=json.dumps(payload))
        except Exception as e:
            msg = str(e).lower()
            # If credentials expired or unavailable, raise immediately
            if ('expiredtoken' in msg) or ('expired token' in msg) or ('unauthorized' in msg):
                raise Exception("AWS token expired or credentials invalid - using fallback")
            
            # If model requires inference profile, try with ARN or fallback
            if ('validationexception' in msg) and ('inference profile' in msg):
                if self.inference_profile_arn:
                    try:
                        return self.bedrock.invoke_model(modelId=self.inference_profile_arn, body=json.dumps(payload))
                    except Exception:
                        # If profile fails and primary wasn't fallback, try fallback
                        if self.model_id_primary != self.model_id_fallback:
                            return self.bedrock.invoke_model(modelId=self.model_id_fallback, body=json.dumps(payload))
                        raise
                # No profile set: try fallback if not already primary
                if self.model_id_primary != self.model_id_fallback:
                    return self.bedrock.invoke_model(modelId=self.model_id_fallback, body=json.dumps(payload))
            # Propagate other errors
            raise
        
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from any local or S3 file using Textract or BeautifulSoup"""
        # Extracting text from file
        
        # Check if it's an S3 path
        if file_path.startswith('s3://'):
            return self._extract_from_s3(file_path)
        else:
            return self._extract_from_local(file_path)
    
    def _extract_from_local(self, file_path: str) -> str:
        """Extract text from local file"""
        _, ext = os.path.splitext(file_path.lower())
            # File extension detected
        
        if ext in ['.html', '.xml']:
            # Using BeautifulSoup for HTML/XML parsing
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    soup = BeautifulSoup(file, 'html.parser')
                    text = soup.get_text(separator='\n')
                return text
            except Exception as e:
                pass  # Error parsing HTML/XML
                return ""
        
        elif ext in ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif']:
            if not self.aws_available or not self.textract:
                    # AWS Textract not available - using PDF parsing fallback
                # Try basic PDF parsing if available
                try:
                    import PyPDF2  # type: ignore
                    with open(file_path, 'rb') as file:
                        pdf_reader = PyPDF2.PdfReader(file)
                        text = ""
                        for page in pdf_reader.pages[:10]:  # Limit to first 10 pages
                            text += page.extract_text() + "\n"
                    if text:
                        return text
                    else:
                        return f"[PDF file: {os.path.basename(file_path)} - text extraction not available without AWS]"
                except ImportError:
                    return f"[PDF file: {os.path.basename(file_path)} - install PyPDF2 or use AWS for extraction]"
                except Exception as e:
                    pass  # PDF parsing error
                    return f"[PDF file: {os.path.basename(file_path)} - extraction failed]"
            
            # Using Textract for document extraction
            try:
                with open(file_path, 'rb') as file:
                    document_bytes = file.read()
                
                response = self.textract.detect_document_text(
                    Document={'Bytes': document_bytes}
                )
                
                text = ""
                for block in response['Blocks']:
                    if block['BlockType'] == 'LINE':
                        text += block['Text'] + "\n"
                
                return text
            except ClientError as e:
                if e.response['Error']['Code'] == 'UnsupportedDocumentException':
                    pass  # Unsupported document format
                    return ""
                else:
                    raise
        else:
            # Unsupported file format
            return ""
    
    def _extract_from_s3(self, s3_path: str) -> str:
        """Extract text from S3 file"""
        # Parse S3 path
        s3_path = s3_path.replace('s3://', '')
        bucket, key = s3_path.split('/', 1)
        
        _, ext = os.path.splitext(key.lower())
        # S3 file extension detected
        
        if ext in ['.html', '.xml']:
            # Using BeautifulSoup for HTML/XML parsing
            try:
                if self.s3 is None:
                    pass  # S3 client not available
                    return ""
                response = self.s3.get_object(Bucket=bucket, Key=key)
                content = response['Body'].read().decode('utf-8')
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text(separator='\n')
                pass  # Extracted text from S3
                return text
            except Exception as e:
                pass  # Error parsing HTML/XML from S3
                return ""
        
        elif ext in ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif']:
            # Using Textract for document extraction from S3
            try:
                if self.textract is None:
                    pass  # Textract client not available
                    return ""
                response = self.textract.detect_document_text(
                    Document={'S3Object': {'Bucket': bucket, 'Name': key}}
                )
                
                text = ""
                for block in response['Blocks']:
                    if block['BlockType'] == 'LINE':
                        text += block['Text'] + "\n"
                
                pass  # Extracted text from S3 using Textract
                return text
            except ClientError as e:
                pass  # Textract error
                return ""
        else:
            # Unsupported file format
            return ""
    
    def _classify_with_keywords(self, text: str) -> str:
        """Fallback classification using keyword matching"""
        text_lower = text.lower()
        
        keywords = {
            'Environmental': ['environment', 'climate', 'carbon', 'emission', 'green', 'renewable', 'energy', 'pollution', 'sustainability'],
            'Tax': ['tax', 'revenue', 'irs', 'fiscal', 'taxation', 'deduction', 'credit', 'rate'],
            'Financial': ['bank', 'financial', 'securities', 'capital', 'market', 'investment', 'credit', 'lending'],
            'Trade': ['trade', 'import', 'export', 'tariff', 'customs', 'commerce', 'consumer', 'protection'],
            'Privacy': ['privacy', 'data protection', 'gdpr', 'personal data', 'consent', 'anonymization'],
            'Labor': ['labor', 'employment', 'wage', 'workplace', 'union', 'worker', 'employee']
        }
        
        scores = {}
        for category, kw_list in keywords.items():
            scores[category] = sum(1 for kw in kw_list if kw in text_lower)
        
        max_score = max(scores.values())
        if max_score > 0:
            # Get the category with the highest score
            best_category = max(scores.keys(), key=lambda k: scores[k])
            return best_category
        return 'Unknown'
    
    def classify_regulation_with_legalbert(self, text: str) -> Dict[str, Any]:
        """Classify regulation using LegalBERT for legal document understanding"""
        # Classifying document using LegalBERT
        
        # Use first 10000 chars for classification (better context than just 2000)
        truncated_text = text[:10000]
        
        legalbert_confidence = 0.0
        try:
            # Tokenize input for LegalBERT (limited to 512 tokens)
            inputs = self.legal_tokenizer(
                truncated_text[:2000],  # LegalBERT still needs small input
                return_tensors="pt",
                truncation=True,
                max_length=512,
                padding=True
            ).to(self.device)
            
            # Get embeddings from LegalBERT
            with torch.no_grad():
                outputs = self.legal_model(**inputs)
                embeddings = outputs.last_hidden_state.mean(dim=1)
            
            # Use embedding norm as confidence measure
            legalbert_confidence = min(torch.norm(embeddings).item() / 10, 1.0)
            pass  # LegalBERT classification completed
        except Exception as e:
            pass  # LegalBERT processing error - continuing
        
        # Try AWS classification, but fallback to keywords if it fails
        try:
            # Use Claude Sonnet for contextual classification (more text for better accuracy)
            prompt = f"""Based on this regulatory document excerpt, classify it into ONE category:
            - Environmental
            - Financial
            - Trade
            - Privacy
            - Labor
            - Tax
            
            Document excerpt: {truncated_text}
            
            Return only the category name and a brief 1-2 sentence explanation."""
            
            response = self._invoke_bedrock(prompt, max_tokens=200)
            
            result = json.loads(response['body'].read())
            classification = result['content'][0]['text'].strip()
            # Document classification completed
            
            return {
                'category': classification,
                'legalbert_confidence': legalbert_confidence
            }
        
        except Exception as e:
            msg = str(e).lower()
            if ('expiredtoken' in msg) or ('expired token' in msg):
                category = self._classify_with_keywords(text)
                return {'category': category, 'legalbert_confidence': legalbert_confidence, 'fallback': True}
            if ('validationexception' in msg) and ('inference profile' in msg):
                category = self._classify_with_keywords(text)
                return {'category': category, 'legalbert_confidence': legalbert_confidence, 'fallback': True}
            category = self._classify_with_keywords(text)
            return {'category': category, 'legalbert_confidence': legalbert_confidence, 'fallback': True}
    
    def _extract_basic_info_fallback(self, text: str, category: str) -> Dict[str, Any]:
        """Fallback extraction using regex and basic parsing when AWS is unavailable"""
        # Using fallback extraction (no AWS required)
        
        import re
        from dateutil.parser import parse as parse_date
        
        result = {
            'title': 'Unknown regulation',
            'country': None,
            'effective_date': None,
            'affected_sectors': [],
            'affected_entities': [],
            'key_requirements': [],
            'penalties': [],
            'raw_content': text[:5000]  # Store first 5000 chars
        }
        
        # Try to extract title from common patterns
        title_patterns = [
            r'(?:DIRECTIVE|REGULATION|ACT|LAW|BILL)\s+(?:\([^)]+\)\s+)?([^\n]{20,150})',
            r'Title:\s*([^\n]{20,150})',
            r'<title>([^<]{20,150})</title>',
            r'#\s+([^\n]{20,150})'
        ]
        for pattern in title_patterns:
            match = re.search(pattern, text[:2000], re.IGNORECASE)
            if match:
                result['title'] = match.group(1).strip()[:200]
                break
        
        # Try to extract country/jurisdiction
        country_patterns = [
            r'(?:European Union|EU|United States|USA|US|China|Japan|Canada|United Kingdom|UK)',
            r'<country>([^<]+)</country>',
            r'Jurisdiction:\s*([^\n]+)'
        ]
        for pattern in country_patterns:
            match = re.search(pattern, text[:5000], re.IGNORECASE)
            if match:
                result['country'] = match.group(1).strip() if match.groups() else match.group(0).strip()
                break
        
        # Try to extract dates
        date_patterns = [
            r'(?:effective|effective date|date of effect|enacted|enforcement):\s*(\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{4})',
            r'(\d{4}[-/]\d{2}[-/]\d{2})',
            r'(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}'
        ]
        for pattern in date_patterns:
            matches = re.finditer(pattern, text[:10000], re.IGNORECASE)
            for match in list(matches)[:3]:  # Take first 3 matches
                try:
                    date_str = match.group(1) if match.groups() else match.group(0)
                    parsed = parse_date(date_str, fuzzy=True)
                    result['effective_date'] = parsed.strftime('%Y-%m-%d')
                    break
                except:
                    continue
            if result['effective_date']:
                break
        
        # Extract basic requirements using keywords
        req_keywords = ['requirement', 'must', 'shall', 'required', 'obligation', 'mandatory']
        sentences = re.split(r'[.!?]+\s+', text[:20000])
        requirements = []
        for sent in sentences:
            if any(kw in sent.lower() for kw in req_keywords) and len(sent) > 30:
                requirements.append(sent.strip()[:200])
                if len(requirements) >= 10:
                    break
        result['key_requirements'] = requirements[:10]
        
        # Extract penalties
        penalty_patterns = [
            r'(?:penalty|fine|sanction).*?(?:€|\$|USD|EUR)?\s*([\d,]+(?:\.[\d]+)?)',
            r'([\d,]+(?:\.[\d]+)?)\s*(?:€|\$|USD|EUR|million|billion).*?(?:penalty|fine)'
        ]
        penalties = []
        for pattern in penalty_patterns:
            matches = re.finditer(pattern, text[:20000], re.IGNORECASE)
            for match in list(matches)[:5]:
                penalties.append({
                    'type': 'Financial',
                    'amount': match.group(1).replace(',', ''),
                    'currency': 'USD',
                    'article_reference': 'Extracted via fallback'
                })
        if penalties:
            result['penalties'] = penalties[:5]
        
        result['extraction_method'] = 'fallback_regex'
        # Fallback extraction completed
        return result
    
    def extract_key_info(self, text: str, category: str) -> Dict[str, Any]:
        """Extract key regulatory information using Claude with automatic chunking for large documents"""
        # Extracting key information
        
        # Claude Sonnet 4.5 supports up to ~3.5M chars
        MAX_CHARS_SONNET = 3500000
        text_length = len(text)
        
        # Truncate to Claude's limit if needed
        if text_length > MAX_CHARS_SONNET:
            text = text[:MAX_CHARS_SONNET]
            # Document very long - truncated

        prompt_template = """You are a financial regulatory intelligence analyst. Extract an exhaustive and precise structured summary from this {category} regulation for downstream financial compliance analytics.

                Return STRICT JSON (UTF-8, no markdown) in English with the following schema. Omit a field only if the regulation provides no signal at all (use null instead of guessing):
                {{
                    "title": string,
                    "country": string,
                    "effective_date": string,
                    "regulatory_body": string or null,
                    "scope": string or null,
                    "affected_sectors": [string],
                    "affected_entities": [string],
                    "key_requirements": [string],
                    "key_requirement_details": [
                        {{
                            "requirement": string,
                            "article_reference": string,
                            "metrics": [
                                {{
                                    "type": string,
                                    "value": number,
                                    "unit": string,
                                    "description": string
                                }}
                            ],
                            "deadline": string or null,
                            "compliance_action": string or null
                        }}
                    ],
                    "reporting_requirements": [
                        {{
                            "description": string,
                            "frequency": string or null,
                            "format": string or null,
                            "article_reference": string
                        }}
                    ],
                    "monetary_thresholds": [
                        {{
                            "amount": number,
                            "currency": string,
                            "description": string,
                            "article_reference": string
                        }}
                    ],
                    "quantitative_limits": [
                        {{
                            "value": number,
                            "unit": string,
                            "description": string,
                            "article_reference": string
                        }}
                    ],
                    "penalties": [
                        {{
                            "type": string,
                            "amount": number or null,
                            "currency": string or null,
                            "imprisonment": string or null,
                            "article_reference": string
                        }}
                    ],
                    "enforcement_agencies": [string],
                    "implementation_timeline": {{
                        "publication_date": string or null,
                        "transposition_deadline": string or null,
                        "phased_milestones": [string]
                    }},
                    "notes": [string],
                    "source_articles": [string]
                }}

                Document excerpt: {document_text}

                Extraction guidelines:
                - Capture EVERY actionable obligation, threshold, reporting duty, or quantitative limit explicitly. Do not collapse multiple items into one summary.
                - Provide explicit article/paragraph references for every obligation, metric, or penalty whenever stated.
                - Preserve all numeric values exactly; convert spelled-out numbers to digits and include currency ISO codes (e.g., "EUR") or units (%, tonnes, MW).
                - Represent percentages as decimals (e.g., 12.5% → 0.125) and monetary amounts as numbers (no thousands separators).
                - Translate narrative text to English while keeping proper nouns in their original form.
                - If a field is unknown, use null instead of fabricating content.
    - Keep JSON valid and exhaustive—no markdown, comments, or trailing commas."""
        
        def merge_regulatory_info(info1: Dict, info2: Dict) -> Dict:
            """Merge two regulatory information dictionaries"""
            merged = info1.copy() if info1 else {}
            
            if not info2:
                return merged
            
            # Title: take the longer one
            if info2.get('title') and (not merged.get('title') or len(info2['title']) > len(merged.get('title', ''))):
                merged['title'] = info2['title']
            
            # Country: take first non-empty
            if info2.get('country') and not merged.get('country'):
                merged['country'] = info2['country']
            
            # Effective date: take first non-empty
            if info2.get('effective_date') and not merged.get('effective_date'):
                merged['effective_date'] = info2['effective_date']
            
            # Affected sectors: merge lists
            sectors1 = merged.get('affected_sectors', [])
            if isinstance(sectors1, str):
                sectors1 = [sectors1] if sectors1 else []
            sectors2 = info2.get('affected_sectors', [])
            if isinstance(sectors2, str):
                sectors2 = [sectors2] if sectors2 else []
            merged['affected_sectors'] = list(set(sectors1 + sectors2))
            
            # Key requirements: merge lists
            reqs1 = merged.get('key_requirements', [])
            if isinstance(reqs1, str):
                reqs1 = [reqs1] if reqs1 else []
            reqs2 = info2.get('key_requirements', [])
            if isinstance(reqs2, str):
                reqs2 = [reqs2] if reqs2 else []
            merged['key_requirements'] = list(set(reqs1 + reqs2))
            
            # Penalties: take the longer one
            if info2.get('penalties') and (not merged.get('penalties') or len(str(info2['penalties'])) > len(str(merged.get('penalties', '')))):
                merged['penalties'] = info2['penalties']
            
            return merged
        
        def extract_recursive(text_chunk: str, depth: int = 0, max_depth: int = 10) -> Optional[Dict]:
            """Recursively extract information, splitting if document is too long"""
            if depth > max_depth:
                pass  # Max depth reached
                return None
            
            chunk_length = len(text_chunk)
            
            # Stop splitting if chunk is too small (< 100 chars) - likely an API error, not length issue
            if chunk_length < 100:
                pass  # Chunk too small - stopping recursion
                return None
            
            prompt = prompt_template.format(category=category, document_text=text_chunk)
            
            try:
                response = self._invoke_bedrock(prompt, max_tokens=1500)
                
                result = json.loads(response['body'].read())
                content = result['content'][0]['text']
                
                try:
                    extracted_info = json.loads(content)
                    return extracted_info
                except json.JSONDecodeError:
                    pass  # Invalid JSON - returning raw content
                    return {'raw_content': content}
                    
            except Exception as e:
                error_msg = str(e).lower()
                
                # On auth errors, use fallback instead of failing
                if ("expiredtoken" in error_msg) or ("expired token" in error_msg):
                    return self._extract_basic_info_fallback(text_chunk, category)
                
                # Handle inference-profile validation error with fallback
                if ("validationexception" in error_msg) and ("inference profile" in error_msg):
                    pass  # AWS model requires inference profile - using fallback
                    return self._extract_basic_info_fallback(text_chunk, category)
                
                # ONLY split if it's specifically about the prompt/input being too long
                # Check for explicit length-related error messages
                is_length_error = (
                    "prompt is too long" in error_msg or
                    "too many tokens" in error_msg or
                    "maximum context length" in error_msg or
                    "input is too long" in error_msg or
                    ("too long" in error_msg and "prompt" in error_msg)
                )
                
                if is_length_error and chunk_length > 1000:
                    # Document is too long for the model, split it
                    pass  # Input too long - splitting
                    
                    mid_point = len(text_chunk) // 2
                    split_point = text_chunk.rfind('\n', mid_point - 10000, mid_point + 10000)
                    if split_point == -1:
                        split_point = mid_point
                    
                    chunk1 = text_chunk[:split_point]
                    chunk2 = text_chunk[split_point:]
                    
                    info1 = extract_recursive(chunk1, depth + 1, max_depth)
                    info2 = extract_recursive(chunk2, depth + 1, max_depth)
                    
                    if info1 and info2:
                        return merge_regulatory_info(info1, info2)
                    return info1 or info2
                    
                elif "throttling" in error_msg or "throttled" in error_msg:
                    import time
                    wait = min(30, (depth + 1) * 5)
                    pass  # Throttling - waiting
                    time.sleep(wait)
                    return extract_recursive(text_chunk, depth, max_depth)
                    
                else:
                    # Any other error - don't try to split, just report it
                    pass  # Error during extraction
                    return None
        
        # Start recursive extraction
        extracted_info = extract_recursive(text)
        
        if extracted_info is not None:
            # Check if fallback was used
            if isinstance(extracted_info, dict) and extracted_info.get('extraction_method') == 'fallback_regex':
                pass  # Key information extracted using fallback method
            elif isinstance(extracted_info, dict) and extracted_info.get('error') in ['ExpiredTokenException', 'ValidationException:InferenceProfileRequired']:
                # This shouldn't happen now (fallback catches it), but handle just in case
                extracted_info = self._extract_basic_info_fallback(text, category)
            pass  # Key information extracted successfully
            return extracted_info
        else:
            pass  # Extraction failed - using fallback method
            return self._extract_basic_info_fallback(text, category)
    
    def process_document(self, file_path: str) -> Dict[str, Any]:
        """Process any document format"""
        print(f"🚀 Starting document processing pipeline...")
        
        # Extract document name/ID
        if file_path.startswith('s3://'):
            document_id = file_path.split('/')[-1]
        else:
            document_id = os.path.basename(file_path)
        
        text = self.extract_text_from_file(file_path)
        
        if not text:
            print("❌ Failed to extract text from document")
            return {
                'document_id': document_id,
                'processing_status': 'failed',
                'error': 'Failed to extract text'
            }
        
        classification = self.classify_regulation_with_legalbert(text)
        key_info = self.extract_key_info(text, classification.get('category', 'Unknown'))
        
        # Determine status - always mark as completed if we have any extraction (even fallback)
        processing_status = 'completed'
        used_fallback = False
        
        # Check if fallback was used
        if isinstance(key_info, dict):
            if key_info.get('extraction_method') == 'fallback_regex':
                used_fallback = True
                processing_status = 'completed'  # Fallback is still a successful extraction
            elif classification.get('fallback'):
                used_fallback = True
        
        print("🎉 Processing completed successfully!" + (" (using fallback - no AWS required)" if used_fallback else ""))
        
        result = {
            'document_id': document_id,
            'category': classification.get('category', 'Unknown'),
            'legalbert_confidence': classification.get('legalbert_confidence', 0.0),
            'extracted_info': key_info,
            'processing_status': processing_status,
            'used_fallback': used_fallback
        }
        
        if used_fallback:
            result['fallback_reason'] = 'AWS unavailable (expired token or no access)'
        
        return result
    
    def save_result(self, result: Dict[str, Any], output_path: str):
        """Save result to local file or S3"""
        if output_path.startswith('s3://'):
            # Save to S3
            if self.s3 is None:
                pass  # S3 client not available
                return result
            
            s3_path = output_path.replace('s3://', '')
            bucket, key = s3_path.split('/', 1)
            
            self.s3.put_object(
                Bucket=bucket,
                Key=key,
                Body=json.dumps(result, indent=2, ensure_ascii=False),
                ContentType='application/json'
            )
            print(f"✅ Saved to S3: {output_path}")
        else:
            # Save to local file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            print(f"✅ Saved to local file: {output_path}")


def lambda_handler(event, context):
    """
    AWS Lambda handler function
    
    Event format:
    {
        "file_path": "s3://bucket/path/to/document.html",
        "output_bucket": "output-bucket-name",
        "output_prefix": "extracted_directives/"
    }
    """
    try:
        file_path = event.get('file_path')
        output_bucket = event.get('output_bucket')
        output_prefix = event.get('output_prefix', 'extracted_directives/')
        
        if not file_path:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'file_path is required'})
            }
        
        # Initialize processor
        processor = RegulatoryDocumentProcessor()
        
        # Process document
        result = processor.process_document(file_path)
        
        # Generate output path
        document_name = file_path.split('/')[-1]
        file_stem = os.path.splitext(document_name)[0]
        output_path = f"s3://{output_bucket}/{output_prefix}{file_stem}_extracted.json"
        
        # Save result
        processor.save_result(result, output_path)
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Document processed successfully',
                'document_id': result['document_id'],
                'category': result['category'],
                'status': result['processing_status'],
                'output_path': output_path
            })
        }
    
    except Exception as e:
        pass  # Lambda error
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e)
            })
        }


def main():
    """Command-line interface for standalone execution"""
    parser = argparse.ArgumentParser(description='Process regulatory documents')
    parser.add_argument('--file_path', required=True, help='Path to document (local or s3://)')
    parser.add_argument('--output_dir', default='./output', help='Output directory for results')
    parser.add_argument('--region', default='us-east-1', help='AWS region')
    
    args = parser.parse_args()
    
    # Initialize processor
    processor = RegulatoryDocumentProcessor(region_name=args.region)
    
    # Process document
    result = processor.process_document(args.file_path)
    
    # Generate output path
    document_name = args.file_path.split('/')[-1]
    file_stem = os.path.splitext(document_name)[0]
    output_path = os.path.join(args.output_dir, f"{file_stem}_extracted.json")
    
    # Save result
    processor.save_result(result, output_path)
    
    # Processing complete


if __name__ == '__main__':
    main()
