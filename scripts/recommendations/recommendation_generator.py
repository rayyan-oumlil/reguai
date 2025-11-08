#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Recommendation Generator - Bedrock-Powered Trading Recommendations

Uses Claude Sonnet via Bedrock to generate actionable trading recommendations
based on regulatory impact analysis.

Usage:
    python recommendation_generator.py --impact_results <path_to_matching_pairs.json>
    
Output:
    Generates recommendations JSON with:
    - Actions to reduce (high risk companies)
    - Actions to increase (low risk opportunities)
    - Justifications for each recommendation
"""

import boto3
import json
import os
import sys
import io
import argparse
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


class RecommendationGenerator:
    """
    Generate trading recommendations using Bedrock Claude Sonnet
    
    Identifies:
    - Companies to REDUCE exposure (high regulatory risk)
    - Companies to INCREASE exposure (low regulatory risk)
    - Justifications for each recommendation
    """
    
    def __init__(self, region_name: str = 'us-east-1'):
        """
        Initialize Bedrock client
        
        Args:
            region_name: AWS region
        """
        self.region_name = region_name
        self.aws_available = False
        
        # Try to initialize Bedrock client
        try:
            self.bedrock = boto3.client('bedrock-runtime', region_name=region_name)
            # Quick test to verify credentials work (try to list models)
            bedrock_client = boto3.client('bedrock', region_name=region_name)
            bedrock_client.list_foundation_models()
            self.aws_available = True
        except Exception:
            # AWS not available - will use fallback
            self.bedrock = None
            self.aws_available = False
        
        # Configure Bedrock model fallback strategy
        # Primary model: Claude Sonnet 4.5 (may require inference profile)
        self.model_id_primary = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-sonnet-4-5-20250929-v1:0')
        self.inference_profile_arn = os.getenv('BEDROCK_INFERENCE_PROFILE_ARN')
        # Safe fallback widely available on-demand
        self.model_id_fallback = 'us.anthropic.claude-3-5-sonnet-20241022-v2:0'
        
        # Risk thresholds
        self.high_risk_threshold = 60.0  # Score >= 60 = high risk
        self.low_risk_threshold = 30.0   # Score <= 30 = low risk
    
    def _invoke_bedrock(self, prompt: str, max_tokens: int = 2000) -> str:
        """
        Invoke Bedrock with fallback handling
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens in response
            
        Returns:
            Generated text response
        """
        # If AWS not available, raise to trigger fallback
        if not self.aws_available or not self.bedrock:
            raise Exception("AWS Bedrock not available - using fallback")
        
        payload = {
            'anthropic_version': 'bedrock-2023-05-31',
            'max_tokens': max_tokens,
            'messages': [{'role': 'user', 'content': prompt}]
        }
        
        # First try the primary model id
        try:
            response = self.bedrock.invoke_model(modelId=self.model_id_primary, body=json.dumps(payload))
        except Exception as e:
            msg = str(e)
            # If model requires inference profile, try with ARN or fallback
            if ('ValidationException' in msg) and ('inference profile' in msg.lower()):
                if self.inference_profile_arn:
                    try:
                        response = self.bedrock.invoke_model(modelId=self.inference_profile_arn, body=json.dumps(payload))
                    except Exception:
                        # If profile fails and primary wasn't fallback, try fallback
                        if self.model_id_primary != self.model_id_fallback:
                            response = self.bedrock.invoke_model(modelId=self.model_id_fallback, body=json.dumps(payload))
                        else:
                            raise
                else:
                    # No profile set: try fallback if not already primary
                    if self.model_id_primary != self.model_id_fallback:
                        response = self.bedrock.invoke_model(modelId=self.model_id_fallback, body=json.dumps(payload))
                    else:
                        raise
            else:
                # Propagate other errors
                raise
        
        # Parse response
        response_body = json.loads(response['body'].read())
        return response_body['content'][0]['text']
    
    def generate_recommendations(
        self,
        impact_results: Dict[str, Any],
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate trading recommendations from impact analysis
        
        Args:
            impact_results: Matching pairs JSON results
            output_path: Optional path to save recommendations
            
        Returns:
            Recommendations JSON
        """
        print("\n" + "="*80)
        print("🤖 GENERATING TRADING RECOMMENDATIONS WITH BEDROCK")
        print("="*80)
        
        # Extract all companies with their risk scores
        companies_analysis = self._extract_company_analyses(impact_results)
        
        # Classify companies by risk level (complete analysis always available)
        high_risk_companies = []
        low_risk_companies = []
        
        for c in companies_analysis:
            # Always use final_risk_score (complete analysis)
            risk_score = c.get('final_risk_score', {}).get('final_risk_score', 0)
            
            # Get price impact for additional criteria
            price_impact = 0
            valuation = c.get('valuation_impact', {})
            if valuation:
                tier3 = valuation.get('tier_3_dcf_valuation', {})
                price_impact = tier3.get('price_impact_percentage', 0)
            
            # Classify companies:
            # - High risk: risk_score >= 60 OR (risk_score >= 40 AND price_impact <= -10%)
            # - Low risk: risk_score <= 30 OR (risk_score <= 50 AND price_impact >= 5%)
            if risk_score >= self.high_risk_threshold or (risk_score >= 40 and price_impact <= -10):
                high_risk_companies.append(c)
            elif risk_score <= self.low_risk_threshold or (risk_score <= 50 and price_impact >= 5):
                low_risk_companies.append(c)
        
        print(f"📊 Analyzed {len(companies_analysis)} companies")
        print(f"⚠️  High risk companies (>={self.high_risk_threshold}): {len(high_risk_companies)}")
        print(f"✅ Low risk companies (<={self.low_risk_threshold}): {len(low_risk_companies)}")
        
        # Generate Bedrock recommendations
        reduce_recommendations = []
        increase_recommendations = []
        
        if high_risk_companies:
            print("\n🔴 Generating REDUCE recommendations...")
            for company in high_risk_companies:
                recommendation = self._generate_company_recommendation(
                    company,
                    recommendation_type='REDUCE'
                )
                if recommendation:
                    reduce_recommendations.append(recommendation)
                # If None returned (AWS not available), skip silently
        
        if low_risk_companies:
            print("\n🟢 Generating INCREASE recommendations...")
            for company in low_risk_companies:
                recommendation = self._generate_company_recommendation(
                    company,
                    recommendation_type='INCREASE'
                )
                if recommendation:
                    increase_recommendations.append(recommendation)
                # If None returned (AWS not available), skip silently
        
        # Build recommendations response
        recommendations = {
            'generated_at': datetime.now().isoformat(),
            'total_companies_analyzed': len(companies_analysis),
            'summary': {
                'high_risk_count': len(high_risk_companies),
                'low_risk_count': len(low_risk_companies),
                'reduce_recommendations_count': len(reduce_recommendations),
                'increase_recommendations_count': len(increase_recommendations)
            },
            'recommendations': {
                'reduce': reduce_recommendations,
                'increase': increase_recommendations
            },
            'risk_thresholds': {
                'high_risk': self.high_risk_threshold,
                'low_risk': self.low_risk_threshold
            }
        }
        
        # Save to file if path provided
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(recommendations, f, indent=2)
            print(f"\n💾 Saved recommendations to: {output_path}")
        
        print("\n✅ Recommendation generation complete!")
        
        return recommendations
    
    def _extract_company_analyses(self, impact_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract company analyses from impact results
        
        Args:
            impact_results: Matching pairs JSON
            
        Returns:
            List of company analysis dictionaries
        """
        companies = []
        
        for reg_id, reg_data in impact_results.get('regulations', {}).items():
            # Get regulation metadata
            regulation_title = reg_data.get('regulation_title', 'N/A')
            regulation_country = reg_data.get('regulation_country', 'N/A')
            
            for company in reg_data.get('companies', []):
                # Include company if it has either:
                # 1. DCF analysis (final_risk_score + valuation_impact), OR
                # 2. At least exposure_score (from Tier 1 matching)
                has_dcf = 'final_risk_score' in company and 'valuation_impact' in company
                has_exposure = 'exposure_score' in company
                
                if has_dcf or has_exposure:
                    # Add regulation context to company data
                    company_with_reg = company.copy()
                    company_with_reg['regulation_title'] = regulation_title
                    company_with_reg['regulation_country'] = regulation_country
                    companies.append(company_with_reg)
        
        return companies
    
    def _generate_company_recommendation(
        self,
        company: Dict[str, Any],
        recommendation_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generate recommendation for a single company using Bedrock
        
        Args:
            company: Company analysis data
            recommendation_type: 'REDUCE' or 'INCREASE'
            
        Returns:
            Recommendation dictionary
        """
        # Extract key metrics
        ticker = company.get('ticker', 'N/A')
        company_name = company.get('company_name', 'N/A')
        
        # Risk scores (always use final_risk_score - complete analysis)
        final_risk_score_data = company.get('final_risk_score', {})
        final_risk = final_risk_score_data.get('final_risk_score', 0)
        risk_category = final_risk_score_data.get('risk_category', 'Unknown')
        exposure_score = company.get('exposure_score', 0)
        
        # Valuation impact (always available - complete analysis)
        valuation = company.get('valuation_impact', {})
        tier1 = valuation.get('tier_1_cash_flow_impact', {})
        tier2 = valuation.get('tier_2_discount_rate_adjustment', {})
        tier3 = valuation.get('tier_3_dcf_valuation', {})
        
        fcf_impact = tier1.get('fcf_impact_per_share', 0)
        fcf_impact_pct = tier1.get('fcf_impact_percentage', 0)
        discount_rate_change = tier2.get('discount_rate_change_bps', 0)
        price_impact = tier3.get('price_impact_percentage', 0)
        
        # Regulatory context
        regulation_title = company.get('regulation_title', 'N/A')
        regulation_country = company.get('regulation_country', 'N/A')
        
        # Build prompt for Bedrock
        prompt = self._build_recommendation_prompt(
            ticker=ticker,
            company_name=company_name,
            recommendation_type=recommendation_type,
            final_risk=final_risk,
            risk_category=risk_category,
            exposure_score=exposure_score,
            fcf_impact=fcf_impact,
            fcf_impact_pct=fcf_impact_pct,
            discount_rate_change=discount_rate_change,
            price_impact=price_impact,
            regulation_title=regulation_title,
            regulation_country=regulation_country,
            matching_details=company.get('matching_details', {}),
            financial_analysis=company.get('quantitative_analysis', {}).get('financial_analysis', {}),
            regulatory_analysis=company.get('quantitative_analysis', {}).get('regulatory_analysis', {})
        )
        
        # Generate with Bedrock - use fallback if AWS not available
        if not self.aws_available or not self.bedrock:
            print(f"  ⚠️  AWS Bedrock not available - using fallback justification for {ticker}")
            justification = self._generate_fallback_justification(recommendation_type, final_risk, price_impact)
        else:
            try:
                justification = self._invoke_bedrock(prompt, max_tokens=1000)
                print(f"  ✅ Generated {recommendation_type} recommendation for {ticker}")
            except Exception as e:
                print(f"  ⚠️  Error generating recommendation for {ticker}: {e}")
                # Use fallback if Bedrock fails
                justification = self._generate_fallback_justification(recommendation_type, final_risk, price_impact)
        
        # Build recommendation (complete analysis always available)
        recommendation = {
            'ticker': ticker,
            'company_name': company_name,
            'recommendation': recommendation_type,
            'current_risk_score': round(final_risk, 2),
            'risk_category': risk_category,
            'metrics': {
                'exposure_score': round(exposure_score, 2),
                'fcf_impact_per_share': round(fcf_impact, 4),
                'fcf_impact_percentage': round(fcf_impact_pct, 2),
                'price_impact_percentage': round(price_impact, 2),
                'discount_rate_change_bps': int(discount_rate_change)
            },
            'regulatory_context': {
                'regulation': regulation_title,
                'region': regulation_country
            },
            'justification': justification.strip()
        }
        
        return recommendation
    
    def _build_recommendation_prompt(
        self,
        ticker: str,
        company_name: str,
        recommendation_type: str,
        final_risk: float,
        risk_category: str,
        exposure_score: float,
        fcf_impact: float,
        fcf_impact_pct: float,
        discount_rate_change: float,
        price_impact: float,
        regulation_title: str,
        regulation_country: str,
        matching_details: Dict[str, Any],
        financial_analysis: Dict[str, Any],
        regulatory_analysis: Dict[str, Any]
    ) -> str:
        """
        Build prompt for Bedrock recommendation generation
        
        Args:
            All company and regulation data
            
        Returns:
            Formatted prompt string
        """
        if recommendation_type == 'REDUCE':
            action = "reduce or exit"
            risk_reason = "high regulatory risk"
        else:  # INCREASE
            action = "consider increasing"
            risk_reason = "relatively low regulatory risk"
        
        prompt = f"""You are a senior portfolio manager providing investment recommendations based on regulatory impact analysis.

COMPANY: {company_name} ({ticker})

REGULATORY CONTEXT:
- Regulation: {regulation_title}
- Region: {regulation_country}

RISK ANALYSIS:
- Final Risk Score: {final_risk:.1f}/100 ({risk_category})
- Exposure Score: {exposure_score:.1f}/100
- FCF Impact: {fcf_impact:.4f} per share ({fcf_impact_pct:+.2f}%)
- Price Impact: {price_impact:+.2f}%
- Discount Rate Change: {discount_rate_change:.0f} bps

FINANCIAL METRICS:
- Revenue: ${financial_analysis.get('revenue', 0):,.0f}
- FCF: ${financial_analysis.get('free_cash_flow', 0):,.0f}
- Market Cap: ${financial_analysis.get('market_cap', 0):,.0f}
- Financial Health: {financial_analysis.get('financial_strength', 'Unknown')}

REGULATORY SEVERITY:
- Overall Severity: {regulatory_analysis.get('overall_severity', 0):.1f}/100
- Classification: {regulatory_analysis.get('regulatory_classification', 'Unknown')}

MATCHING REASONS:
- Geographic Match: {matching_details.get('by_country', {}).get('matched', False)}
- Sector Match: {matching_details.get('by_sector', {}).get('matched', False)}
- Segments Match: {matching_details.get('by_segments', {}).get('matched', False)}

TASK:
Provide a professional, data-driven investment recommendation to {action} position in {ticker} due to {risk_reason}.

REQUIREMENTS:
1. Write 2-3 concise paragraphs
2. Focus on the quantitative metrics (risk score, price impact, FCF impact)
3. Explain the regulatory exposure and why it matters
4. Be specific about the magnitude of impact
5. Use professional investment language
6. Don't include bullet points - use full sentences

OUTPUT:
Write only the justification text, nothing else."""

        return prompt
    
    def _generate_fallback_justification(
        self,
        recommendation_type: str,
        final_risk: float,
        price_impact: float
    ) -> str:
        """
        Generate basic fallback justification if Bedrock fails
        
        Args:
            recommendation_type: 'REDUCE' or 'INCREASE'
            final_risk: Risk score
            price_impact: Price impact percentage
            
        Returns:
            Basic justification text
        """
        if recommendation_type == 'REDUCE':
            return (
                f"We recommend reducing exposure due to elevated regulatory risk score of {final_risk:.1f}/100. "
                f"The estimated price impact of {price_impact:+.2f}% reflects significant fundamental headwinds from "
                f"the regulatory changes. Given the sustained negative impact on free cash flow and valuation, "
                f"prudent risk management suggests reducing position size or exiting entirely."
            )
        else:  # INCREASE
            return (
                f"This company presents a relatively attractive opportunity with a low risk score of {final_risk:.1f}/100. "
                f"The regulatory impact appears manageable with minimal estimated price impact of {price_impact:+.2f}%. "
                f"The company's strong fundamentals and limited regulatory exposure suggest it may outperform "
                f"more exposed peers. Consider increasing allocation to capture potential relative value."
            )


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Generate trading recommendations using Bedrock',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        '--impact_results',
        type=str,
        default='data/generated/impact_analysis/matching_pairs.json',
        help='Path to impact analysis results JSON'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='data/generated/recommendations/recommendations.json',
        help='Output path for recommendations JSON'
    )
    parser.add_argument(
        '--region',
        type=str,
        default='us-east-1',
        help='AWS region for Bedrock (default: us-east-1)'
    )
    parser.add_argument(
        '--high-risk-threshold',
        type=float,
        default=60.0,
        help='High risk threshold (default: 60.0)'
    )
    parser.add_argument(
        '--low-risk-threshold',
        type=float,
        default=30.0,
        help='Low risk threshold (default: 30.0)'
    )
    
    args = parser.parse_args()
    
    # Load impact results
    print(f"📂 Loading impact results from: {args.impact_results}")
    with open(args.impact_results, 'r') as f:
        impact_results = json.load(f)
    
    # Create output directory
    output_dir = Path(args.output).parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Generate recommendations
    generator = RecommendationGenerator(region_name=args.region)
    generator.high_risk_threshold = args.high_risk_threshold
    generator.low_risk_threshold = args.low_risk_threshold
    
    recommendations = generator.generate_recommendations(
        impact_results,
        output_path=args.output
    )
    
    # Print summary
    print("\n" + "="*80)
    print("📊 RECOMMENDATIONS SUMMARY")
    print("="*80)
    print(f"Total companies analyzed: {recommendations['total_companies_analyzed']}")
    print(f"🔴 REDUCE recommendations: {recommendations['summary']['reduce_recommendations_count']}")
    print(f"🟢 INCREASE recommendations: {recommendations['summary']['increase_recommendations_count']}")
    print("="*80)


if __name__ == '__main__':
    main()

