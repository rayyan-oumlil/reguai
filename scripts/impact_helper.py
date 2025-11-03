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


def list_available_impact_analyses() -> List[Dict[str, Any]]:
    """
    List all available impact analysis files
    
    Returns:
        List of impact analysis metadata dictionaries
    """
    impact_dir = Path('data/generated/impact_analysis')
    
    if not impact_dir.exists():
        return []
    
    analyses = []
    
    # Try to load index file first
    index_path = impact_dir / 'impact_analysis_index.json'
    if index_path.exists():
        try:
            with open(index_path, 'r') as f:
                index_data = json.load(f)
                
            # Add each directive from index
            for directive in index_data.get('directives', []):
                analyses.append({
                    'filename': directive.get('filename'),
                    'title': directive.get('title', 'Unknown'),
                    'document_id': directive.get('document_id', 'Unknown'),
                    'total_matches': directive.get('total_matches', 0),
                    'filtered_matches': directive.get('filtered_matches', 0),
                    'path': str(impact_dir / directive.get('filename'))
                })
        except (json.JSONDecodeError, Exception) as e:
            print(f"❌ Error reading impact_analysis_index.json: {e}")
    
    # Also add matching_pairs.json if it exists (combines all)
    matching_pairs_path = impact_dir / 'matching_pairs.json'
    if matching_pairs_path.exists():
        analyses.insert(0, {
            'filename': 'matching_pairs.json',
            'title': 'Combined Analysis (All Regulations)',
            'document_id': 'all',
            'total_matches': 0,
            'filtered_matches': 0,
            'path': str(matching_pairs_path)
        })
    
    return analyses


def load_impact_results(impact_path: str = 'data/generated/impact_analysis/matching_pairs.json') -> Optional[Dict[str, Any]]:
    """
    Load impact analysis results from JSON
    
    Args:
        impact_path: Path to impact analysis JSON file
        
    Returns:
        Impact results dictionary or None if file not found
    """
    try:
        with open(impact_path, 'r') as f:
            data = json.load(f)
            
        # If single regulation file, wrap it in expected format
        if 'regulation_title' in data or 'regulation_id' in data or ('title' in data and 'document_id' in data):
            # Single regulation format - normalize and wrap it
            reg_id = data.get('regulation_id', data.get('document_id', 'single'))
            
            # Normalize field names for compatibility
            normalized_data = {
                'regulation_id': reg_id,
                'regulation_title': data.get('regulation_title', data.get('title', 'Unknown')),
                'regulation_country': data.get('regulation_country', data.get('country', 'Unknown')),
                'effective_date': data.get('effective_date', 'Unknown'),
                'total_companies_matched': data.get('total_companies_matched', data.get('filtered_matches', 0))
            }
            
            # Handle both 'companies' and 'all_companies' fields
            companies = data.get('companies', data.get('all_companies', []))
            if companies:
                normalized_data['companies'] = companies
            
            # Copy any other fields
            for key, value in data.items():
                if key not in normalized_data:
                    normalized_data[key] = value
            
            return {
                'regulations': {
                    reg_id: normalized_data
                },
                'metadata': {
                    'analysis_date': data.get('analysis_date', 'Unknown'),
                    'total_regulations': 1
                }
            }
        
        # Otherwise return as-is (matching_pairs format)
        return data
    except FileNotFoundError:
        print(f"❌ Impact results not found: {impact_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing impact results: {e}")
        return None


def load_recommendations(recommendations_path: str = 'data/generated/recommendations/recommendations.json') -> Optional[Dict[str, Any]]:
    """
    Load recommendations from JSON
    
    Args:
        recommendations_path: Path to recommendations.json
        
    Returns:
        Recommendations dictionary or None if file not found
    """
    try:
        with open(recommendations_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Recommendations not found: {recommendations_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"❌ Error parsing recommendations: {e}")
        return None


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
    
    risk_dist = companies_df.groupby('risk_premium_range').size().reset_index(name='count')
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
        
        heatmap_data = companies_df.groupby(['risk_bin', 'exposure_bin']).size().reset_index(name='count')
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
    
    # Format columns
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


def render_recommendations_table(recommendations: Dict[str, Any]):
    """
    Render recommendations table
    
    Args:
        recommendations: Recommendations dictionary
    """
    st.header("🤖 Trading Recommendations (Bedrock)")
    
    # Summary
    summary = recommendations.get('summary', {})
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("🔴 REDUCE", summary.get('reduce_recommendations_count', 0))
    
    with col2:
        st.metric("🟢 INCREASE", summary.get('increase_recommendations_count', 0))
    
    # Recommendations
    recs_data = recommendations.get('recommendations', {})
    
    # REDUCE recommendations
    if recs_data.get('reduce'):
        st.subheader("🔴 Reduce Positions")
        
        reduce_df = pd.DataFrame(recs_data['reduce'])
        display_cols = ['ticker', 'company_name', 'current_risk_score', 'risk_category', 'justification']
        
        for idx, row in reduce_df.iterrows():
            with st.expander(f"🔴 {row['ticker']} - {row['company_name']} (Risk: {row['current_risk_score']:.1f})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Risk Score:** {row['current_risk_score']:.1f} ({row['risk_category']})")
                    st.markdown(f"**Price Impact:** {row['metrics']['price_impact_percentage']:.2f}%")
                    st.markdown(f"**FCF Impact:** {row['metrics']['fcf_impact_per_share']:.4f}/share")
                
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
            with st.expander(f"🟢 {row['ticker']} - {row['company_name']} (Risk: {row['current_risk_score']:.1f})"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"**Risk Score:** {row['current_risk_score']:.1f} ({row['risk_category']})")
                    st.markdown(f"**Price Impact:** {row['metrics']['price_impact_percentage']:.2f}%")
                    st.markdown(f"**FCF Impact:** {row['metrics']['fcf_impact_per_share']:.4f}/share")
                
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
        companies_df: Companies impact DataFrame
        filter_regulation_id: Optional regulation ID to filter by
    """
    # Filter by regulation if provided
    if filter_regulation_id:
        filtered_df = companies_df[companies_df['regulation_id'] == filter_regulation_id].copy()
    else:
        filtered_df = companies_df.copy()
    
    if filtered_df.empty:
        st.info("No companies found for selected regulation")
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
    display_df['exposure_score'] = display_df['exposure_score'].apply(lambda x: f"{x:.1f}")
    display_df['fcf_impact_per_share'] = display_df['fcf_impact_per_share'].apply(lambda x: f"${x:.4f}")
    display_df['fcf_impact_pct'] = display_df['fcf_impact_pct'].apply(lambda x: f"{x:.2f}%")
    display_df['risk_premium'] = display_df['risk_premium'].apply(lambda x: f"{x*100:.2f}%")
    display_df['price_impact_pct'] = display_df['price_impact_pct'].apply(lambda x: f"{x:.2f}%")
    display_df['final_risk_score'] = display_df['final_risk_score'].apply(lambda x: f"{x:.1f}")
    
    # Display table with search
    search_term = st.text_input("🔍 Search Companies", key="company_search")
    
    if search_term:
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

