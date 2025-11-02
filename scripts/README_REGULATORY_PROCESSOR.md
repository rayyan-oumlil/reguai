# Regulatory Document Processor Script

A standalone Python script for processing regulatory documents using AWS Textract, LegalBERT, and Bedrock. This script can be run locally, from Jupyter notebooks, or deployed as an AWS Lambda function.

## Features

- **Multi-format Support**: Handles HTML, XML, PDF, and image files (JPEG, PNG, TIFF)
- **Text Extraction**: Uses BeautifulSoup for HTML/XML and AWS Textract for PDFs/images
- **AI Classification**: Leverages LegalBERT and Claude for regulatory category classification
- **Key Information Extraction**: Extracts structured data (title, country, dates, requirements, penalties) in English
- **S3 Integration**: Can process files directly from S3 and save results to S3
- **Lambda-Ready**: Designed to be deployed as an AWS Lambda function for automatic processing

## Usage

### 1. Command Line (Standalone)

Process a local file:
```bash
python scripts/process_regulatory_document.py \
    --file_path data/raw/directives/document.html \
    --output_dir data/generated/extracted_directives \
    --region us-east-1
```

Process an S3 file:
```bash
python scripts/process_regulatory_document.py \
    --file_path s3://my-bucket/directives/document.html \
    --output_dir s3://my-bucket/extracted/ \
    --region us-east-1
```

### 2. From Jupyter Notebook

```python
import sys
sys.path.append('../scripts')

from process_regulatory_document import RegulatoryDocumentProcessor

# Initialize processor
processor = RegulatoryDocumentProcessor(region_name='us-east-1')

# Process a document
result = processor.process_document('data/raw/directives/document.html')

# Save result
processor.save_result(result, 'data/generated/extracted_directives/document_extracted.json')
```

### 3. AWS Lambda Deployment

#### Lambda Function Setup

1. **Create Lambda Function**:
   - Runtime: Python 3.11+
   - Memory: 2048 MB (recommended for LegalBERT model)
   - Timeout: 5 minutes
   - Architecture: x86_64

2. **Package Dependencies**:
   ```bash
   # Create deployment package
   pip install -t lambda_package/ boto3 transformers torch beautifulsoup4
   cd lambda_package
   zip -r ../lambda_function.zip .
   cd ..
   zip -g lambda_function.zip scripts/process_regulatory_document.py
   ```

3. **Upload to Lambda**:
   - Upload `lambda_function.zip` to your Lambda function
   - Set handler to: `process_regulatory_document.lambda_handler`

4. **IAM Permissions**:
   Attach a policy with the following permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "bedrock:InvokeModel",
           "textract:DetectDocumentText",
           "s3:GetObject",
           "s3:PutObject"
         ],
         "Resource": "*"
       }
     ]
   }
   ```

#### Lambda Event Format

```json
{
  "file_path": "s3://source-bucket/directives/document.html",
  "output_bucket": "output-bucket",
  "output_prefix": "extracted_directives/"
}
```

#### S3 Trigger Setup

Configure S3 to automatically trigger Lambda when new files are uploaded:

1. Go to S3 bucket → Properties → Event notifications
2. Create event notification:
   - Event types: `PUT`, `POST`, `COPY`
   - Prefix: `directives/`
   - Suffix: `.html` or `.xml`
   - Destination: Your Lambda function

## Output Format

The script generates JSON files with the following structure:

```json
{
  "document_id": "document.html",
  "category": "Environmental regulation concerning waste management...",
  "legalbert_confidence": 0.87,
  "extracted_info": {
    "title": "Directive on Single-Use Plastics",
    "country": "European Union",
    "effective_date": "July 3, 2021",
    "affected_sectors": ["Manufacturing", "Retail", "Food & Beverage"],
    "key_requirements": [
      "Ban on single-use plastic items",
      "Extended producer responsibility schemes",
      "Labeling requirements for plastic products"
    ],
    "penalties": "Member states shall determine penalties, which must be effective, proportionate and dissuasive"
  },
  "processing_status": "completed"
}
```

## Environment Variables

Required AWS credentials (set via `.env` file or environment):
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_DEFAULT_REGION`

## Dependencies

```
boto3>=1.26.0
transformers>=4.30.0
torch>=2.0.0
beautifulsoup4>=4.12.0
```

For Lambda, also include:
```
python-dotenv>=1.0.0  # If loading .env files
```

## Architecture

```
┌─────────────────────┐
│   Input Document    │
│  (HTML/XML/PDF/IMG) │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Text Extraction    │
│  • BeautifulSoup    │
│  • AWS Textract     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Classification     │
│  • LegalBERT        │
│  • Claude Sonnet    │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Info Extraction     │
│  • Claude Haiku     │
│  • Structured JSON  │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   Output (JSON)     │
│  • Local File       │
│  • S3 Bucket        │
└─────────────────────┘
```

## Error Handling

The script includes comprehensive error handling:
- Failed text extraction returns empty string with error message
- Classification errors fall back to "Unknown" category
- JSON parsing errors return raw content for manual review
- Lambda errors return proper HTTP status codes

## Performance Considerations

- **LegalBERT Model**: Loads once per Lambda cold start (~2-3 seconds)
- **Text Extraction**: HTML/XML is fast; Textract may take 1-5 seconds per page
- **Claude API**: Typically responds in 1-3 seconds
- **Total Processing Time**: 5-15 seconds per document

## Cost Optimization

To minimize AWS costs:
1. Use Lambda with appropriate memory (2048 MB) to reduce execution time
2. Consider provisioned concurrency for high-volume processing
3. Use S3 Intelligent-Tiering for output storage
4. Monitor Bedrock API usage (Claude Haiku is more cost-effective than Sonnet)

## Troubleshooting

### Import Errors in Lambda
- Ensure all dependencies are included in the deployment package
- Check Python version compatibility (3.11+ recommended)

### Memory Issues
- Increase Lambda memory to 3008 MB if LegalBERT fails to load
- Consider using Lambda layers for large dependencies

### Timeout Errors
- Increase Lambda timeout to 5-10 minutes
- For very large files, consider async processing with Step Functions

### S3 Access Denied
- Verify IAM role has `s3:GetObject` and `s3:PutObject` permissions
- Check bucket policies allow Lambda access

## Future Enhancements

- [ ] Batch processing support for multiple files
- [ ] Async processing with SQS/SNS
- [ ] Caching for frequently accessed models
- [ ] Support for additional file formats (DOCX, RTF)
- [ ] Multi-language support beyond English
- [ ] Custom classification categories
- [ ] Integration with compliance databases

## License

See main project LICENSE file.
