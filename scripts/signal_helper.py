"""
Signal Helper - Streamlit Helper Functions for Signal Generation

Loads impact analysis results and generates quantamental signals,
providing visualization and analysis tools for the Streamlit app.
"""

import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from typing import Dict, List, Any, Optional
import sys
sys.path.append(str(Path(__file__).parent))
from signal_generator import SignalGenerator, InvestmentStrategy

try:
    import streamlit as st
except ImportError:
    # Create proper mock for testing
    import sys
    from unittest.mock import MagicMock
    st = MagicMock()


def generate_signals_for_analysis(
    impact_results: Dict[str, Any],
    investment_strategy: str = 'LONG_ONLY'
) -> Dict[str, Any]:
    """
    Generate signals for all companies in impact analysis results
    
    Args:
        impact_results: Impact analysis results dictionary
        investment_strategy: Investment strategy type
        
    Returns:
        Signals dictionary organized by regulation and ticker
    """
    generator = SignalGenerator()
    all_signals = {}
    
    # Process each regulation
    for reg_id, reg_data in impact_results.get('regulations', {}).items():
        all_signals[reg_id] = {
            'regulation_id': reg_id,
            'regulation_title': reg_data.get('regulation_title', 'Unknown'),
            'signals': []
        }
        
        # Process each company
        for company in reg_data.get('companies', []):
            ticker = company.get('ticker')
            
            # Extract tier results
            valuation_impact = company.get('valuation_impact', {})
            quantitative_analysis = company.get('quantitative_analysis', {})
            
            # Skip if no valuation impact data
            if not valuation_impact or not quantitative_analysis:
                continue
            
            # Extract portfolio weight from market data
            market_data = company.get('market_data', {})
            if not market_data:
                # Try to get from company data if available
                market_data = {}
            
            portfolio_weight = market_data.get('sp500_weight', 0.01)
            
            # Generate signal
            signal_result = generator.generate_signals(
                ticker=ticker,
                regulation_id=reg_id,
                tier_results=valuation_impact,
                company_data={
                    'exposure_score': company.get('exposure_score', 0)
                },
                market_data=market_data,
                investment_strategy=investment_strategy,
                recent_volatility=0.2,  # Default 20% vol
                days_since_news=0,  # Default: recent
                recent_price_change=0.0,  # Default: no reaction
                portfolio_weight=portfolio_weight,
                sector_concentration=0.05  # Default 5% sector concentration
            )
            
            all_signals[reg_id]['signals'].append(signal_result)
    
    return all_signals


