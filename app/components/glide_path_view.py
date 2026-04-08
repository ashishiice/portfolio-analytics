"""
Glide Path View Component
Streamlit component for displaying age-based asset allocation and drift analysis.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from typing import Dict, Optional

# Import utils
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent.parent))
from utils.glide_path import (
    get_target_allocation, calculate_drift, get_glide_path_projection,
    check_rebalancing_needed, get_rebalancing_urgency, aggregate_allocation_by_asset_class
)
from utils.rebalancer import calculate_rebalancing_trades, calculate_drift_matrix


def render_allocation_comparison(current_allocation: Dict[str, float],
                                target_allocation: Dict[str, float]):
    """Render side-by-side allocation comparison bars."""
    
    assets = ['equity', 'debt', 'gold', 'cash']
    
    # Prepare data
    current_vals = [current_allocation.get(a, 0) for a in assets]
    target_vals = [target_allocation.get(a, 0) for a in assets]
    
    fig = go.Figure()
    
    # Current allocation bars
    fig.add_trace(go.Bar(
        name='Current',
        x=assets,
        y=current_vals,
        marker_color=['#3498db', '#2ecc71', '#f1c40f', '#95a5a6'],
        text=[f'{v:.1f}%' for v in current_vals],
        textposition='auto',
    ))
    
    # Target allocation bars
    fig.add_trace(go.Bar(
        name='Target',
        x=assets,
        y=target_vals,
        marker_color=['#3498db', '#2ecc71', '#f1c40f', '#95a5a6'],
        marker_opacity=0.5,
        text=[f'{v:.1f}%' for v in target_vals],
        textposition='auto',
    ))
    
    fig.update_layout(
        title="Current vs Target Asset Allocation",
        xaxis_title="Asset Class",
        yaxis_title="Allocation (%)",
        barmode='group',
        height=400,
        yaxis=dict(range=[0, max(max(current_vals), max(target_vals)) * 1.2]),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_drift_indicators(current_allocation: Dict[str, float],
                           target_allocation: Dict[str, float]):
    """Render drift indicators with color coding."""
    
    st.subheader("Allocation Drift Analysis")
    
    drift = calculate_drift(current_allocation, target_allocation)
    
    # Create drift visualization
    assets = ['equity', 'debt', 'gold', 'cash']
    
    cols = st.columns(4)
    
    for i, asset in enumerate(assets):
        with cols[i]:
            current = current_allocation.get(asset, 0)
            target = target_allocation.get(asset, 0)
            drift_val = drift.get(asset, 0)
            
            # Determine color and status
            if abs(drift_val) > 10:
                color = '#e74c3c'  # Red - Critical
                status = '🔴'
            elif abs(drift_val) > 5:
                color = '#f39c12'  # Orange - Warning
                status = '🟠'
            elif abs(drift_val) > 2:
                color = '#f1c40f'  # Yellow - Attention
                status = '🟡'
            else:
                color = '#27ae60'  # Green - Optimal
                status = '🟢'
            
            st.markdown(f"""
                <div style="border: 2px solid {color}; border-radius: 10px; padding: 15px; text-align: center;">
                    <h3 style="margin: 0; color: {color};">{asset.upper()}</h3>
                    <p style="font-size: 24px; margin: 10px 0; color: {color};">{status}</p>
                    <p style="margin: 5px 0;">Current: <strong>{current:.1f}%</strong></p>
                    <p style="margin: 5px 0;">Target: <strong>{target:.1f}%</strong></p>
                    <p style="margin: 5px 0; color: {color};">Drift: <strong>{drift_val:+.1f}%</strong></p>
                </div>
            """, unsafe_allow_html=True)


def render_glide_path_projection(current_age: int, final_age: int = 60):
    """Render year-by-year glide path projection chart."""
    
    st.subheader("Glide Path Projection")
    
    # Get projection data
    projection_df = get_glide_path_projection(current_age, final_age)
    
    if projection_df.empty:
        st.warning("Unable to generate glide path projection")
        return
    
    # Create stacked area chart
    fig = go.Figure()
    
    colors = {
        'equity': '#3498db',
        'debt': '#2ecc71', 
        'gold': '#f1c40f',
        'cash': '#95a5a6'
    }
    
    for asset in ['cash', 'gold', 'debt', 'equity']:  # Reverse order for proper stacking
        fig.add_trace(go.Scatter(
            x=projection_df['age'],
            y=projection_df[asset],
            mode='lines',
            stackgroup='one',
            name=asset.upper(),
            line=dict(width=0.5, color=colors[asset]),
            fillcolor=colors[asset]
        ))
    
    # Add current age marker
    fig.add_vline(x=current_age, line_dash="dash", line_color="#e74c3c", 
                  annotation_text="Current Age", annotation_position="top")
    
    fig.update_layout(
        title="Asset Allocation Glide Path (Age-based)",
        xaxis_title="Age",
        yaxis_title="Allocation (%)",
        yaxis=dict(range=[0, 100]),
        hovermode='x unified',
        height=450,
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Show key milestones
    st.markdown("#### Key Milestones")
    
    milestones = []
    for _, row in projection_df.iterrows():
        age = int(row['age'])
        if age % 5 == 0:
            milestones.append({
                'Age': age,
                'Equity': f"{row['equity']:.0f}%",
                'Debt': f"{row['debt']:.0f}%",
                'Gold': f"{row['gold']:.0f}%",
                'Cash': f"{row['cash']:.0f}%"
            })
    
    if milestones:
        st.dataframe(pd.DataFrame(milestones), hide_index=True, use_container_width=True)


def render_rebalancing_calculator(current_holdings_df: pd.DataFrame,
                                 target_allocation: Dict[str, float],
                                 total_aum: Optional[float] = None):
    """Render rebalancing calculator output."""
    
    st.subheader("Rebalancing Calculator")
    
    if current_holdings_df is None or current_holdings_df.empty:
        st.warning("No holdings data available for rebalancing calculation")
        return
    
    # Calculate rebalancing trades
    trades_df = calculate_rebalancing_trades(current_holdings_df, target_allocation, total_aum)
    
    if trades_df.empty:
        st.info("No rebalancing trades required")
        return
    
    # Filter to only show actions needed
    action_trades = trades_df[trades_df['action'] != 'HOLD']
    
    if action_trades.empty:
        st.success("✅ Portfolio is well-balanced! No trades required.")
        return
    
    # Display trades by action type
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📈 Buy Orders")
        buy_trades = action_trades[action_trades['action'] == 'BUY']
        if not buy_trades.empty:
            buy_total = buy_trades['amount'].sum()
            st.metric("Total Buy Amount", f"₹{buy_total:,.2f}")
            
            for _, trade in buy_trades.iterrows():
                with st.container():
                    st.markdown(f"""
                        <div style="background-color: #d5f5e3; padding: 10px; border-radius: 5px; margin: 5px 0;">
                            <strong>{trade['scheme']}</strong><br>
                            Amount: ₹{trade['amount']:,.2f} | 
                            Target %: {trade['target_pct']:.1f}%
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No buy orders required")
    
    with col2:
        st.markdown("#### 📉 Sell Orders")
        sell_trades = action_trades[action_trades['action'] == 'SELL']
        if not sell_trades.empty:
            sell_total = sell_trades['amount'].sum()
            st.metric("Total Sell Amount", f"₹{sell_total:,.2f}")
            
            for _, trade in sell_trades.iterrows():
                with st.container():
                    st.markdown(f"""
                        <div style="background-color: #fadbd8; padding: 10px; border-radius: 5px; margin: 5px 0;">
                            <strong>{trade['scheme']}</strong><br>
                            Amount: ₹{trade['amount']:,.2f} | 
                            Current %: {trade['current_pct']:.1f}%
                        </div>
                    """, unsafe_allow_html=True)
        else:
            st.info("No sell orders required")
    
    # Show full trades table
    with st.expander("View Complete Trade Details"):
        st.dataframe(
            trades_df[['scheme', 'asset_class', 'current_pct', 'target_pct', 'action', 'amount']],
            hide_index=True,
            use_container_width=True
        )
    
    # Cost estimation
    st.markdown("#### 💰 Estimated Transaction Costs")
    
    from utils.rebalancer import simulate_rebalancing_cost
    costs = simulate_rebalancing_cost(action_trades)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Exit Load", f"₹{costs['exit_load']:,.2f}")
    with col2:
        st.metric("STT", f"₹{costs['stt']:,.2f}")
    with col3:
        st.metric("Stamp Duty", f"₹{costs['stamp_duty']:,.2f}")
    with col4:
        st.metric("Total Cost", f"₹{costs['total_cost']:,.2f}")


