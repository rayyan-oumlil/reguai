"""
Impact Helper - Streamlit Helper Functions for Impact Analysis

Loads and displays 3-tier valuation results and recommendations
"""

import json
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# Import streamlit only when needed (for testing outside streamlit)
try:
    import streamlit as st
except ImportError:
    # Create proper mock for testing
    import sys
    from unittest.mock import MagicMock
    
    # Create mock module
    st = MagicMock()
    
    # Add context managers
    class ContextManager:
        def __enter__(self):
            return MagicMock()
        def __exit__(self, *args):
            return None
    
    st.expander.return_value.__enter__ = lambda self: MagicMock()
    st.expander.return_value.__exit__ = lambda self, *args: None
    st.spinner.return_value.__enter__ = lambda self: MagicMock()
    st.spinner.return_value.__exit__ = lambda self, *args: None
    st.columns.return_value = [MagicMock() for _ in range(3)]
    st.tabs.return_value = [MagicMock() for _ in range(3)]
    
    # Add other needed attributes
    st.number_input = MagicMock(return_value=500)
    st.selectbox = MagicMock(return_value=0)
    st.multiselect = MagicMock(return_value=[])
    st.slider = MagicMock(return_value=0.3)
    st.checkbox = MagicMock(return_value=True)
    st.button = MagicMock(return_value=False)
    st.text_area = MagicMock()
    st.rerun = MagicMock()
    st.divider = MagicMock()