def signals_to_dataframe(signals_data: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert signals data to DataFrame for display
    
    Args:
        signals_data: Signals dictionary
        
    Returns:
        DataFrame with signals data
    """
    rows = []
    
    for reg_id, reg_data in signals_data.items():
        for signal in reg_data.get('signals', []):
            rows.append({
                'regulation_id': reg_id,
                'regulation_title': reg_data.get('regulation_title', 'Unknown'),
                'ticker': signal.get('ticker'),
                'composite_signal': signal.get('composite_alpha_signal', 0),
                'signal_category': signal.get('signal_strength', {}).get('category', 'NEUTRAL'),
                'signal_action': signal.get('signal_strength', {}).get('action', 'HOLD'),
                'confidence': signal.get('signal_strength', {}).get('confidence', 'LOW'),
                'weight_change': signal.get('signal_strength', {}).get('suggested_weight_change', '0%'),
                
                # Component signals
                'fundamental_signal': signal.get('component_signals', {}).get('fundamental', {}).get('signal_value', 0),
                'momentum_signal': signal.get('component_signals', {}).get('momentum', {}).get('signal_value', 0),
                'concentration_signal': signal.get('component_signals', {}).get('concentration', {}).get('signal_value', 0),
                
                # Underlying analysis
                'price_impact_pct': signal.get('underlying_analysis', {}).get('tier3', {}).get('price_impact_percentage', 0),
                'confidence_score': signal.get('metadata', {}).get('confidence_score', 0),
                'investment_strategy': signal.get('metadata', {}).get('investment_strategy', 'UNKNOWN')
            })
    
    return pd.DataFrame(rows)


def render_signals_summary(signals_df: pd.DataFrame):
    """
    Render signal analysis summary KPIs
    
    Args:
        signals_df: Signals DataFrame
    """
    if signals_df.empty:
        st.info("No signals data available")
        return
    
    # Calculate metrics
    total_signals = len(signals_df)
    avg_composite = signals_df['composite_signal'].mean()
    strong_signals = len(signals_df[signals_df['signal_category'].isin(['STRONG_BUY', 'STRONG_SELL'])])
    buy_signals = len(signals_df[signals_df['signal_category'].isin(['BUY', 'STRONG_BUY', 'MILD_BUY'])])
    sell_signals = len(signals_df[signals_df['signal_category'].isin(['SELL', 'STRONG_SELL', 'MILD_SELL'])])
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📊 Total Signals",
            total_signals,
            help="Total signals generated"
        )
    
    with col2:
        st.metric(
            "⚖️ Avg Composite Signal",
            f"{avg_composite:.2f}",
            delta=f"{avg_composite:.2f}",
            delta_color="normal" if abs(avg_composite) < 2 else "inverse",
            help="Average composite alpha signal"
        )
    
    with col3:
        st.metric(
            "🟢 Buy Signals",
            buy_signals,
            delta=f"{buy_signals/total_signals*100:.1f}%" if total_signals > 0 else "0%",
            help="Buy and strong buy signals"
        )
    
    with col4:
        st.metric(
            "🔴 Sell Signals",
            sell_signals,
            delta=f"{sell_signals/total_signals*100:.1f}%" if total_signals > 0 else "0%",
            delta_color="inverse",
            help="Sell and strong sell signals"
        )


def render_signals_distribution(signals_df: pd.DataFrame):
    """
    Render signal distribution charts
    
    Args:
        signals_df: Signals DataFrame
    """
    if signals_df.empty:
        return
    
    st.subheader("📊 Signal Distribution Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Signal category distribution
        category_counts = signals_df['signal_category'].value_counts()
        
        fig = px.bar(
            x=category_counts.index,
            y=category_counts.values,
            title='Signal Category Distribution',
            labels={'x': 'Category', 'y': 'Count'},
            color=category_counts.values,
            color_continuous_scale='RdYlGn_r'
        )
        
        fig.update_layout(height=350, showlegend=False)
        fig.update_xaxes(tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Composite signal distribution
        fig2 = px.histogram(
            signals_df,
            x='composite_signal',
            nbins=20,
            title='Composite Signal Distribution',
            labels={'composite_signal': 'Composite Signal', 'count': 'Count'},
            color_discrete_sequence=['#1f77b4']
        )
        
        fig2.update_layout(height=350, showlegend=False)
        fig2.add_vline(x=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig2, use_container_width=True)


def render_component_signals_chart(signals_df: pd.DataFrame):
    """
    Render component signals comparison
    
    Args:
        signals_df: Signals DataFrame
    """
    if signals_df.empty:
        return
    
    st.subheader("📊 Component Signal Analysis")
    
    # Top 20 by absolute composite signal
    top_signals = signals_df.nlargest(20, 'composite_signal', keep='all')
    top_signals = top_signals.sort_values('composite_signal')
    
    # Create grouped bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Fundamental',
        x=top_signals['ticker'],
        y=top_signals['fundamental_signal'],
        marker_color='#1f77b4'
    ))
    
    fig.add_trace(go.Bar(
        name='Momentum',
        x=top_signals['ticker'],
        y=top_signals['momentum_signal'],
        marker_color='#ff7f0e'
    ))
    
    fig.add_trace(go.Bar(
        name='Concentration',
        x=top_signals['ticker'],
        y=top_signals['concentration_signal'],
        marker_color='#2ca02c'
    ))
    
    fig.add_trace(go.Bar(
        name='Composite',
        x=top_signals['ticker'],
        y=top_signals['composite_signal'],
        marker_color='#d62728'
    ))
    
    fig.update_layout(
        title='Top 20 Signals: Component Breakdown',
        xaxis_title='Ticker',
        yaxis_title='Signal Value',
        barmode='group',
        height=400,
        showlegend=True
    )
    
    fig.add_hline(y=0, line_dash="dash", line_color="gray")
    st.plotly_chart(fig, use_container_width=True)


def render_signals_table(signals_df: pd.DataFrame):
    """
    Render interactive signals table
    
    Args:
        signals_df: Signals DataFrame
    """
    if signals_df.empty:
        return
    
    st.subheader("📋 Trading Signals")
    
    # Filter options
    col1, col2, col3 = st.columns(3)
    
    with col1:
        category_filter = st.multiselect(
            "Filter by Category",
            options=signals_df['signal_category'].unique(),
            default=signals_df['signal_category'].unique()
        )
    
    with col2:
        strategy_filter = st.selectbox(
            "Investment Strategy",
            options=signals_df['investment_strategy'].unique() if 'investment_strategy' in signals_df.columns else ['ALL']
        )
    
    with col3:
        search_term = st.text_input("🔍 Search Tickers", "")
    
    # Apply filters
    filtered_df = signals_df.copy()
    
    if category_filter:
        filtered_df = filtered_df[filtered_df['signal_category'].isin(category_filter)]
    
    if strategy_filter and strategy_filter != 'ALL':
        filtered_df = filtered_df[filtered_df['investment_strategy'] == strategy_filter]
    
    if search_term:
        mask = (
            filtered_df['ticker'].str.contains(search_term, case=False) |
            filtered_df['regulation_title'].str.contains(search_term, case=False)
        )
        filtered_df = filtered_df[mask]
    
    # Display table
    display_cols = [
        'ticker',
        'regulation_title',
        'composite_signal',
        'signal_category',
        'signal_action',
        'confidence',
        'weight_change',
        'price_impact_pct'
    ]
    
    display_df = filtered_df[display_cols].copy()
    
    # Format columns
    display_df['composite_signal'] = display_df['composite_signal'].apply(lambda x: f"{x:.2f}")
    display_df['price_impact_pct'] = display_df['price_impact_pct'].apply(lambda x: f"{x:.2f}%")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )


def render_signal_details(signal: Dict[str, Any]):
    """
    Render detailed signal information
    
    Args:
        signal: Signal dictionary
    """
    st.subheader(f"📈 Signal Details: {signal.get('ticker')}")
    
    # Main metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Composite Alpha Signal",
            f"{signal.get('composite_alpha_signal', 0):.2f}",
            help="Weighted combination of all signals"
        )
    
    with col2:
        signal_strength = signal.get('signal_strength', {})
        st.metric(
            "Category",
            signal_strength.get('category', 'NEUTRAL'),
            help=signal_strength.get('action', 'HOLD')
        )
    
    with col3:
        st.metric(
            "Confidence",
            signal_strength.get('confidence', 'LOW'),
            help=f"Suggested: {signal_strength.get('suggested_weight_change', '0%')}"
        )
    
    # Component breakdown
    st.markdown("### Component Signals")
    
    components = signal.get('component_signals', {})
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        fundamental = components.get('fundamental', {})
        st.metric(
            "Fundamental Signal",
            f"{fundamental.get('signal_value', 0):.2f}",
            help=fundamental.get('interpretation', '')
        )
    
    with col2:
        momentum = components.get('momentum', {})
        st.metric(
            "Momentum Signal",
            f"{momentum.get('signal_value', 0):.2f}",
            help=momentum.get('interpretation', '')
        )
    
    with col3:
        concentration = components.get('concentration', {})
        st.metric(
            "Concentration Signal",
            f"{concentration.get('signal_value', 0):.2f}",
            help=concentration.get('interpretation', '')
        )
    
    # Underlying analysis
    with st.expander("🔍 Underlying Analysis"):
        underlying = signal.get('underlying_analysis', {})
        
        tier3 = underlying.get('tier3', {})
        if tier3:
            st.markdown("**Tier 3: DCF Valuation**")
            st.json(tier3)
        
        tier1 = underlying.get('tier1', {})
        if tier1:
            st.markdown("**Tier 1: Cash Flow Impact**")
            st.json(tier1)
        
        tier2 = underlying.get('tier2', {})
        if tier2:
            st.markdown("**Tier 2: Risk Premium**")
            st.json(tier2)

