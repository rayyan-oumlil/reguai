# 🤖 Recommendation Generator - Bedrock Integration

Generates actionable trading recommendations from regulatory impact analysis using AWS Bedrock Claude Sonnet.

## 📋 Overview

The Recommendation Generator analyzes 3-tier valuation results to produce:
- **REDUCE** recommendations for high-risk companies (risk score >= threshold)
- **INCREASE** recommendations for low-risk companies (risk score <= threshold)
- **AI-generated justifications** for each recommendation using Bedrock

## 🏗️ Architecture

### Input: Impact Analysis Results
```
data/generated/impact_analysis/matching_pairs.json
├── regulations/
│   ├── regulation_id/
│   │   ├── companies/
│   │   │   ├── final_risk_score
│   │   │   ├── valuation_impact (Tier 1, 2, 3)
│   │   │   └── quantitative_analysis
```

### Output: Recommendations JSON
```
data/generated/recommendations/recommendations.json
├── generated_at
├── total_companies_analyzed
├── summary
├── recommendations/
│   ├── reduce[] - High risk companies
│   └── increase[] - Low risk companies
└── risk_thresholds
```

## 🚀 Usage

### Basic Usage
```bash
python scripts/recommendation_generator.py
```

### With Custom Thresholds
```bash
python scripts/recommendation_generator.py \
    --high-risk-threshold 60.0 \
    --low-risk-threshold 30.0
```

### Custom Input/Output
```bash
python scripts/recommendation_generator.py \
    --impact_results data/custom_impact.json \
    --output data/custom_recommendations.json \
    --region us-east-1
```

## 📊 Recommendation Structure

### Each Recommendation Contains:

```json
{
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "recommendation": "REDUCE" | "INCREASE",
  "current_risk_score": 45.5,
  "risk_category": "Moderate",
  "metrics": {
    "exposure_score": 50.0,
    "fcf_impact_per_share": -0.1234,
    "fcf_impact_percentage": -5.50,
    "price_impact_percentage": -12.34,
    "discount_rate_change_bps": 100
  },
  "regulatory_context": {
    "regulation": "EU AI Act",
    "region": "European Union"
  },
  "justification": "AI-generated 2-3 paragraph explanation..."
}
```

## 🤖 Bedrock Integration

### Model Configuration
- **Primary**: Claude Sonnet 4.5 (`anthropic.claude-sonnet-4-5-20250929-v1:0`)
- **Fallback**: Claude 3.5 Sonnet (`us.anthropic.claude-3-5-sonnet-20241022-v2:0`)
- **Max Tokens**: 1000 for justifications

### Prompt Engineering
The generator builds comprehensive prompts including:
- Company financial metrics
- Risk scores (Tier 1, 2, 3)
- Regulatory context
- Valuation impacts
- Matching reasons

### Fallback Behavior
If Bedrock fails (credentials, errors), the generator uses:
- Basic template-based justifications
- Still includes all quantitative metrics
- Saves partial results

## 🎯 Risk Thresholds

### Default Thresholds
- **High Risk**: >= 60.0 (REDUCE)
- **Low Risk**: <= 30.0 (INCREASE)

### Customization
Adjust thresholds based on:
- Portfolio risk tolerance
- Market conditions
- Regulatory environment

```bash
--high-risk-threshold 70.0  # More conservative
--low-risk-threshold 20.0   # Stricter criteria
```

## 📈 Example Output

### Summary Statistics
```
================================================================================
📊 RECOMMENDATIONS SUMMARY
================================================================================
Total companies analyzed: 40
🔴 REDUCE recommendations: 32
🟢 INCREASE recommendations: 1
================================================================================
```

### Recommendation Types

#### REDUCE Example
```json
{
  "ticker": "TSLA",
  "company_name": "Tesla, Inc.",
  "recommendation": "REDUCE",
  "current_risk_score": 65.2,
  "risk_category": "Moderate",
  "metrics": {
    "price_impact_percentage": -28.5
  },
  "justification": "Tesla exhibits elevated regulatory exposure with a risk score of 65.2/100. The estimated 28.5% price impact reflects material headwinds from environmental regulations affecting the energy sector..."
}
```

