# Impact Orchestrator

## Overview

The Impact Orchestrator analyzes regulatory documents from the generated data folder using AWS Comprehend and matches them with companies from the company universe, calculating exposure scores to determine which companies are affected by each regulatory bill or directive.

## Features

- **AWS Comprehend Integration**: Uses AWS Comprehend to analyze regulatory documents for:
  - Entity detection (organizations, locations, dates)
  - Key phrase extraction
  - Sentiment analysis
  
- **Company Matching**: Matches companies to bills based on:
  - Sector alignment
  - Geographic exposure
  - Explicit company mentions
  - Business segment overlap
  - Supply chain dependencies
  - Regulatory risk alignment

- **Exposure Score Calculation**: Calculates a 0-100 exposure score for each company-bill pair based on:
  - Sector match (0-30 points)
  - Geography match (0-25 points)
  - Explicit mention (0-20 points)
  - Segment match (0-10 points)
  - Supply chain match (0-10 points)
  - Regulatory risk match (0-5 points)

- **Threshold Filtering**: Filters companies based on exposure score threshold

- **Results Storage**: Saves comprehensive analysis results in JSON format

## Usage

### Basic Usage

```bash
python scripts/impact_orchestrator.py
```

### With Custom Parameters

```bash
python scripts/impact_orchestrator.py \
  --directives_dir data/generated/extracted_directives \
  --company_universe data/generated/company_universe/company_universe.json \
  --output data/generated/impact_analysis/impact_analysis.json \
  --threshold 0.2 \
  --region us-east-1
```

### Parameters

- `--directives_dir`: Directory containing extracted directives JSON files (default: `data/generated/extracted_directives`)
- `--company_universe`: Path to company universe JSON file (default: `data/generated/company_universe/company_universe.json`)
- `--output`: Output path for analysis results (default: `data/generated/impact_analysis/impact_analysis.json`)
- `--threshold`: Exposure score threshold between 0.0 and 1.0 (default: 0.1, i.e., 10% exposure)
- `--region`: AWS region for Comprehend (default: `us-east-1`)

## Output Format

The script generates a JSON file with the following structure:

```json
{
  "analysis_date": "2025-01-XX...",
  "total_directives": 5,
  "total_companies": 500,
  "exposure_threshold": 0.1,
  "directive_analyses": [
    {
      "document_id": "...",
      "title": "...",
      "country": "...",
      "category": "...",
      "effective_date": "...",
      "total_matches": 45,
      "filtered_matches": 23,
      "top_companies": [
        {
          "ticker": "AAPL",
          "company_name": "Apple Inc.",
          "exposure_score": 65.5,
          "exposure_factors": {
            "sector_match": 25.0,
            "geography_match": 15.0,
            "explicit_mention": 20.0,
            "segment_match": 5.0,
            "supply_chain_match": 0.0,
            "regulatory_risk_match": 0.5
          },
          "sector": "Technology",
          "industry": "Consumer Electronics",
          "has_geographic_match": true,
          "is_explicitly_mentioned": true
        }
      ],
      "comprehend_summary": {
        "entities_found": 150,
        "key_phrases_found": 89,
        "sentiment": "NEUTRAL"
      }
    }
  ]
}
```

## How It Works

1. **Load Data**: Loads all extracted directives and the company universe
2. **Text Extraction**: Extracts text content from each directive's structured data
3. **Comprehend Analysis**: Uses AWS Comprehend to analyze text for entities, key phrases, and sentiment
4. **Company Matching**: For each directive, matches companies based on multiple factors
5. **Score Calculation**: Calculates exposure scores (0-100) for each company-bill pair
6. **Filtering**: Filters results based on exposure threshold
7. **Storage**: Saves comprehensive results to JSON

## Exposure Score Breakdown

The exposure score is calculated from multiple factors:

- **Sector Match (30 points max)**: How well the company's sector/industry aligns with affected sectors
- **Geography Match (25 points max)**: Geographic overlap between company operations and regulation jurisdiction
- **Explicit Mention (20 points max)**: Direct mentions of the company name or ticker in the document
- **Segment Match (10 points max)**: Overlap between company business segments and affected sectors
- **Supply Chain Match (10 points max)**: If regulation affects company supply chain dependencies
- **Regulatory Risk Match (5 points max)**: Alignment with company's existing regulatory risk profile

## Example Use Cases

### Find Companies Affected by EU AI Act

```bash
# Analyze with 15% exposure threshold
python scripts/impact_orchestrator.py --threshold 0.15

# Results will show companies with 15%+ exposure to any directive
```

### Analyze Specific Directive

```python
from scripts.impact_orchestrator import ImpactOrchestrator

orchestrator = ImpactOrchestrator()
directives = orchestrator.load_directives('data/generated/extracted_directives')
companies = orchestrator.load_company_universe('data/generated/company_universe/company_universe.json')

# Analyze specific directive
directive = [d for d in directives if 'AI Act' in d.get('document_id', '')][0]
text = orchestrator.extract_text_from_directive(directive)
results = orchestrator.analyze_with_comprehend(text, directive['document_id'])
matches = orchestrator.match_companies_to_bill(directive, companies, results)

# Top 10 affected companies
top_10 = matches[:10]
```

## AWS Requirements

- **AWS Credentials**: Configured via environment variables, AWS CLI, or IAM role
- **IAM Permissions**: The script requires the following AWS permissions:
  - `comprehend:DetectEntities`
  - `comprehend:DetectKeyPhrases`
  - `comprehend:DetectSentiment`

## Cost Considerations

- AWS Comprehend charges per 100 characters analyzed
- The script limits analysis to first 20 chunks (100,000 characters max per document) to control costs
- Results are cached per document to avoid re-analysis

## Troubleshooting

### "No directives found"
- Check that `--directives_dir` points to the correct directory
- Ensure extracted directive files follow the naming pattern `*_extracted.json`

### "Comprehend error"
- Verify AWS credentials are configured
- Check IAM permissions for Comprehend
- Ensure region is correct

### "Insufficient text"
- Some directives may have failed extraction
- Check directive `processing_status` field

## Next Steps

After running the impact orchestrator, you can:
1. Use results for portfolio risk analysis
2. Generate recommendations for companies above threshold
3. Visualize exposure by sector or geography
4. Track changes over time as new directives are added

