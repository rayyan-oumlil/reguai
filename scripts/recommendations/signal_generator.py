#!/usr/bin/env python3
"""
Signal Generator - Quantamental Trading Signals from Regulatory Impact Analysis

Transforms 3-tier DCF valuation impact into actionable trading signals:
- Fundamental Signal: Long-term value based on DCF impact
- Momentum Signal: Short-term mispricing opportunities
- Concentration Signal: Risk management based on exposure
- Composite Alpha Signal: Unified signal combining all perspectives

Usage:
    from signal_generator import SignalGenerator
    
    generator = SignalGenerator()
    signals = generator.generate_signals(
        ticker='AAPL',
        regulation_id='EU-2024-1689',
        tier_results=valuation_impact,
        company_data=company_data,
        market_data=market_data
    )
"""

import math
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from enum import Enum


class InvestmentStrategy(Enum):
    """Investment strategy types for signal weighting"""
    LONG_ONLY = "LONG_ONLY"
    LONG_SHORT = "LONG_SHORT"
    RISK_PARITY = "RISK_PARITY"
    BALANCED = "BALANCED"


class SignalStrength(Enum):
    """Signal strength categories"""
    STRONG_SELL = "STRONG_SELL"
    SELL = "SELL"
    MILD_SELL = "MILD_SELL"
    NEUTRAL = "NEUTRAL"
    MILD_BUY = "MILD_BUY"
    BUY = "BUY"
    STRONG_BUY = "STRONG_BUY"