def load_impact_results(impact_path: str = 'data/generated/impact_analysis/matching_pairs.json') -> Optional[Dict[str, Any]]:
    """
    Load impact analysis results from JSON
    Tries to load from matching_pairs.json first (has Tier 2/3 data),
    then enriches with individual *_impact.json files if needed
    
    Args:
        impact_path: Path to impact analysis JSON file
        
    Returns:
        Impact results dictionary or None if file not found
    """
    # First, try loading from matching_pairs.json (has complete Tier 2/3 data)
    impact_dir = Path('data/generated/impact_analysis')
    matching_pairs_path = impact_dir / 'matching_pairs.json'
    
    matching_pairs_data = None
    if matching_pairs_path.exists():
        try:
            with open(matching_pairs_path, 'r', encoding='utf-8') as f:
                matching_pairs_data = json.load(f)
        except Exception as e:
            print(f"⚠️ Error loading matching_pairs.json: {e}")
    
    # Use matching_pairs.json directly (all directives in it have Tier 2/3)
    # Les fichiers *_impact.json incomplets ont été supprimés
    if matching_pairs_data and 'regulations' in matching_pairs_data:
        return matching_pairs_data
    
    # Last fallback: try loading from specified path
    try:
        with open(impact_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    except FileNotFoundError:
        print(f"❌ Impact results not found: {impact_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing impact results: {e}")
        return None


def load_recommendations(recommendations_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Load recommendations - only per-directive format (all_recommendations.json)
    """
    rec_dir = Path('data/generated/recommendations')
    
    # Only load per-directive format (all_recommendations.json)
    if recommendations_path is None:
        all_recs_path = rec_dir / 'all_recommendations.json'
        if all_recs_path.exists():
            try:
                with open(all_recs_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return None
    
    # Load from specified path if provided
    rec_path = Path(recommendations_path)
    if not rec_path.exists():
        return None
    
    try:
        with open(rec_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


def load_recommendations_per_directive() -> Dict[str, Dict[str, Any]]:
    """
    Load recommendations per directive from individual files or all_recommendations.json
    
    Returns:
        Dictionary mapping regulation_id to recommendations dict
    """
    rec_dir = Path('data/generated/recommendations')
    recommendations_by_directive = {}
    
    # Try to load from all_recommendations.json first
    all_recs_path = rec_dir / 'all_recommendations.json'
    if all_recs_path.exists():
        try:
            with open(all_recs_path, 'r', encoding='utf-8') as f:
                all_data = json.load(f)
                recommendations_by_directive = all_data.get('recommendations_by_directive', {})
                return recommendations_by_directive
        except Exception:
            pass
    
    # Fallback: load individual recommendation files
    rec_files = list(rec_dir.glob("*_recommendations.json"))
    for rec_file in rec_files:
        try:
            with open(rec_file, 'r', encoding='utf-8') as f:
                rec_data = json.load(f)
                reg_id = rec_data.get('regulation_id', rec_file.stem)
                recommendations_by_directive[reg_id] = rec_data
        except Exception:
            continue
    
    return recommendations_by_directive


def impact_results_to_dataframes(impact_results: Dict[str, Any]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Convert impact results to DataFrames
    
    Args:
        impact_results: Impact results dictionary
        
    Returns:
        Tuple of (companies_df, regulations_df)
    """
    companies_data = []
    regulations_data = []
    
    for reg_id, reg_data in impact_results.get('regulations', {}).items():
        # Regulation-level data
        reg_entry = {
            'regulation_id': reg_id,
            'regulation_title': reg_data.get('regulation_title', 'N/A'),
            'regulation_country': reg_data.get('regulation_country', 'N/A'),
            'total_companies': reg_data.get('total_companies_matched', 0),
            'effective_date': reg_data.get('effective_date', 'N/A')
        }
        regulations_data.append(reg_entry)
        
        # Company-level data
        for company in reg_data.get('companies', []):
            company_entry = {
                'regulation_id': reg_id,
                'regulation_title': reg_data.get('regulation_title', 'N/A'),
                'ticker': company.get('ticker', 'N/A'),
                'company_name': company.get('company_name', 'N/A'),
                'exposure_score': company.get('exposure_score', 0),
            }
            
            # Tier 1: FCF Impact
            tier1 = company.get('valuation_impact', {}).get('tier_1_cash_flow_impact', {})
            company_entry['fcf_impact_per_share'] = tier1.get('fcf_impact_per_share', 0)
            company_entry['fcf_impact_pct'] = tier1.get('fcf_impact_percentage', 0)
            
            # Tier 2: Risk Premium
            tier2 = company.get('valuation_impact', {}).get('tier_2_discount_rate_adjustment', {})
            company_entry['risk_premium'] = tier2.get('total_risk_premium', 0)
            company_entry['discount_rate_change_bps'] = tier2.get('discount_rate_change_bps', 0)
            
            # Tier 3: Price Impact
            tier3 = company.get('valuation_impact', {}).get('tier_3_dcf_valuation', {})
            company_entry['price_impact_pct'] = tier3.get('price_impact_percentage', 0)
            
            # Final Risk Score
            final_risk = company.get('final_risk_score', {})
            company_entry['final_risk_score'] = final_risk.get('final_risk_score', 0)
            company_entry['risk_category'] = final_risk.get('risk_category', 'Unknown')
            
            companies_data.append(company_entry)
    
    companies_df = pd.DataFrame(companies_data)
    regulations_df = pd.DataFrame(regulations_data)
    
    return companies_df, regulations_df


def render_impact_summary(companies_df: pd.DataFrame, regulations_df: pd.DataFrame):
    """
    Render impact analysis summary KPIs
    
    Args:
        companies_df: Companies impact DataFrame
        regulations_df: Regulations DataFrame
    """
    # Calculate metrics
    total_companies = len(companies_df)
    avg_risk_score = companies_df['final_risk_score'].mean()
    avg_price_impact = companies_df['price_impact_pct'].mean()
    high_risk_count = len(companies_df[companies_df['risk_category'].isin(['Moderate', 'High'])])
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "📊 Companies Analyzed",
            total_companies,
            help="Total companies with regulatory exposure"
        )
    
    with col2:
        st.metric(
            "⚠️ Average Risk Score",
            f"{avg_risk_score:.1f}/100",
            delta=f"{avg_risk_score - 50:.1f}",
            help="Average final risk score across all companies"
        )
    
    with col3:
        st.metric(
            "💰 Average Price Impact",
            f"{avg_price_impact:.2f}%",
            delta=f"{abs(avg_price_impact):.2f}",
            delta_color="inverse",
            help="Average estimated price impact from DCF valuation"
        )
    
    with col4:
        st.metric(
            "🔴 High Risk Companies",
            high_risk_count,
            delta=f"{high_risk_count / total_companies * 100:.1f}%",
            delta_color="inverse",
            help="Companies with Moderate or High risk"
        )


def render_tier1_fcf_chart(companies_df: pd.DataFrame):
    """
    Render Tier 1 FCF Impact charts
    
    Args:
        companies_df: Companies impact DataFrame
    """
    st.subheader("📊 Tier 1: Cash Flow Impact per Share")
    
    # Two-column layout for charts
    col1, col2 = st.columns(2)
    
    with col1:
        # Top 15 by FCF impact (absolute)
        top_fcf = companies_df.nlargest(15, 'fcf_impact_per_share', keep='all')
        
        fig = px.bar(
            top_fcf,
            x='ticker',
            y='fcf_impact_per_share',
            color='fcf_impact_pct',
            title='Top 15 by FCF Impact ($/share)',
            labels={
                'ticker': 'Ticker',
                'fcf_impact_per_share': 'FCF Impact ($/share)',
                'fcf_impact_pct': 'FCF Impact %'
            },
            color_continuous_scale='Reds',
            hover_data=['company_name', 'fcf_impact_pct']
        )
        
        fig.update_layout(height=350, showlegend=True)
        fig.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Top 15 by FCF impact percentage
        top_fcf_pct = companies_df.nlargest(15, 'fcf_impact_pct', keep='all')
        
        fig2 = px.bar(
            top_fcf_pct,
            x='ticker',
            y='fcf_impact_pct',
            color='exposure_score',
            title='Top 15 by FCF Impact (%)',
            labels={
                'ticker': 'Ticker',
                'fcf_impact_pct': 'FCF Impact (%)',
                'exposure_score': 'Exposure Score'
            },
            color_continuous_scale='Oranges',
            hover_data=['company_name', 'fcf_impact_per_share']
        )
        
        fig2.update_layout(height=350, showlegend=True)
        fig2.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig2, use_container_width=True)
    
    # Distribution histogram
    fig3 = px.histogram(
        companies_df,
        x='fcf_impact_per_share',
        nbins=20,
        title='FCF Impact Distribution',
        labels={
            'fcf_impact_per_share': 'FCF Impact ($/share)',
            'count': 'Number of Companies'
        },
        color_discrete_sequence=['#1f77b4']
    )
    fig3.update_layout(height=250, showlegend=False)
    fig3.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="No Impact")
    st.plotly_chart(fig3, use_container_width=True)