#### INCREASE Example
```json
{
  "ticker": "MSFT",
  "company_name": "Microsoft Corporation",
  "recommendation": "INCREASE",
  "current_risk_score": 15.3,
  "risk_category": "Low",
  "metrics": {
    "price_impact_percentage": -2.1
  },
  "justification": "Microsoft presents a relatively attractive opportunity with minimal regulatory exposure. The risk score of 15.3/100 and estimated 2.1% price impact suggest manageable regulatory headwinds..."
}
```

## 🔄 Integration with Impact Calculator

### Workflow
```bash
# Step 1: Run impact analysis
python scripts/impact_calculator.py --quant-engine --threshold 0.3

# Step 2: Generate recommendations
python scripts/recommendation_generator.py --high-risk-threshold 40

# Step 3: Load in Streamlit (future)
# streamlit run app.py
```

### Data Flow
```
Impact Calculator (Tier 1, 2, 3)
    ↓
matching_pairs.json
    ↓
Recommendation Generator (Bedrock)
    ↓
recommendations.json
    ↓
Streamlit Dashboard
```

## 🛠️ Technical Details

### Classes

#### `RecommendationGenerator`
Main orchestrator for recommendation generation.

**Key Methods**:
- `generate_recommendations()` - Main entry point
- `_generate_company_recommendation()` - Per-company Bedrock calls
- `_build_recommendation_prompt()` - Prompt engineering
- `_invoke_bedrock()` - Bedrock API wrapper with fallback

### Bedrock API Pattern
```python
payload = {
    'anthropic_version': 'bedrock-2023-05-31',
    'max_tokens': max_tokens,
    'messages': [{'role': 'user', 'content': prompt}]
}

response = bedrock.invoke_model(
    modelId=model_id,
    body=json.dumps(payload)
)
```

### Error Handling
1. **Credentials Missing**: Use fallback justifications
2. **Model Unavailable**: Try fallback model
3. **Invalid Input**: Skip company, continue processing
4. **API Throttling**: (Future: retry with backoff)

## 🔮 Future Enhancements

### Phase 1: Enhanced Bedrock Prompts
- Industry-specific templates
- ESG considerations
- Competitive positioning

### Phase 2: Batch Processing
- Parallel Bedrock calls
- Rate limiting
- Progress tracking

### Phase 3: Recommendation Confidence
- LLM confidence scores
- Historical accuracy tracking
- Multi-model consensus

## 📚 Dependencies

```python
boto3>=1.28.0          # AWS Bedrock
json                   # Data serialization
datetime               # Timestamps
pathlib                # File handling
argparse               # CLI interface
```

## 🔐 Configuration

### Environment Variables
```bash
# Optional: Custom Bedrock model
export BEDROCK_MODEL_ID="anthropic.claude-sonnet-4-5-20250929-v1:0"

# Optional: Inference profile ARN
export BEDROCK_INFERENCE_PROFILE_ARN="arn:aws:..."
```

### AWS Credentials
Configure via `~/.aws/credentials`:
```ini
[default]
aws_access_key_id = YOUR_KEY
aws_secret_access_key = YOUR_SECRET
region = us-east-1
```

## 📊 Output Examples

See `data/generated/recommendations/recommendations.json` for full examples.

### Key Metrics Included
- Exposure scores (geographic, sector, segment)
- Financial impact (FCF per share, % changes)
- Valuation impacts (price impact %, DCF breakdown)
- Regulatory context (regulation, region, severity)

## 🔗 Related Documentation

- `README_IMPACT_CALCULATOR.md` - 3-tier valuation architecture
- `README_IMPACT_ORCHESTRATOR.md` - Matching pairs generation
- `doc/SERVICES_AWS_ET_MODELES.md` - Bedrock configuration

## ✅ Testing

```bash
# Test with small subset
python scripts/impact_calculator.py --quant-engine --limit-pairs 5
python scripts/recommendation_generator.py --high-risk-threshold 50

# Test fallback behavior (no AWS credentials)
AWS_PROFILE="" python scripts/recommendation_generator.py

# Verify output structure
python -m json.tool data/generated/recommendations/recommendations.json | head -100
```

