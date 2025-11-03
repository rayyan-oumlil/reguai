# Signal Generator - Quantamental Trading Signals

## Overview

The Signal Generator transforms regulatory impact analysis into actionable trading signals across multiple investment horizons and strategies. It converts the 3-tier DCF valuation framework into practical portfolio management decisions.

## Architecture

The system generates three primary signal types:

1. **Fundamental Signal** (Long-Term Value)
   - Based on DCF-based price impact
   - Confidence-adjusted
   - Non-linear scaling for extreme moves
   - Time horizon: 6-18 months

2. **Momentum Signal** (Short-Term Trading)
   - Gap between theoretical impact and market reaction
   - Volatility-normalized
   - Time decay based on news recency
   - Time horizon: 1-10 days

3. **Concentration Signal** (Risk Management)
   - Exposure concentration risk
   - Portfolio weight amplifier
   - Sector concentration amplifier
   - Time horizon: Medium-term rebalancing

4. **Composite Alpha Signal**
   - Weighted combination of all three
   - Strategy-specific weighting
   - Non-linear transformation
   - Actionable categorization

## Usage

### Basic Usage

```python
from scripts.signal_generator import SignalGenerator

generator = SignalGenerator()

signal_result = generator.generate_signals(
    ticker='AAPL',
    regulation_id='EU-2024-1689',
    tier_results=valuation_impact,
    company_data=company_data,
    market_data=market_data
)

print(signal_result['composite_alpha_signal'])
print(signal_result['signal_strength'])
```

### From Impact Analysis

```python
from scripts.signal_helper import generate_signals_for_analysis

# Generate signals for all companies in impact results
signals_data = generate_signals_for_analysis(
    impact_results,
    investment_strategy='LONG_ONLY'
)

# Convert to DataFrame
from scripts.signal_helper import signals_to_dataframe
signals_df = signals_to_dataframe(signals_data)
```

### In Streamlit

The signals are automatically integrated into the "📈 Analyse d'Impact" page:

1. Load impact analysis results
2. Signals are generated automatically
3. View in the "📈 Trading Signals" section
4. Visualize distributions, component breakdowns, and tables

## Investment Strategies

The system supports multiple investment strategies with different weighting schemes:

### LONG_ONLY (Default)
- Fundamental: 60%
- Momentum: 25%
- Concentration: 15%

### LONG_SHORT
- Fundamental: 40%
- Momentum: 45%
- Concentration: 15%

### RISK_PARITY
- Fundamental: 30%
- Momentum: 20%
- Concentration: 50%

### BALANCED
- Fundamental: 50%
- Momentum: 30%
- Concentration: 20%

## Signal Categorization

Signals are automatically categorized into actionable recommendations:

| Category | Composite Signal | Action | Confidence | Weight Change |
|----------|-----------------|--------|------------|---------------|
| STRONG_SELL | ≤ -8.0 | IMMEDIATE_REDUCTION | HIGH | -3% to -5% |
| SELL | -8.0 to -4.0 | GRADUAL_REDUCTION | MEDIUM | -1% to -3% |
| MILD_SELL | -4.0 to -2.0 | MONITOR_CLOSELY | LOW | 0% to -1% |
| NEUTRAL | -2.0 to +2.0 | HOLD | LOW | 0% |
| MILD_BUY | +2.0 to +4.0 | CONSIDER_INCREASE | LOW | 0% to +1% |
| BUY | +4.0 to +8.0 | GRADUAL_ADD | MEDIUM | +1% to +3% |
| STRONG_BUY | ≥ +8.0 | IMMEDIATE_ADD | HIGH | +3% to +5% |

## Signal Interpretation

### Fundamental Signal
- **-10%**: "Stock is 10% overvalued due to regulation"
- **+5%**: "Stock is 5% undervalued (beneficiary)"