def render_tier2_risk_chart(companies_df: pd.DataFrame):
    """
    Render Tier 2 Risk Premium chart
    
    Args:
        companies_df: Companies impact DataFrame
    """
    st.subheader("📊 Tier 2: Risk Premium Adjustment")
    
    # Group by risk premium ranges
    companies_df['risk_premium_range'] = pd.cut(
        companies_df['risk_premium'],
        bins=[0, 0.5, 1.0, 1.5, 2.0, 5.0],
        labels=['0-0.5%', '0.5-1.0%', '1.0-1.5%', '1.5-2.0%', '2.0%+']
    )
    
    risk_dist = companies_df.groupby('risk_premium_range').size().reset_index()
    risk_dist.columns = ['risk_premium_range', 'count']
    risk_dist['risk_premium_range'] = risk_dist['risk_premium_range'].astype(str)
    
    fig = px.bar(
        risk_dist,
        x='risk_premium_range',
        y='count',
        title='Distribution of Risk Premium Adjustments',
        labels={
            'risk_premium_range': 'Risk Premium Range (%)',
            'count': 'Number of Companies'
        },
        color='count',
        color_continuous_scale='Oranges'
    )
    
    fig.update_layout(height=400, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)


def render_tier3_price_impact_chart(companies_df: pd.DataFrame):
    """
    Render Tier 3 Price Impact chart
    
    Args:
        companies_df: Companies impact DataFrame
    """
    st.subheader("📊 Tier 3: Price Impact % (DCF Valuation)")
    
    # Two-column layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Top 20 by absolute price impact
        top_price = companies_df.nlargest(20, 'price_impact_pct', keep='all').sort_values('price_impact_pct')
        
        fig = px.bar(
            top_price,
            x='ticker',
            y='price_impact_pct',
            color='final_risk_score',
            title='Top 20 by Price Impact',
            labels={
                'ticker': 'Ticker',
                'price_impact_pct': 'Price Impact (%)',
                'final_risk_score': 'Risk Score'
            },
            color_continuous_scale='RdYlGn_r',
            hover_data=['company_name', 'final_risk_score', 'risk_category']
        )
        
        fig.update_layout(height=350, showlegend=True)
        fig.add_hline(y=0, line_dash="dash", line_color="gray", annotation_text="No Impact")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Scatter plot: Risk vs Price Impact
        fig2 = px.scatter(
            companies_df,
            x='final_risk_score',
            y='price_impact_pct',
            size='exposure_score',
            color='risk_category',
            title='Risk Score vs Price Impact',
            labels={
                'final_risk_score': 'Risk Score',
                'price_impact_pct': 'Price Impact (%)',
                'exposure_score': 'Exposure',
                'risk_category': 'Category'
            },
            hover_data=['ticker', 'company_name'],
            size_max=15
        )
        
        fig2.update_layout(height=350, showlegend=True)
        fig2.add_vline(x=50, line_dash="dash", line_color="gray", annotation_text="Medium Risk")
        fig2.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig2, use_container_width=True)
    
    # Price impact distribution
    fig3 = px.histogram(
        companies_df,
        x='price_impact_pct',
        nbins=20,
        title='Price Impact Distribution',
        labels={
            'price_impact_pct': 'Price Impact (%)',
            'count': 'Number of Companies'
        },
        color_discrete_sequence=['#ff6b6b']
    )
    fig3.update_layout(height=250, showlegend=False)
    fig3.add_vline(x=0, line_dash="dash", line_color="red", annotation_text="No Impact")
    st.plotly_chart(fig3, use_container_width=True)


