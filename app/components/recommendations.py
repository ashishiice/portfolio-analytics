"""
Recommendations Component
Streamlit component for displaying prioritized action recommendations.
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

# Import utils
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.risk_metrics import calculate_risk_score
from utils.glide_path import get_rebalancing_urgency, calculate_drift
from utils.tax_tracker import identify_harvest_opportunities, classify_gains, TAX_RULES


def create_priority_card(priority: int, title: str, problem: str, 
                        current_state: str, recommendation: str, 
                        expected_impact: str, color: str):
    """Create a styled priority card."""
    
    color_map = {
        'red': {'bg': '#fadbd8', 'border': '#e74c3c', 'icon': '🔴'},
        'yellow': {'bg': '#fcf3cf', 'border': '#f1c40f', 'icon': '🟡'},
        'green': {'bg': '#d5f5e3', 'border': '#27ae60', 'icon': '🟢'}
    }
    
    colors = color_map.get(color, color_map['yellow'])
    
    st.markdown(f"""
        <div style="background-color: {colors['bg']}; 
                    border-left: 5px solid {colors['border']}; 
                    border-radius: 8px; 
                    padding: 15px; 
                    margin: 10px 0;">
            <div style="display: flex; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 24px; margin-right: 10px;">{colors['icon']}</span>
                <h4 style="margin: 0; color: {colors['border']};">Priority {priority}: {title}</h4>
            </div>
            <table style="width: 100%; border: none;">
                <tr>
                    <td style="width: 20%; border: none; vertical-align: top;"><strong>Problem:</strong></td>
                    <td style="border: none;">{problem}</td>
                </tr>
                <tr>
                    <td style="border: none; vertical-align: top;"><strong>Current State:</strong></td>
                    <td style="border: none;">{current_state}</td>
                </tr>
                <tr>
                    <td style="border: none; vertical-align: top;"><strong>Recommendation:</strong></td>
                    <td style="border: none; color: {colors['border']}; font-weight: bold;">{recommendation}</td>
                </tr>
                <tr>
                    <td style="border: none; vertical-align: top;"><strong>Expected Impact:</strong></td>
                    <td style="border: none;">{expected_impact}</td>
                </tr>
            </table>
        </div>
    """, unsafe_allow_html=True)


def generate_risk_recommendations(current_allocation: Dict[str, float],
                                  concentration_data: Optional[Dict] = None,
                                  liquidity_data: Optional[Dict] = None) -> List[Dict]:
    """Generate risk-based recommendations."""
    
    recommendations = []
    
    # Check concentration risk
    if concentration_data:
        max_conc = concentration_data.get('max_scheme_concentration', 0)
        if max_conc > 0.20:
            recommendations.append({
                'priority': 1,
                'title': 'High Concentration Risk',
                'problem': 'Single scheme exceeds 20% of portfolio',
                'current_state': f"Largest holding: {max_conc*100:.1f}% of portfolio",
                'recommendation': 'Reduce largest position to under 15% through systematic transfer',
                'expected_impact': 'Lower portfolio volatility and reduce single-point-of-failure risk',
                'color': 'red'
            })
        elif max_conc > 0.15:
            recommendations.append({
                'priority': 2,
                'title': 'Moderate Concentration',
                'problem': 'Single scheme approaching concentration limit',
                'current_state': f"Largest holding: {max_conc*100:.1f}% of portfolio",
                'recommendation': 'Monitor position size and set alert at 20% threshold',
                'expected_impact': 'Maintain diversification discipline',
                'color': 'yellow'
            })
    
    # Check liquidity risk
    if liquidity_data:
        illiquid_pct = liquidity_data.get('illiquid_allocation', 0)
        if illiquid_pct > 0.25:
            recommendations.append({
                'priority': 1,
                'title': 'Liquidity Risk',
                'problem': 'High allocation to illiquid assets (ELSS, locked-in schemes)',
                'current_state': f"Illiquid allocation: {illiquid_pct*100:.1f}%",
                'recommendation': 'Build emergency buffer in liquid funds before further ELSS investment',
                'expected_impact': 'Ensure 3-6 months expenses accessible without exit penalties',
                'color': 'red'
            })
    
    # Check asset allocation drift
    drift = calculate_drift(current_allocation, {'equity': 60, 'debt': 35, 'gold': 3, 'cash': 2})
    max_drift = max(abs(d) for d in drift.values())
    
    if max_drift > 15:
        recommendations.append({
            'priority': 1,
            'title': 'Critical Asset Allocation Drift',
            'problem': 'Portfolio severely misaligned with age-appropriate allocation',
            'current_state': f"Maximum drift: {max_drift:.1f}% from target",
            'recommendation': 'Execute immediate rebalancing to align with glide path',
            'expected_impact': 'Reduce risk exposure appropriate for age 35',
            'color': 'red'
        })
    elif max_drift > 10:
        recommendations.append({
            'priority': 2,
            'title': 'Asset Allocation Drift',
            'problem': 'Portfolio allocation deviating from target',
            'current_state': f"Maximum drift: {max_drift:.1f}% from target",
            'recommendation': 'Plan rebalancing trades within next 30 days',
            'expected_impact': 'Maintain risk profile aligned with investment horizon',
            'color': 'yellow'
        })
    
    return recommendations


def generate_tax_recommendations(holdings_df: pd.DataFrame) -> List[Dict]:
    """Generate tax optimization recommendations."""
    
    recommendations = []
    
    if holdings_df is None or holdings_df.empty:
        return recommendations
    
    # Classify gains
    df = classify_gains(holdings_df)
    
    # Check for tax loss harvesting opportunities
    harvest_opps = identify_harvest_opportunities(df)
    
    if not harvest_opps.empty:
        total_harvest = harvest_opps['harvest_value'].sum()
        potential_savings = harvest_opps['potential_tax_savings'].sum()
        
        recommendations.append({
            'priority': 2,
            'title': 'Tax Loss Harvesting Opportunity',
            'problem': f"₹{total_harvest:,.2f} in unrealized losses available for harvesting",
            'current_state': f"Potential tax savings: ₹{potential_savings:,.2f}",
            'recommendation': 'Sell loss positions before March 31st, reinvest in similar funds after 1 month',
            'expected_impact': f"Save ₹{potential_savings:,.2f} in taxes; maintain market exposure",
            'color': 'yellow'
        })
    
    # Check for STCG exposure
    stcg_positions = df[df['gain_type'] == 'STCG']
    stcg_gains = stcg_positions[stcg_positions['unrealized_gain'] > 0]['unrealized_gain'].sum()
    
    if stcg_gains > 100000:
        tax_liability = stcg_gains * 0.20  # 20% STCG rate
        recommendations.append({
            'priority': 1 if tax_liability > 50000 else 2,
            'title': 'High STCG Tax Exposure',
            'problem': 'Significant short-term gains subject to 20% tax',
            'current_state': f"Unrealized STCG: ₹{stcg_gains:,.2f} (Tax: ₹{tax_liability:,.2f})",
            'recommendation': 'Hold positions until LTCG eligible (>1 year) or harvest losses to offset',
            'expected_impact': f"Potential tax savings: ₹{tax_liability:,.2f}",
            'color': 'red' if tax_liability > 50000 else 'yellow'
        })
    
    # Check for cash drag
    cash_pct = (holdings_df[holdings_df.get('scheme_type', '').str.upper() == 'CASH']['current_value'].sum() / 
                holdings_df['current_value'].sum()) * 100
    
    if cash_pct > 10:
        recommendations.append({
            'priority': 2,
            'title': 'Cash Drag',
            'problem': 'Excess cash earning sub-optimal returns',
            'current_state': f"Cash allocation: {cash_pct:.1f}% (Target: 2%)",
            'recommendation': 'Deploy excess cash to liquid funds or STP to equity over 3-6 months',
            'expected_impact': 'Improve returns by 4-6% annually on idle cash',
            'color': 'yellow'
        })
    
    return recommendations


def generate_diversification_recommendations(current_allocation: Dict[str, float],
                                             holdings_df: Optional[pd.DataFrame] = None) -> List[Dict]:
    """Generate diversification recommendations."""
    
    recommendations = []
    
    # Check equity sub-allocation
    equity_pct = current_allocation.get('equity', 0)
    
    if equity_pct > 0 and holdings_df is not None:
        # Check for adequate debt allocation
        debt_pct = current_allocation.get('debt', 0)
        
        if debt_pct < 20 and equity_pct > 70:
            recommendations.append({
                'priority': 2,
                'title': 'Debt Allocation Below Recommended',
                'problem': 'Low debt allocation increases portfolio volatility',
                'current_state': f"Debt: {debt_pct:.1f}% vs Target: 35%",
                'recommendation': 'Increase debt allocation through SIP in corporate bond or gilt funds',
                'expected_impact': 'Reduce portfolio volatility by 3-5%, improve Sharpe ratio',
                'color': 'yellow'
            })
    
    # Check gold allocation
    gold_pct = current_allocation.get('gold', 0)
    if gold_pct < 3:
        recommendations.append({
            'priority': 3,
            'title': 'Consider Gold Allocation',
            'problem': 'Portfolio lacks inflation hedge and diversification through gold',
            'current_state': f"Gold: {gold_pct:.1f}% vs Recommended: 5%",
            'recommendation': 'Add 2-5% gold allocation via Gold ETF or Sovereign Gold Bonds',
            'expected_impact': 'Portfolio diversification, inflation protection, reduced correlation',
            'color': 'green'
        })
    
    # Goal alignment check
    if equity_pct > 70:
        recommendations.append({
            'priority': 3,
            'title': 'Goal-Based Allocation Review',
            'problem': 'Verify equity allocation aligns with goal timelines',
            'current_state': f"Current equity: {equity_pct:.1f}%",
            'recommendation': 'Map portfolio to goals: <3Y goals → Debt; 3-7Y → Hybrid; >7Y → Equity',
            'expected_impact': 'Reduce goal-specific risk through appropriate asset-liability matching',
            'color': 'green'
        })
    
    return recommendations


def render_recommendations(current_allocation: Dict[str, float] = None,
                          holdings_df: Optional[pd.DataFrame] = None,
                          concentration_data: Optional[Dict] = None,
                          liquidity_data: Optional[Dict] = None):
    """
    Main function to render the recommendations panel.
    
    Args:
        current_allocation: Current asset allocation
        holdings_df: Holdings DataFrame
        concentration_data: Concentration metrics
        liquidity_data: Liquidity metrics
    """
    
    st.header("📋 Action Recommendations")
    
    # Default allocation if not provided
    if current_allocation is None:
        current_allocation = {
            'equity': 68,
            'debt': 25,
            'gold': 4,
            'cash': 3
        }
    
    # Generate all recommendations
    all_recommendations = []
    
    # Risk-based recommendations
    all_recommendations.extend(
        generate_risk_recommendations(current_allocation, concentration_data, liquidity_data)
    )
    
    # Tax recommendations
    if holdings_df is not None:
        all_recommendations.extend(
            generate_tax_recommendations(holdings_df)
        )
    
    # Diversification recommendations
    all_recommendations.extend(
        generate_diversification_recommendations(current_allocation, holdings_df)
    )
    
    # Sort by priority
    all_recommendations.sort(key=lambda x: x['priority'])
    
    # Count by priority
    p1_count = sum(1 for r in all_recommendations if r['priority'] == 1)
    p2_count = sum(1 for r in all_recommendations if r['priority'] == 2)
    p3_count = sum(1 for r in all_recommendations if r['priority'] == 3)
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("🔴 Critical", p1_count)
    with col2:
        st.metric("🟠 Optimization", p2_count)
    with col3:
        st.metric("🟢 Best Practice", p3_count)
    
    st.divider()
    
    # Render recommendations by priority
    
    # Priority 1 - Critical
    if p1_count > 0:
        st.subheader("🔴 Priority 1: Critical Actions")
        st.markdown("*Address these risks immediately to protect your portfolio*")
        
        for rec in all_recommendations:
            if rec['priority'] == 1:
                create_priority_card(
                    rec['priority'], rec['title'], rec['problem'],
                    rec['current_state'], rec['recommendation'],
                    rec['expected_impact'], rec['color']
                )
    else:
        st.success("✅ No critical risks detected in your portfolio!")
    
    st.divider()
    
    # Priority 2 - Optimization
    if p2_count > 0:
        st.subheader("🟡 Priority 2: Optimization Opportunities")
        st.markdown("*Implement these to improve tax efficiency and returns*")
        
        for rec in all_recommendations:
            if rec['priority'] == 2:
                create_priority_card(
                    rec['priority'], rec['title'], rec['problem'],
                    rec['current_state'], rec['recommendation'],
                    rec['expected_impact'], rec['color']
                )
    else:
        st.info("ℹ️ No immediate optimization opportunities")
    
    st.divider()
    
    # Priority 3 - Best Practices
    if p3_count > 0:
        st.subheader("🟢 Priority 3: Good Practices")
        st.markdown("*Consider these for long-term portfolio health*")
        
        for rec in all_recommendations:
            if rec['priority'] == 3:
                create_priority_card(
                    rec['priority'], rec['title'], rec['problem'],
                    rec['current_state'], rec['recommendation'],
                    rec['expected_impact'], rec['color']
                )
    
    # Action tracker
    with st.expander("📊 Your Action Tracker"):
        st.markdown("""
        **This Week:**
        - [ ] Review critical risk alerts
        - [ ] Check rebalancing requirements
        
        **This Month:**
        - [ ] Execute tax loss harvesting (if applicable)
        - [ ] Review and rebalance if drift > 10%
        
        **This Quarter:**
        - [ ] Full portfolio health check
        - [ ] Goal-alignment review
        - [ ] Tax efficiency assessment
        """)
    
    # Tax season reminder
    today = datetime.now()
    if today.month in [1, 2, 3]:  # Jan, Feb, Mar
        st.warning("📅 **Tax Season Reminder**: March 31st deadline approaching! Review tax loss harvesting opportunities.")
