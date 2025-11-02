#!/usr/bin/env python3
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
import argparse
from typing import Dict, Any
from pathlib import Path
from botocore.exceptions import ClientError
from bs4 import BeautifulSoup
from transformers import AutoTokenizer, AutoModel
import torch


class RegulatoryDocumentProcessor:
    """Process regulatory documents using AWS Textract, LegalBERT, and Bedrock"""
    
    def __init__(self, region_name='us-east-1'):
        self.bedrock = boto3.client('bedrock-runtime', region_name=region_name)
        self.textract = boto3.client('textract', region_name=region_name)
        self.s3 = boto3.client('s3', region_name=region_name)
        
        # Load LegalBERT for legal document classification
        print("📚 Loading LegalBERT model for legal analysis...")
        self.legal_tokenizer = AutoTokenizer.from_pretrained("nlpaueb/legal-bert-base-uncased")
        self.legal_model = AutoModel.from_pretrained("nlpaueb/legal-bert-base-uncased")
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.legal_model.to(self.device)
        print("✅ LegalBERT model loaded successfully")
        
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from any local or S3 file using Textract or BeautifulSoup"""
        print(f"📄 Extracting text from: {file_path}")
        
        # Check if it's an S3 path
        if file_path.startswith('s3://'):
            return self._extract_from_s3(file_path)
        else:
            return self._extract_from_local(file_path)
    
    def _extract_from_local(self, file_path: str) -> str:
        """Extract text from local file"""
        _, ext = os.path.splitext(file_path.lower())
        print(f"   File extension detected: {ext}")
        
        if ext in ['.html', '.xml']:
            print("   Using BeautifulSoup for HTML/XML parsing...")
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    soup = BeautifulSoup(file, 'html.parser')
                    text = soup.get_text(separator='\n')
                print(f"✅ Extracted {len(text):,} characters using BeautifulSoup")
                return text
            except Exception as e:
                print(f"❌ Error parsing HTML/XML: {e}")
                return ""
        
        elif ext in ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif']:
            print("   Using Textract for document extraction...")
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
                
                print(f"✅ Extracted {len(text):,} characters using Textract")
                return text
            except ClientError as e:
                if e.response['Error']['Code'] == 'UnsupportedDocumentException':
                    print("❌ Unsupported document format. Textract supports JPEG, PNG, PDF, and TIFF files.")
                    return ""
                else:
                    raise
        else:
            print(f"❌ Unsupported file format: {ext}. Supported: PDF, images (JPEG/PNG/TIFF), HTML, XML.")
            return ""
    
    def _extract_from_s3(self, s3_path: str) -> str:
        """Extract text from S3 file"""
        # Parse S3 path
        s3_path = s3_path.replace('s3://', '')
        bucket, key = s3_path.split('/', 1)
        
        _, ext = os.path.splitext(key.lower())
        print(f"   S3 file extension detected: {ext}")
        
        if ext in ['.html', '.xml']:
            print("   Using BeautifulSoup for HTML/XML parsing...")
            try:
                response = self.s3.get_object(Bucket=bucket, Key=key)
                content = response['Body'].read().decode('utf-8')
                soup = BeautifulSoup(content, 'html.parser')
                text = soup.get_text(separator='\n')
                print(f"✅ Extracted {len(text):,} characters using BeautifulSoup")
                return text
            except Exception as e:
                print(f"❌ Error parsing HTML/XML from S3: {e}")
                return ""
        
        elif ext in ['.pdf', '.jpg', '.jpeg', '.png', '.tiff', '.tif']:
            print("   Using Textract for document extraction from S3...")
            try:
                response = self.textract.detect_document_text(
                    Document={'S3Object': {'Bucket': bucket, 'Name': key}}
                )
                
                text = ""
                for block in response['Blocks']:
                    if block['BlockType'] == 'LINE':
                        text += block['Text'] + "\n"
                
                print(f"✅ Extracted {len(text):,} characters using Textract")
                return text
            except ClientError as e:
                print(f"❌ Textract error: {e}")
                return ""
        else:
            print(f"❌ Unsupported file format: {ext}")
            return ""
    
    def classify_regulation_with_legalbert(self, text: str) -> Dict[str, Any]:
        """Classify regulation using LegalBERT for legal document understanding"""
        print("🔍 Classifying document using LegalBERT...")
        
        # Truncate text to avoid token limit (512 tokens max for BERT)
        truncated_text = text[:2000]
        
        try:
            # Tokenize input
            inputs = self.legal_tokenizer(
                truncated_text,
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
            confidence = min(torch.norm(embeddings).item() / 10, 1.0)
            print(f"📋 LegalBERT confidence score: {confidence:.2%}")
            
            # Use Claude for contextual classification
            prompt = f"""Based on this regulatory document excerpt, classify it into ONE category:
            - Environmental
            - Financial
            - Trade
            - Privacy
            - Labor
            - Tax
            
            Document excerpt: {truncated_text}
            
            Return only the category name and a brief 1-2 sentence explanation."""
            
            response = self.bedrock.invoke_model(
                modelId='anthropic.claude-sonnet-4-5-20250929-v1:0',
                body=json.dumps({
                    'anthropic_version': 'bedrock-2023-05-31',
                    'max_tokens': 100,
                    'messages': [{'role': 'user', 'content': prompt}]
                })
            )
            
            result = json.loads(response['body'].read())
            classification = result['content'][0]['text'].strip()
            print(f"📋 Document classification: {classification}")
            
            return {
                'category': classification,
                'legalbert_confidence': confidence
            }
        
        except Exception as e:
            print(f"⚠️ Classification error: {e}. Falling back to basic extraction.")
            return {'category': 'Unknown', 'legalbert_confidence': 0.0}
    
    def extract_key_info(self, text: str, category: str) -> Dict[str, Any]:
        """Extract key regulatory information using Claude"""
        print(f"🔎 Extracting key information for {category} regulation...")
        prompt = f"""Extract key information from this {category} regulation. Return all information in English.
        
        Required fields:
        - title: Document title (translate to English if needed)
        - country: Country or region where this regulation applies (e.g., "United States", "European Union", "Japan", etc.)
        - effective_date: When it takes effect
        - affected_sectors: Which business sectors are impacted
        - key_requirements: Main compliance requirements (max 3)
        - penalties: Potential penalties for non-compliance
        
        Document: {text[:4000]}
        
        Return ONLY valid JSON (no markdown, no code blocks, just pure JSON). Ensure all text fields are in English."""
        
        response = self.bedrock.invoke_model(
            modelId='anthropic.claude-3-haiku-20240307-v1:0',
            body=json.dumps({
                'anthropic_version': 'bedrock-2023-05-31',
                'max_tokens': 500,
                'messages': [{'role': 'user', 'content': prompt}]
            })
        )
        
        result = json.loads(response['body'].read())
        content = result['content'][0]['text'].strip()
        print("✅ Key information extracted")
        
        try:
            # Remove markdown code blocks if present
            if content.startswith('```'):
                content = content.split('```')[1]
                if content.startswith('json'):
                    content = content[4:]
                content = content.strip()
            
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"⚠️ Failed to parse JSON: {e}")
            return {'raw_content': content}
    
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
        key_info = self.extract_key_info(text, classification['category'])
        print("🎉 Processing completed successfully!")
        
        return {
            'document_id': document_id,
            'category': classification['category'],
            'legalbert_confidence': classification.get('legalbert_confidence', 0.0),
            'extracted_info': key_info,
            'processing_status': 'completed'
        }
    
    def save_result(self, result: Dict[str, Any], output_path: str):
        """Save result to local file or S3"""
        if output_path.startswith('s3://'):
            # Save to S3
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
        print(f"❌ Lambda error: {str(e)}")
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
    
    print("\n" + "="*80)
    print("📊 PROCESSING COMPLETE")
    print("="*80)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