def render_final_risk_distribution(companies_df: pd.DataFrame):
    """
    Render final risk score distribution
    
    Args:
        companies_df: Companies impact DataFrame
    """
    st.subheader("📊 Final Risk Score Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Histogram with risk categories
        fig = px.histogram(
            companies_df,
            x='final_risk_score',
            color='risk_category',
            title='Risk Score Distribution by Category',
            labels={
                'final_risk_score': 'Final Risk Score',
                'count': 'Number of Companies',
                'risk_category': 'Risk Category'
            },
            nbins=20
        )
        
        fig.update_layout(height=350, showlegend=True)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Box plot by category
        fig2 = px.box(
            companies_df,
            x='risk_category',
            y='final_risk_score',
            title='Risk Score by Category',
            labels={
                'final_risk_score': 'Risk Score',
                'risk_category': 'Risk Category'
            }
        )
        
        fig2.update_layout(height=350, showlegend=False)
        st.plotly_chart(fig2, use_container_width=True)
    
    # Heatmap: Risk vs Exposure
    if len(companies_df) > 1:
        # Create bins for heatmap
        companies_df['exposure_bin'] = pd.cut(
            companies_df['exposure_score'],
            bins=[0, 20, 40, 60, 80, 100],
            labels=['0-20', '20-40', '40-60', '60-80', '80-100']
        )
        companies_df['risk_bin'] = pd.cut(
            companies_df['final_risk_score'],
            bins=[0, 20, 40, 60, 80, 100],
            labels=['0-20', '20-40', '40-60', '60-80', '80-100']
        )
        
        heatmap_data = companies_df.groupby(['risk_bin', 'exposure_bin']).size().reset_index()
        heatmap_data.columns = ['risk_bin', 'exposure_bin', 'count']
        heatmap_pivot = heatmap_data.pivot(index='exposure_bin', columns='risk_bin', values='count').fillna(0)
        
        fig3 = go.Figure(data=go.Heatmap(
            z=heatmap_pivot.values,
            x=[str(col) for col in heatmap_pivot.columns],
            y=[str(idx) for idx in heatmap_pivot.index],
            colorscale='YlOrRd',
            text=heatmap_pivot.values,
            texttemplate='%{text}',
            textfont={"size": 12},
            hoverongaps=False
        ))
        
        fig3.update_layout(
            title='Risk Score vs Exposure Score Heatmap',
            xaxis_title='Risk Score Range',
            yaxis_title='Exposure Score Range',
            height=350
        )
        st.plotly_chart(fig3, use_container_width=True)


def render_companies_table(companies_df: pd.DataFrame):
    """
    Render interactive companies impact table
    
    Args:
        companies_df: Companies impact DataFrame
    """
    st.subheader("📋 Companies Impact Analysis")
    
    # Prepare display DataFrame
    display_df = companies_df[[
        'ticker',
        'company_name',
        'exposure_score',
        'fcf_impact_per_share',
        'price_impact_pct',
        'final_risk_score',
        'risk_category'
    ]].copy()
    
    # Format columns (ensure DataFrame, not ndarray)
    if isinstance(display_df, pd.DataFrame):
        display_df['exposure_score'] = display_df['exposure_score'].apply(lambda x: f"{x:.1f}")
        display_df['fcf_impact_per_share'] = display_df['fcf_impact_per_share'].apply(lambda x: f"${x:.4f}")
        display_df['price_impact_pct'] = display_df['price_impact_pct'].apply(lambda x: f"{x:.2f}%")
        display_df['final_risk_score'] = display_df['final_risk_score'].apply(lambda x: f"{x:.1f}")
    
    # Display table
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True
    )