def render_rebalancing_status(current_allocation: Dict[str, float],
                             target_allocation: Dict[str, float]):
    """Render rebalancing status indicator."""
    
    urgency = get_rebalancing_urgency(current_allocation, target_allocation)
    
    urgency_level = urgency.get('urgency', 'Low')
    action_required = urgency.get('action_required', 'None')
    max_deviation = urgency.get('max_deviation', 0)
    
    if urgency_level == 'High':
        color = '#e74c3c'
        icon = '🔴'
        bg_color = '#fadbd8'
    elif urgency_level == 'Medium':
        color = '#f39c12'
        icon = '🟠'
        bg_color = '#fdebd0'
    else:
        color = '#27ae60'
        icon = '🟢'
        bg_color = '#d5f5e3'
    
    st.markdown(f"""
        <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; 
                    border-left: 5px solid {color}; margin: 20px 0;">
            <h3 style="color: {color}; margin: 0;">{icon} Rebalancing Status: {urgency_level}</h3>
            <p style="color: #2c3e50; margin: 10px 0;">
                Action Required: <strong>{action_required}</strong><br>
                Maximum Deviation: <strong>{max_deviation:.1f}%</strong>
            </p>
        </div>
    """, unsafe_allow_html=True)


def render_glide_path_view(current_age: int = 35,
                          current_holdings_df: Optional[pd.DataFrame] = None,
                          total_aum: Optional[float] = None):
    """
    Main function to render the complete glide path view.
    
    Args:
        current_age: Current age of investor
        current_holdings_df: DataFrame with current holdings
        total_aum: Total portfolio value
    """
    st.header("🎯 Glide Path & Asset Allocation")
    
    # Get target allocation
    target_allocation = get_target_allocation(current_age)
    
    # Calculate current allocation from holdings if available
    if current_holdings_df is not None and not current_holdings_df.empty:
        current_allocation = aggregate_allocation_by_asset_class(current_holdings_df)
        if total_aum is None:
            total_aum = current_holdings_df['current_value'].sum()
    else:
        # Use example allocation
        current_allocation = {
            'equity': 68,
            'debt': 25,
            'gold': 4,
            'cash': 3
        }
        if total_aum is None:
            total_aum = 1000000  # Example: ₹10L
    
    # Rebalancing Status
    render_rebalancing_status(current_allocation, target_allocation)
    
    st.divider()
    
    # Allocation Comparison
    render_allocation_comparison(current_allocation, target_allocation)
    
    st.divider()
    
    # Drift Indicators
    render_drift_indicators(current_allocation, target_allocation)
    
    st.divider()
    
    # Glide Path Projection
    render_glide_path_projection(current_age, final_age=60)
    
    st.divider()
    
    # Rebalancing Calculator
    if current_holdings_df is not None and not current_holdings_df.empty:
        # Create sample holdings if not provided properly
        if 'scheme' not in current_holdings_df.columns:
            sample_holdings = pd.DataFrame([
                {'scheme': 'Large Cap Fund', 'scheme_type': 'Equity', 'scheme_category': 'Large Cap', 'current_value': total_aum * 0.30},
                {'scheme': 'Mid Cap Fund', 'scheme_type': 'Equity', 'scheme_category': 'Mid Cap', 'current_value': total_aum * 0.25},
                {'scheme': 'Small Cap Fund', 'scheme_type': 'Equity', 'scheme_category': 'Small Cap', 'current_value': total_aum * 0.13},
                {'scheme': 'Corporate Bond Fund', 'scheme_type': 'Debt', 'scheme_category': 'Corporate Bond', 'current_value': total_aum * 0.15},
                {'scheme': 'Gilt Fund', 'scheme_type': 'Debt', 'scheme_category': 'Gilt', 'current_value': total_aum * 0.10},
                {'scheme': 'Gold ETF', 'scheme_type': 'Gold', 'scheme_category': 'Gold ETF', 'current_value': total_aum * 0.04},
                {'scheme': 'Liquid Fund', 'scheme_type': 'Cash', 'scheme_category': 'Liquid', 'current_value': total_aum * 0.03},
            ])
            render_rebalancing_calculator(sample_holdings, target_allocation, total_aum)
        else:
            render_rebalancing_calculator(current_holdings_df, target_allocation, total_aum)
    else:
        # Show with sample data
        st.info("Using sample portfolio data. Connect your portfolio for personalized rebalancing.")
        sample_holdings = pd.DataFrame([
            {'scheme': 'Large Cap Fund', 'scheme_type': 'Equity', 'scheme_category': 'Large Cap', 'current_value': total_aum * 0.30},
            {'scheme': 'Mid Cap Fund', 'scheme_type': 'Equity', 'scheme_category': 'Mid Cap', 'current_value': total_aum * 0.25},
            {'scheme': 'Small Cap Fund', 'scheme_type': 'Equity', 'scheme_category': 'Small Cap', 'current_value': total_aum * 0.13},
            {'scheme': 'Corporate Bond Fund', 'scheme_type': 'Debt', 'scheme_category': 'Corporate Bond', 'current_value': total_aum * 0.15},
            {'scheme': 'Gilt Fund', 'scheme_type': 'Debt', 'scheme_category': 'Gilt', 'current_value': total_aum * 0.10},
            {'scheme': 'Gold ETF', 'scheme_type': 'Gold', 'scheme_category': 'Gold ETF', 'current_value': total_aum * 0.04},
            {'scheme': 'Liquid Fund', 'scheme_type': 'Cash', 'scheme_category': 'Liquid', 'current_value': total_aum * 0.03},
        ])
        render_rebalancing_calculator(sample_holdings, target_allocation, total_aum)
    
    # User settings
    with st.expander("⚙️ User Settings"):
        st.markdown("""
        **Current Profile Settings:**
        - Age: 35 years
        - Risk Profile: Moderate-Aggressive
        - Target Equity: 60%
        - Retirement Age: 60
        
        *Note: Adjust profile in Settings tab to see personalized glide path.*
        """)
