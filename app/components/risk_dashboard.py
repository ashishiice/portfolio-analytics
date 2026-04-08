"""
Risk Dashboard Component
Streamlit component for displaying portfolio risk metrics and visualizations.
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
from utils.risk_metrics import (
    portfolio_volatility, sharpe_ratio, max_drawdown, 
    rolling_returns, benchmark_deviation, calculate_risk_score,
    get_drawdown_series
)


def render_risk_score_card(risk_score: Dict):
    """Render the overall risk score card."""
    score = risk_score.get('risk_score', 50)
    level = risk_score.get('risk_level', 'Moderate')
    components = risk_score.get('components', {})
    
    # Determine color based on score
    if score >= 70:
        color = '#e74c3c'  # Red
        bg_color = '#fadbd8'
    elif score >= 45:
        color = '#f39c12'  # Orange
        bg_color = '#fdebd0'
    elif score >= 25:
        color = '#f1c40f'  # Yellow
        bg_color = '#fcf3cf'
    else:
        color = '#27ae60'  # Green
        bg_color = '#d5f5e3'
    
    st.markdown(f"""
        <div style="background-color: {bg_color}; padding: 20px; border-radius: 10px; 
                    border-left: 5px solid {color}; margin-bottom: 20px;">
            <h2 style="color: {color}; margin: 0;">Risk Score: {score}/100</h2>
            <h4 style="color: #2c3e50; margin: 10px 0;">{level} Risk Level</h4>
        </div>
    """, unsafe_allow_html=True)
    
    # Risk components breakdown
    st.subheader("Risk Components")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        vol_score = components.get('volatility', 15)
        st.metric("Volatility", f"{vol_score}/35")
    with col2:
        conc_score = components.get('concentration', 15)
        st.metric("Concentration", f"{conc_score}/30")
    with col3:
        liq_score = components.get('liquidity', 10)
        st.metric("Liquidity", f"{liq_score}/20")
    with col4:
        dd_score = components.get('drawdown', 7)
        st.metric("Drawdown", f"{dd_score}/15")


def render_drawdown_chart(nav_history_df: pd.DataFrame):
    """Render drawdown chart using Plotly."""
    if nav_history_df is None or nav_history_df.empty:
        st.warning("No NAV history data available for drawdown analysis")
        return
    
    # Get drawdown series
    dd_series = get_drawdown_series(nav_history_df)
    
    if dd_series.empty:
        st.warning("Unable to calculate drawdown")
        return
    
    fig = go.Figure()
    
    # Add drawdown area
    fig.add_trace(go.Scatter(
        x=dd_series.index,
        y=dd_series['drawdown_pct'],
        fill='tozeroy',
        name='Drawdown %',
        line=dict(color='#e74c3c', width=1),
        fillcolor='rgba(231, 76, 60, 0.3)'
    ))
    
    # Add zero line
    fig.add_hline(y=0, line_dash="solid", line_color="#2c3e50", line_width=2)
    
    # Update layout
    fig.update_layout(
        title="Portfolio Drawdown History",
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        hovermode='x unified',
        showlegend=False,
        height=400,
        yaxis=dict(tickformat='.1f', ticksuffix='%'),
        plot_bgcolor='white'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Drawdown statistics
    max_dd = dd_series['drawdown_pct'].min()
    avg_dd = dd_series[dd_series['drawdown_pct'] < 0]['drawdown_pct'].mean()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Maximum Drawdown", f"{max_dd:.2f}%", delta_color="inverse")
    with col2:
        st.metric("Average Drawdown", f"{avg_dd:.2f}%" if not np.isnan(avg_dd) else "N/A", delta_color="inverse")
    with col3:
        current_dd = dd_series['drawdown_pct'].iloc[-1]
        st.metric("Current Drawdown", f"{current_dd:.2f}%", delta_color="inverse")


def render_rolling_returns_chart(nav_history_df: pd.DataFrame, 
                                 nifty_returns: Optional[pd.Series] = None):
    """Render rolling returns comparison chart."""
    if nav_history_df is None or nav_history_df.empty:
        st.warning("No NAV history available")
        return
    
    # Calculate rolling returns
    rolling_rets = rolling_returns(nav_history_df, windows=[1, 3, 5])
    
    if rolling_rets.empty:
        st.warning("Insufficient data for rolling returns calculation")
        return
    
    fig = make_subplots(
        rows=3, cols=1,
        subplot_titles=('1-Year Rolling Returns', '3-Year Rolling Returns', '5-Year Rolling Returns'),
        vertical_spacing=0.08
    )
    
    colors = {'1Y': '#3498db', '3Y': '#2ecc71', '5Y': '#9b59b6'}
    
    for i, window in enumerate(['1Y', '3Y', '5Y'], 1):
        if window in rolling_rets.columns:
            fig.add_trace(
                go.Scatter(
                    x=rolling_rets.index,
                    y=rolling_rets[window],
                    mode='lines',
                    name=f'{window} Returns',
                    line=dict(color=colors[window], width=2),
                    showlegend=(i == 1)
                ),
                row=i, col=1
            )
            
            # Add zero line
            fig.add_hline(y=0, line_dash="dash", line_color="#95a5a6", 
                         line_width=1, row=i, col=1)
    
    fig.update_layout(
        height=600,
        showlegend=True,
        title_text="Rolling Returns Analysis",
        hovermode='x unified'
    )
    
    # Update y-axes to show percentage
    for i in range(1, 4):
        fig.update_yaxes(ticksuffix='%', row=i, col=1)
    
    st.plotly_chart(fig, use_container_width=True)


def render_benchmark_deviation_chart(portfolio_returns: pd.Series,
                                    nifty_returns: pd.Series):
    """Render benchmark deviation chart."""
    if portfolio_returns is None or nifty_returns is None:
        st.warning("Returns data not available for benchmark comparison")
        return
    
    # Align series
    aligned = pd.concat([portfolio_returns, nifty_returns], axis=1).dropna()
    
    if aligned.empty:
        st.warning("No overlapping data between portfolio and benchmark")
        return
    
    port_rets = aligned.iloc[:, 0]
    bench_rets = aligned.iloc[:, 1]
    
    # Calculate cumulative returns
    port_cum = (1 + port_rets).cumprod() - 1
    bench_cum = (1 + bench_rets).cumprod() - 1
    
    # Calculate alpha
    deviation = port_cum - bench_cum
    
    fig = go.Figure()
    
    # Add portfolio and benchmark lines
    fig.add_trace(go.Scatter(
        x=port_cum.index,
        y=port_cum * 100,
        name='Portfolio',
        line=dict(color='#3498db', width=2)
    ))
    
    fig.add_trace(go.Scatter(
        x=bench_cum.index,
        y=bench_cum * 100,
        name='Nifty 50',
        line=dict(color='#e74c3c', width=2, dash='dash')
    ))
    
    # Update layout
    fig.update_layout(
        title="Portfolio vs Nifty 50 - Cumulative Returns",
        xaxis_title="Date",
        yaxis_title="Cumulative Return (%)",
        hovermode='x unified',
        height=400,
        yaxis=dict(tickformat='.1f', ticksuffix='%'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Calculate and display alpha metrics
    metrics = benchmark_deviation(port_rets, bench_rets)
    
    st.subheader("Benchmark Deviation Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        alpha = metrics.get('alpha', 0)
        delta_color = "normal" if alpha >= 0 else "inverse"
        st.metric("Alpha", f"{alpha:.2f}%", delta_color=delta_color)
    with col2:
        beta = metrics.get('beta', 1)
        st.metric("Beta", f"{beta:.2f}")
    with col3:
        tracking_error = metrics.get('tracking_error', 0)
        st.metric("Tracking Error", f"{tracking_error:.2f}%")
    with col4:
        info_ratio = metrics.get('information_ratio', 0)
        st.metric("Information Ratio", f"{info_ratio:.2f}")


def render_risk_dashboard(nav_history_df: Optional[pd.DataFrame] = None,
                         portfolio_returns: Optional[pd.Series] = None,
                         nifty_returns: Optional[pd.Series] = None,
                         concentration_data: Optional[Dict] = None,
                         liquidity_data: Optional[Dict] = None):
    """
    Main function to render the complete risk dashboard.
    
    Args:
        nav_history_df: DataFrame with NAV history
        portfolio_returns: Series with portfolio returns
        nifty_returns: Series with Nifty 50 returns
        concentration_data: Dict with concentration metrics
        liquidity_data: Dict with liquidity metrics
    """
    st.header("📊 Risk Dashboard")
    
    # Risk Score Section
    st.subheader("Portfolio Risk Assessment")
    
    if nav_history_df is not None and not nav_history_df.empty:
        risk_score = calculate_risk_score(
            nav_history_df, 
            concentration_data=concentration_data,
            liquidity_data=liquidity_data
        )
        render_risk_score_card(risk_score)
    else:
        st.warning("⚠️ NAV history data not available. Risk score based on portfolio composition only.")
        # Show placeholder risk score based on available data
        placeholder_score = {
            'risk_score': 45,
            'risk_level': 'Moderate (Estimated)',
            'components': {
                'volatility': 15,
                'concentration': 15,
                'liquidity': 10,
                'drawdown': 5
            }
        }
        render_risk_score_card(placeholder_score)
    
    st.divider()
    
    # Drawdown Chart
    st.subheader("Drawdown Analysis")
    if nav_history_df is not None and not nav_history_df.empty:
        render_drawdown_chart(nav_history_df)
    else:
        st.info("Historical NAV data required for drawdown analysis. ")
        st.info("Connect to CAS data or import portfolio to enable this feature.")
    
    st.divider()
    
    # Rolling Returns
    st.subheader("Rolling Returns")
    if nav_history_df is not None and not nav_history_df.empty:
        render_rolling_returns_chart(nav_history_df, nifty_returns)
    else:
        st.info("Historical NAV data required for rolling returns analysis.")
    
    st.divider()
    
    # Benchmark Deviation
    st.subheader("Benchmark Comparison (vs Nifty 50)")
    if portfolio_returns is not None and nifty_returns is not None:
        render_benchmark_deviation_chart(portfolio_returns, nifty_returns)
    else:
        st.info("Portfolio and benchmark returns data required for comparison.")
    
    # Additional Risk Metrics
    st.divider()
    st.subheader("Key Risk Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if nav_history_df is not None and not nav_history_df.empty:
            vol = portfolio_volatility(nav_history_df)
            st.metric("Annualized Volatility", f"{vol*100:.2f}%" if not np.isnan(vol) else "N/A")
        else:
            st.metric("Annualized Volatility", "N/A")
    
    with col2:
        if portfolio_returns is not None and len(portfolio_returns) > 0:
            sharpe = sharpe_ratio(portfolio_returns.dropna())
            st.metric("Sharpe Ratio", f"{sharpe:.2f}" if not np.isnan(sharpe) else "N/A")
        else:
            st.metric("Sharpe Ratio", "N/A")
    
    with col3:
        if nav_history_df is not None and not nav_history_df.empty:
            dd_info = max_drawdown(nav_history_df)
            st.metric("Max Drawdown", f"{dd_info['max_drawdown_pct']:.2f}%", delta_color="inverse")
        else:
            st.metric("Max Drawdown", "N/A")
    
    with col4:
        st.metric("Risk-Free Rate", "6.00%")
    
    # Risk Explanations
    with st.expander("📖 Understanding Risk Metrics"):
        st.markdown("""
        **Risk Score (0-100)**: Composite measure based on:
        - Volatility (35%): Standard deviation of returns
        - Concentration (30%): Single scheme/category exposure
        - Liquidity (20%): % in illiquid assets
        - Drawdown (15%): Historical peak-to-trough decline
        
        **Sharpe Ratio**: Risk-adjusted return. Higher is better. >1 is good, >2 is excellent.
        
        **Max Drawdown**: Largest decline from peak to trough. Lower is better.
        
        **Alpha**: Excess return vs benchmark. Positive means outperforming.
        
        **Beta**: Sensitivity to market movements. 1 = market average, <1 = less volatile.
        """)