def render_recommendations_table(recommendations: Dict[str, Any], selected_reg_id: Optional[str] = None):
    """
    Render recommendations table
    Supports both per-directive format (all_recommendations.json) and global format
    
    Args:
        recommendations: Recommendations dictionary (can be all_recommendations or single recommendations)
        selected_reg_id: Optional regulation ID to filter by (from directive selector at top)
    """
    # Check if this is the per-directive format
    if 'recommendations_by_directive' in recommendations:
        # Per-directive format
        recommendations_by_directive = recommendations.get('recommendations_by_directive', {})
        
        # Filter by selected directive if provided
        if selected_reg_id and selected_reg_id in recommendations_by_directive:
            # Only show the selected directive
            rec_data = recommendations_by_directive[selected_reg_id]
            reg_title = rec_data.get('regulation_title', selected_reg_id)
            summary = rec_data.get('summary', {})
            
            # Summary metrics for this directive only
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🔴 REDUCE", summary.get('reduce_recommendations_count', 0))
            with col2:
                st.metric("🟢 INCREASE", summary.get('increase_recommendations_count', 0))
            
            st.divider()
            
            # Display recommendations for this directive
            _render_single_recommendations(rec_data)
        else:
            # No filter - show all directives (shouldn't happen in normal flow)
            st.header("🤖 Trading Recommendations par Directive")
            total_summary = recommendations.get('summary', {})
            
            # Overall summary
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🔴 Total REDUCE", total_summary.get('total_reduce', 0))
            with col2:
                st.metric("🟢 Total INCREASE", total_summary.get('total_increase', 0))
            
            st.divider()
            
            # Display per directive
            for reg_id, rec_data in recommendations_by_directive.items():
                reg_title = rec_data.get('regulation_title', reg_id)
                summary = rec_data.get('summary', {})
                
                with st.expander(f"📋 {reg_title[:60]}... (🔴 {summary.get('reduce_recommendations_count', 0)} | 🟢 {summary.get('increase_recommendations_count', 0)})", expanded=False):
                    _render_single_recommendations(rec_data)
        
        return
    
    # Global format (old format)
    st.header("🤖 Trading Recommendations (Bedrock)")
    
    # Summary
    summary = recommendations.get('summary', {})
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("🔴 REDUCE", summary.get('reduce_recommendations_count', 0))
    
    with col2:
        st.metric("🟢 INCREASE", summary.get('increase_recommendations_count', 0))
    
    _render_single_recommendations(recommendations)