### Momentum Signal
- **-8.2**: Strong sell signal (big impact, no price reaction)
- **+6.7**: Strong buy signal (positive impact, price hasn't moved)
- **±0.3**: Neutral (market has reacted appropriately)

### Concentration Signal
- **-25.0**: High concentration risk (reduce position)
- **-8.5**: Moderate concentration risk
- **-1.2**: Low concentration risk

## Visualizations

The system provides comprehensive visualizations:

1. **Signal Summary KPIs**
   - Total signals
   - Average composite signal
   - Buy vs Sell distribution
   - Confidence levels

2. **Signal Distribution**
   - Category distribution bar chart
   - Composite signal histogram

3. **Component Signals**
   - Grouped bar chart of all components
   - Top 20 signals breakdown

4. **Interactive Table**
   - Filterable by category, strategy
   - Searchable by ticker
   - Sortable columns

## Configuration

Key parameters for signal generation:

```python
signal_result = generator.generate_signals(
    ticker='AAPL',
    regulation_id='EU-2024-1689',
    tier_results=valuation_impact,
    company_data=company_data,
    market_data=market_data,
    
    # Strategy configuration
    investment_strategy='LONG_ONLY',  # LONG_ONLY, LONG_SHORT, RISK_PARITY, BALANCED
    
    # Market data
    recent_volatility=0.2,           # Recent 20-day volatility
    days_since_news=0,               # Days since regulation announcement
    recent_price_change=0.0,         # Recent 5-day price movement (%)
    
    # Portfolio data
    portfolio_weight=0.01,           # Portfolio weight of position
    sector_concentration=0.05        # Sector concentration
)
```

## Output Format

```json
{
  "ticker": "AAPL",
  "regulation_id": "EU-2024-1689",
  "composite_alpha_signal": -7.42,
  "signal_strength": {
    "category": "STRONG_SELL",
    "action": "IMMEDIATE_REDUCTION",
    "confidence": "HIGH",
    "suggested_weight_change": "-3% to -5%"
  },
  "component_signals": {
    "fundamental": {
      "signal_value": -8.17,
      "signal_type": "FUNDAMENTAL_DCF",
      "time_horizon": "LONG_TERM",
      "interpretation": "Stock is 8.17% overvalued due to regulation"
    },
    "momentum": {
      "signal_value": -6.84,
      "signal_type": "MOMENTUM_MISPRICING",
      "time_horizon": "SHORT_TERM",
      "interpretation": "Sell signal (impact not yet priced in)"
    },
    "concentration": {
      "signal_value": -6.70,
      "signal_type": "CONCENTRATION_RISK",
      "time_horizon": "MEDIUM_TERM",
      "interpretation": "Moderate concentration risk"
    }
  },
  "underlying_analysis": {
    "tier1": {...},
    "tier2": {...},
    "tier3": {...}
  },
  "metadata": {
    "processed_at": "2025-11-02T14:30:45Z",
    "analysis_version": "v1.0",
    "confidence_score": 0.82,
    "investment_strategy": "LONG_ONLY"
  }
}
```

## Integration Points

### With Impact Analysis
- Automatically generates signals from tier 1, 2, 3 results
- Requires complete DCF valuation data
- Fallback handling for missing data

### With Streamlit UI
- Integrated into "📈 Analyse d'Impact" page
- Real-time generation and display
- Interactive filtering and visualization

### With Recommendation System
- Complements Bedrock-based recommendations
- Provides quantitative signal foundation
- Enables systematic portfolio adjustments

## Future Enhancements

Potential improvements:

1. **Real-time Market Data**
   - Integrate Yahoo Finance for recent price movements
   - Automatic volatility calculation
   - News sentiment integration

2. **Backtesting**
   - Historical signal performance
   - Signal accuracy metrics
   - Optimization of weighting schemes

3. **Advanced Strategies**
   - Multi-factor models
   - Mean reversion signals
   - Pairs trading signals

4. **Storage Architecture**
   - DynamoDB for signal storage
   - Historical tracking
   - Performance attribution

## Dependencies

- `scripts/signal_generator.py`: Core signal generation logic
- `scripts/signal_helper.py`: Streamlit integration and visualization
- `scripts/impact_calculator.py`: 3-tier DCF valuation
- `scripts/impact_helper.py`: Impact results loading

## Testing

```python
# Test with existing impact data
from pathlib import Path
import json
from scripts.signal_helper import generate_signals_for_analysis

# Load impact results
with open('data/generated/impact_analysis/matching_pairs.json') as f:
    impact_results = json.load(f)

# Generate signals
signals = generate_signals_for_analysis(impact_results)
print(f"Generated {len(signals)} regulation signals")
```

## References

- Section C of the comprehensive signal generation specification
- 3-tier DCF valuation methodology
- Quantamental signal design principles