class SignalGenerator:
    """
    Quantamental Signal Generator
    
    Converts regulatory impact analysis into actionable trading signals
    across multiple time horizons and investment strategies
    """
    
    def __init__(self):
        """Initialize signal generator"""
        pass
    
    def generate_signals(
        self,
        ticker: str,
        regulation_id: str,
        tier_results: Dict[str, Any],
        company_data: Dict[str, Any],
        market_data: Dict[str, Any],
        investment_strategy: str = 'LONG_ONLY',
        recent_volatility: float = 0.2,
        days_since_news: int = 0,
        recent_price_change: float = 0.0,
        portfolio_weight: float = 0.01,
        sector_concentration: float = 0.05
    ) -> Dict[str, Any]:
        """
        Generate comprehensive trading signals from valuation impact
        
        Args:
            ticker: Company ticker symbol
            regulation_id: Regulation identifier
            tier_results: Tier 1, 2, 3 impact results
            company_data: Company data from universe
            market_data: Market data including portfolio weight
            investment_strategy: Strategy type (LONG_ONLY, LONG_SHORT, RISK_PARITY, BALANCED)
            recent_volatility: Recent 20-day volatility
            days_since_news: Days since regulation announcement
            recent_price_change: Recent 5-day price movement (%)
            portfolio_weight: Portfolio weight of this position
            sector_concentration: Sector concentration in portfolio
            
        Returns:
            Complete signal analysis with all components
        """
        # Extract tier 3 DCF results
        tier3_impact = tier_results.get('tier_3_dcf_valuation', {})
        tier1_impact = tier_results.get('tier_1_cash_flow_impact', {})
        tier2_impact = tier_results.get('tier_2_discount_rate_adjustment', {})
        
        # Calculate confidence score
        confidence_score = self._calculate_confidence_score(
            tier1_impact, tier2_impact, tier3_impact
        )
        
        # Generate component signals
        fundamental_signal = self.calculate_fundamental_signal(
            tier3_impact, 
            confidence_score
        )
        
        momentum_signal = self.calculate_momentum_signal(
            tier3_impact.get('price_impact_percentage', 0),
            recent_volatility,
            days_since_news,
            recent_price_change
        )
        
        concentration_signal = self.calculate_concentration_signal(
            company_data.get('exposure_score', 0),
            portfolio_weight,
            sector_concentration
        )
        
        # Calculate composite alpha signal
        composite_signal = self.calculate_composite_alpha(
            fundamental_signal,
            momentum_signal,
            concentration_signal,
            investment_strategy
        )
        
        # Build comprehensive response
        return {
            'ticker': ticker,
            'regulation_id': regulation_id,
            'composite_alpha_signal': composite_signal['composite_signal'],
            'signal_strength': composite_signal['signal_strength'],
            'component_signals': {
                'fundamental': fundamental_signal,
                'momentum': momentum_signal,
                'concentration': concentration_signal
            },
            'underlying_analysis': {
                'tier1': tier1_impact,
                'tier2': tier2_impact,
                'tier3': tier3_impact
            },
            'metadata': {
                'processed_at': datetime.utcnow().isoformat(),
                'analysis_version': 'v1.0',
                'confidence_score': confidence_score,
                'investment_strategy': investment_strategy
            }
        }
    
    def calculate_fundamental_signal(
        self,
        tier3_impact: Dict[str, Any],
        confidence_score: float
    ) -> Dict[str, Any]:
        """
        C.1.1 Fundamental Signal (Long-Term Value)
        
        Purpose: For fundamental investors who care about intrinsic value changes
        Direct DCF-based price impact, adjusted for confidence
        
        Args:
            tier3_impact: Tier 3 DCF valuation results
            confidence_score: Model confidence score (0-1)
            
        Returns:
            Fundamental signal with metadata
        """
        # Base signal is the theoretical price impact
        base_signal = tier3_impact.get('price_impact_percentage', 0)
        
        # Adjust for model confidence
        confidence_adjusted = base_signal * confidence_score
        
        # Apply non-linear scaling for extreme moves
        if abs(confidence_adjusted) > 20:
            # Cap extreme moves and apply damping
            scaled_signal = math.copysign(
                min(30, 20 + (abs(confidence_adjusted) - 20) * 0.5),
                confidence_adjusted
            )
        else:
            scaled_signal = confidence_adjusted
        
        return {
            'signal_value': round(scaled_signal, 2),
            'base_impact': round(base_signal, 2),
            'confidence_multiplier': round(confidence_score, 3),
            'signal_type': 'FUNDAMENTAL_DCF',
            'time_horizon': 'LONG_TERM',  # 6-18 months
            'interpretation': self._interpret_fundamental_signal(scaled_signal)
        }
    
    def calculate_momentum_signal(
        self,
        price_impact_pct: float,
        recent_volatility: float,
        days_since_news: int = 0,
        recent_price_change: float = 0.0
    ) -> Dict[str, Any]:
        """
        C.1.2 Momentum Signal (Short-Term Trading)
        
        Purpose: Identify mispricings where market hasn't reacted yet
        Signal based on gap between theoretical impact and market reaction
        
        Args:
            price_impact_pct: Theoretical DCF price impact (%)
            recent_volatility: Recent 20-day historical volatility
            days_since_news: Days since regulation news
            recent_price_change: Recent 5-day price movement (%)
            
        Returns:
            Momentum signal with metadata
        """
        # Calculate the "mispricing gap"
        mispricing_gap = price_impact_pct - recent_price_change
        
        # Normalize by volatility to get signal strength
        if recent_volatility > 0:
            volatility_normalized = mispricing_gap / recent_volatility
        else:
            volatility_normalized = mispricing_gap / 0.01  # Default 1% vol
        
        # Apply decay based on time since regulation news
        time_decay = math.exp(-days_since_news / 10.0)  # Half-life ~7 days
        
        momentum_signal = volatility_normalized * time_decay
        
        return {
            'signal_value': round(momentum_signal, 2),
            'mispricing_gap': round(mispricing_gap, 2),
            'recent_price_move': round(recent_price_change, 2),
            'volatility_ratio': round(volatility_normalized, 2),
            'time_decay_factor': round(time_decay, 3),
            'signal_type': 'MOMENTUM_MISPRICING',
            'time_horizon': 'SHORT_TERM',  # 1-10 days
            'interpretation': self._interpret_momentum_signal(momentum_signal)
        }
    
    def calculate_concentration_signal(
        self,
        exposure_score: float,
        portfolio_weight: float,
        sector_concentration: float
    ) -> Dict[str, Any]:
        """
        C.1.3 Concentration Signal (Risk Management)
        
        Purpose: Identify companies with dangerous exposure concentrations
        Risk signal based on exposure concentration and portfolio importance
        
        Args:
            exposure_score: Exposure score (0-100)
            portfolio_weight: Portfolio weight of position
            sector_concentration: Sector concentration in portfolio
            
        Returns:
            Concentration signal with metadata
        """
        # Base concentration risk
        concentration_risk = exposure_score / 100.0  # Normalize to 0-1
        
        # Amplify if stock has large portfolio weight
        portfolio_amplifier = 1.0 + (portfolio_weight * 10)  # 1% weight → 1.1x
        
        # Amplify if sector is highly concentrated
        sector_amplifier = 1.0 + (sector_concentration * 2)
        
        # Combine factors
        raw_signal = -concentration_risk * portfolio_amplifier * sector_amplifier
        
        # Convert to percentage scale
        concentration_signal = raw_signal * 50  # Scale to meaningful range
        
        return {
            'signal_value': round(concentration_signal, 2),
            'exposure_risk': round(concentration_risk, 3),
            'portfolio_amplifier': round(portfolio_amplifier, 2),
            'sector_amplifier': round(sector_amplifier, 2),
            'signal_type': 'CONCENTRATION_RISK',
            'time_horizon': 'MEDIUM_TERM',  # Portfolio rebalancing timeframe
            'interpretation': self._interpret_concentration_signal(concentration_signal)
        }
    
    def calculate_composite_alpha(
        self,
        fundamental: Dict[str, Any],
        momentum: Dict[str, Any],
        concentration: Dict[str, Any],
        investment_strategy: str = 'LONG_ONLY'
    ) -> Dict[str, Any]:
        """
        C.1.4 Composite Alpha Signal
        
        Purpose: Unified signal combining all three perspectives with strategy-aware weighting
        Combine signals based on investment strategy
        
        Args:
            fundamental: Fundamental signal results
            momentum: Momentum signal results
            concentration: Concentration signal results
            investment_strategy: Strategy type
            
        Returns:
            Composite signal with strength categorization
        """
        # Strategy-specific weights
        weights = self._get_strategy_weights(investment_strategy)
        
        # Calculate weighted composite
        composite = (
            fundamental['signal_value'] * weights['fundamental'] +
            momentum['signal_value'] * weights['momentum'] + 
            concentration['signal_value'] * weights['concentration']
        )
        
        # Apply non-linear transformation for extreme values
        if abs(composite) > 10:
            composite = math.copysign(10 + (abs(composite) - 10) * 0.3, composite)
        
        # Categorize signal strength
        signal_strength = self.categorize_signal_strength(composite)
        
        return {
            'composite_signal': round(composite, 2),
            'component_signals': {
                'fundamental': fundamental,
                'momentum': momentum, 
                'concentration': concentration
            },
            'strategy_weights': weights,
            'investment_strategy': investment_strategy,
            'signal_strength': signal_strength
        }
    
    def categorize_signal_strength(self, composite_signal: float) -> Dict[str, Any]:
        """
        C.2 Signal Categorization & Action Mapping
        
        Convert numerical signal to actionable categories
        
        Args:
            composite_signal: Composite signal value
            
        Returns:
            Signal strength categorization with action recommendations
        """
        if composite_signal <= -8.0:
            return {
                'category': 'STRONG_SELL',
                'action': 'IMMEDIATE_REDUCTION',
                'confidence': 'HIGH',
                'suggested_weight_change': '-3% to -5%'
            }
        elif composite_signal <= -4.0:
            return {
                'category': 'SELL', 
                'action': 'GRADUAL_REDUCTION',
                'confidence': 'MEDIUM',
                'suggested_weight_change': '-1% to -3%'
            }
        elif composite_signal <= -2.0:
            return {
                'category': 'MILD_SELL',
                'action': 'MONITOR_CLOSELY',
                'confidence': 'LOW', 
                'suggested_weight_change': '0% to -1%'
            }
        elif composite_signal >= 8.0:
            return {
                'category': 'STRONG_BUY',
                'action': 'IMMEDIATE_ADD',
                'confidence': 'HIGH',
                'suggested_weight_change': '+3% to +5%'
            }
        elif composite_signal >= 4.0:
            return {
                'category': 'BUY',
                'action': 'GRADUAL_ADD',
                'confidence': 'MEDIUM',
                'suggested_weight_change': '+1% to +3%'
            }
        elif composite_signal >= 2.0:
            return {
                'category': 'MILD_BUY',
                'action': 'CONSIDER_INCREASE',
                'confidence': 'LOW',
                'suggested_weight_change': '0% to +1%'
            }
        else:
            return {
                'category': 'NEUTRAL',
                'action': 'HOLD',
                'confidence': 'LOW',
                'suggested_weight_change': '0%'
            }
    
    def _calculate_confidence_score(
        self,
        tier1_impact: Dict[str, Any],
        tier2_impact: Dict[str, Any],
        tier3_impact: Dict[str, Any]
    ) -> float:
        """
        Calculate overall confidence score based on data quality and impact magnitude
        
        Args:
            tier1_impact: Tier 1 cash flow impact
            tier2_impact: Tier 2 risk premium adjustment
            tier3_impact: Tier 3 DCF valuation
            
        Returns:
            Confidence score (0-1)
        """
        confidence_factors = []
        
        # Factor 1: Data completeness
        tier1_complete = (
            tier1_impact.get('annual_fcf_impact', 0) != 0 or
            tier1_impact.get('total_measures_analyzed', 0) > 0
        )
        tier3_complete = tier3_impact.get('price_impact_percentage', 0) != 0
        
        if tier1_complete and tier3_complete:
            confidence_factors.append(0.4)
        elif tier1_complete or tier3_complete:
            confidence_factors.append(0.2)
        else:
            confidence_factors.append(0.0)
        
        # Factor 2: Impact magnitude (more extreme impacts = lower confidence in model)
        price_impact = abs(tier3_impact.get('price_impact_percentage', 0))
        if price_impact > 30:
            confidence_factors.append(0.1)  # Very extreme, less confident
        elif price_impact > 15:
            confidence_factors.append(0.3)
        else:
            confidence_factors.append(0.5)
        
        # Factor 3: Tier 2 risk adjustment data quality
        if tier2_impact.get('total_risk_premium', 0) != 0:
            confidence_factors.append(0.2)
        
        return min(sum(confidence_factors), 1.0)
    
    def _get_strategy_weights(self, strategy: str) -> Dict[str, float]:
        """
        Get strategy-specific weighting scheme
        
        Args:
            strategy: Investment strategy type
            
        Returns:
            Weights dictionary
        """
        if strategy == 'LONG_ONLY':
            return {
                'fundamental': 0.60,   # Focus on long-term value
                'momentum': 0.25,      # Some timing consideration
                'concentration': 0.15   # Risk management
            }
        elif strategy == 'LONG_SHORT':
            return {
                'fundamental': 0.40,   # Balanced approach
                'momentum': 0.45,      # Heavy on timing
                'concentration': 0.15
            }
        elif strategy == 'RISK_PARITY':
            return {
                'fundamental': 0.30,
                'momentum': 0.20, 
                'concentration': 0.50   # Heavy risk focus
            }
        else:  # Default balanced
            return {
                'fundamental': 0.50, 
                'momentum': 0.30, 
                'concentration': 0.20
            }
    
    def _interpret_fundamental_signal(self, signal: float) -> str:
        """Interpret fundamental signal value"""
        if signal <= -10:
            return f"Stock is {abs(signal):.1f}% overvalued due to regulation"
        elif signal <= -5:
            return f"Stock is {abs(signal):.1f}% overvalued (regulatory headwind)"
        elif signal <= -2:
            return f"Mildly overvalued ({abs(signal):.1f}%)"
        elif signal >= 10:
            return f"Stock is {signal:.1f}% undervalued (beneficiary)"
        elif signal >= 5:
            return f"Stock is {signal:.1f}% undervalued (regulatory tailwind)"
        elif signal >= 2:
            return f"Mildly undervalued ({signal:.1f}%)"
        else:
            return "Fairly valued based on regulation"
    
    def _interpret_momentum_signal(self, signal: float) -> str:
        """Interpret momentum signal value"""
        if signal <= -5:
            return f"Strong sell signal (big impact, no price reaction)"
        elif signal <= -2:
            return f"Sell signal (impact not yet priced in)"
        elif signal <= -0.5:
            return f"Mild sell signal"
        elif signal >= 5:
            return f"Strong buy signal (positive impact, price hasn't moved)"
        elif signal >= 2:
            return f"Buy signal (positive impact not yet priced)"
        elif signal >= 0.5:
            return f"Mild buy signal"
        else:
            return f"Neutral (market has reacted appropriately)"
    
    def _interpret_concentration_signal(self, signal: float) -> str:
        """Interpret concentration signal value"""
        if signal <= -20:
            return f"High concentration risk (reduce position)"
        elif signal <= -10:
            return f"Moderate concentration risk"
        elif signal <= -2:
            return f"Low concentration risk"
        else:
            return f"Acceptable concentration"