def _render_single_recommendations(recommendations: Dict[str, Any]):
    """Render recommendations for a single directive"""
    # Recommendations
    recs_data = recommendations.get('recommendations', {})
    
    # REDUCE recommendations
    if recs_data.get('reduce'):
        st.subheader("🔴 Reduce Positions")
        
        reduce_df = pd.DataFrame(recs_data['reduce'])
        display_cols = ['ticker', 'company_name', 'current_risk_score', 'risk_category', 'justification']
        
        for idx, row in reduce_df.iterrows():
            risk_label = f"{row['current_risk_score']:.1f} (3-Tier DCF)"
            
            with st.expander(f"🔴 {row['ticker']} - {row['company_name']} (Risk: {risk_label})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Risk Score:** {row['current_risk_score']:.1f} ({row['risk_category']})")
                    st.markdown(f"**Price Impact:** {row['metrics']['price_impact_percentage']:.2f}%")
                    st.markdown(f"**FCF Impact:** {row['metrics']['fcf_impact_per_share']:.4f}/share")
                    st.markdown(f"**Exposure Score:** {row['metrics']['exposure_score']:.1f}")
                
                with col2:
                    st.markdown(f"**Regulation:** {row['regulatory_context']['regulation']}")
                    st.markdown(f"**Region:** {row['regulatory_context']['region']}")
                
                st.markdown("**Justification:**")
                st.info(row['justification'])
    
    # INCREASE recommendations
    if recs_data.get('increase'):
        st.subheader("🟢 Consider Increasing Positions")
        
        increase_df = pd.DataFrame(recs_data['increase'])
        
        for idx, row in increase_df.iterrows():
            risk_label = f"{row['current_risk_score']:.1f} (3-Tier DCF)"
            
            with st.expander(f"🟢 {row['ticker']} - {row['company_name']} (Risk: {risk_label})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Risk Score:** {row['current_risk_score']:.1f} ({row['risk_category']})")
                    st.markdown(f"**Price Impact:** {row['metrics']['price_impact_percentage']:.2f}%")
                    st.markdown(f"**FCF Impact:** {row['metrics']['fcf_impact_per_share']:.4f}/share")
                    st.markdown(f"**Exposure Score:** {row['metrics']['exposure_score']:.1f}")
                
                with col2:
                    st.markdown(f"**Regulation:** {row['regulatory_context']['regulation']}")
                    st.markdown(f"**Region:** {row['regulatory_context']['region']}")
                
                st.markdown("**Justification:**")
                st.success(row['justification'])


def render_regulation_selector(regulations_df: pd.DataFrame):
    """
    Render regulation selector dropdown
    
    Args:
        regulations_df: Regulations DataFrame
        
    Returns:
        Selected regulation or None
    """
    if regulations_df.empty:
        return None
    
    # If only one regulation, return it directly (no need for selector)
    if len(regulations_df) == 1:
        return regulations_df.iloc[0].to_dict()
    
    # Create display labels
    regulations_df['display_label'] = regulations_df.apply(
        lambda row: f"{row['regulation_title'][:50]}... ({row['regulation_country']})",
        axis=1
    )
    
    selected_idx = st.selectbox(
        "Select Regulation:",
        range(len(regulations_df)),
        format_func=lambda x: regulations_df.iloc[x]['display_label']
    )
    
    if selected_idx is not None:
        return regulations_df.iloc[selected_idx].to_dict()
    return None


def render_company_details_table(companies_df: pd.DataFrame, filter_regulation_id: Optional[str] = None):
    """
    Render detailed company impacts table
    
    Args:
        companies_df: Companies impact DataFrame (already filtered by directive)
        filter_regulation_id: Optional regulation ID to filter by (usually None since already filtered)
    """
    # Use companies_df directly since it's already filtered by directive
    filtered_df = companies_df.copy()
    
    if filtered_df.empty:
        st.info("Aucune entreprise trouvée pour cette directive")
        return
    
    # Sort by final risk score (descending)
    filtered_df = filtered_df.sort_values('final_risk_score', ascending=False)
    
    # Create detailed display DataFrame
    display_cols = [
        'ticker',
        'company_name',
        'exposure_score',
        'fcf_impact_per_share',
        'fcf_impact_pct',
        'risk_premium',
        'price_impact_pct',
        'final_risk_score',
        'risk_category'
    ]
    
    display_df = filtered_df[display_cols].copy()
    
    # Format numeric columns
    # Format columns (ensure DataFrame, not ndarray)
    if isinstance(display_df, pd.DataFrame):
        display_df['exposure_score'] = display_df['exposure_score'].apply(lambda x: f"{x:.1f}")
        display_df['fcf_impact_per_share'] = display_df['fcf_impact_per_share'].apply(lambda x: f"${x:.4f}")
        display_df['fcf_impact_pct'] = display_df['fcf_impact_pct'].apply(lambda x: f"{x:.2f}%")
        display_df['risk_premium'] = display_df['risk_premium'].apply(lambda x: f"{x*100:.2f}%")
        display_df['price_impact_pct'] = display_df['price_impact_pct'].apply(lambda x: f"{x:.2f}%")
        display_df['final_risk_score'] = display_df['final_risk_score'].apply(lambda x: f"{x:.1f}")
    
    # Display table with search
    search_term = st.text_input("🔍 Search Companies", key="company_search")
    
    if search_term and isinstance(display_df, pd.DataFrame):
        mask = (
            display_df['ticker'].str.contains(search_term, case=False) |
            display_df['company_name'].str.contains(search_term, case=False)
        )
        display_df = display_df[mask]
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )


# ============================================
# SIGNAL HELPER FUNCTIONS (merged from signal_helper.py)
# ============================================

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from scripts.recommendations.signal_generator import SignalGenerator, InvestmentStrategy


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
        
        # Get companies for this regulation
        companies = reg_data.get('companies', [])
        
        # Process each company
        for company in companies:
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


def signals_to_dataframe(signals_data: Dict[str, Any], impact_results: Optional[Dict[str, Any]] = None) -> pd.DataFrame:
    """
    Convert signals data to DataFrame for display
    
    Args:
        signals_data: Signals dictionary
        impact_results: Optional impact results to get company names
        
    Returns:
        DataFrame with signals data
    """
    rows = []
    
    # Create a mapping from ticker to company_name if impact_results provided
    ticker_to_name = {}
    if impact_results:
        for reg_id, reg_data in impact_results.get('regulations', {}).items():
            for company in reg_data.get('companies', []):
                ticker = company.get('ticker')
                company_name = company.get('company_name') or company.get('market_data', {}).get('company_name', '')
                if ticker:
                    ticker_to_name[ticker] = company_name
    
    for reg_id, reg_data in signals_data.items():
        for signal in reg_data.get('signals', []):
            ticker = signal.get('ticker')
            company_name = ticker_to_name.get(ticker, '') if ticker else ''
            
            rows.append({
                'regulation_id': reg_id,
                'regulation_title': reg_data.get('regulation_title', 'Unknown'),
                'ticker': ticker,
                'company_name': company_name,
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
    """Render signals table"""
    if signals_df.empty:
        st.info("Aucun signal disponible")
        return
    
    # Display columns - use only columns that exist in the dataframe
    available_cols = signals_df.columns.tolist()
    
    # Map desired columns to available columns
    display_cols = []
    col_mapping = {
        'ticker': 'ticker',
        'company_name': 'company_name',
        'signal': 'signal_action',
        'strength': 'weight_change',
        'confidence': 'confidence',
        'expected_return': 'composite_signal'
    }
    
    for desired_col in ['ticker', 'company_name', 'signal', 'strength', 'confidence', 'expected_return']:
        actual_col = col_mapping.get(desired_col)
        if actual_col and actual_col in available_cols:
            display_cols.append(actual_col)
    
    # If no valid columns found, use available columns
    if not display_cols:
        display_cols = available_cols[:6]  # Take first 6 columns
    
    st.dataframe(
        signals_df[display_cols],
        use_container_width=True,
        hide_index=True
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

