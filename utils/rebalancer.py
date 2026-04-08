"""
Rebalancer Module
Calculates rebalancing trades and generates rebalancing reports.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime


def calculate_rebalancing_trades(current_holdings_df: pd.DataFrame,
                                target_allocation: Dict[str, float],
                                total_aum: Optional[float] = None) -> pd.DataFrame:
    """
    Calculate rebalancing trades needed to reach target allocation.
    
    Args:
        current_holdings_df: DataFrame with columns [scheme, scheme_type, scheme_category, current_value]
        target_allocation: Dictionary with target percentages {equity: 60, debt: 35, ...}
        total_aum: Total AUM (calculated from holdings if not provided)
        
    Returns:
        DataFrame with rebalancing trade details
    """
    if current_holdings_df is None or current_holdings_df.empty:
        return pd.DataFrame()
    
    df = current_holdings_df.copy()
    
    # Calculate total AUM
    if total_aum is None:
        total_aum = df['current_value'].sum()
    
    if total_aum == 0:
        return pd.DataFrame()
    
    # Map schemes to asset classes
    from .glide_path import map_scheme_to_asset_class, load_glide_path_config
    
    config = load_glide_path_config()
    
    df['asset_class'] = df.apply(
        lambda row: map_scheme_to_asset_class(
            row.get('scheme_type', ''), 
            row.get('scheme_category', ''), 
            config
        ), 
        axis=1
    )
    
    # Calculate current percentages
    df['current_pct'] = (df['current_value'] / total_aum) * 100
    
    # Calculate target value and percentage for each scheme
    # Distribute target allocation within each asset class based on current weights
    results = []
    
    for asset_class in ['equity', 'debt', 'gold', 'cash']:
        target_pct = target_allocation.get(asset_class, 0)
        target_value = (target_pct / 100) * total_aum
        
        # Get schemes in this asset class
        asset_schemes = df[df['asset_class'] == asset_class]
        
        if asset_schemes.empty:
            continue
        
        # Calculate current total for this asset class
        current_asset_value = asset_schemes['current_value'].sum()
        current_asset_pct = (current_asset_value / total_aum) * 100
        
        # Calculate allocation adjustment needed
        asset_adjustment = target_value - current_asset_value
        
        # Distribute adjustment among schemes proportionally
        if current_asset_value > 0:
            weights = asset_schemes['current_value'] / current_asset_value
        else:
            weights = pd.Series([1/len(asset_schemes)] * len(asset_schemes), index=asset_schemes.index)
        
        for idx, row in asset_schemes.iterrows():
            scheme_target_value = row['current_value'] + (asset_adjustment * weights[idx])
            scheme_target_pct = (scheme_target_value / total_aum) * 100
            
            trade_value = scheme_target_value - row['current_value']
            
            if trade_value > 0.01:
                action = 'BUY'
            elif trade_value < -0.01:
                action = 'SELL'
            else:
                action = 'HOLD'
                trade_value = 0
            
            results.append({
                'scheme': row.get('scheme', f"Scheme_{idx}"),
                'asset_class': asset_class,
                'current_value': round(row['current_value'], 2),
                'current_pct': round(row['current_pct'], 2),
                'target_pct': round(scheme_target_pct, 2),
                'target_value': round(scheme_target_value, 2),
                'action': action,
                'amount': round(abs(trade_value), 2)
            })
    
    return pd.DataFrame(results)


def optimize_tax_efficient_rebalance(holdings_df: pd.DataFrame,
                                    elss_lockin_df: Optional[pd.DataFrame] = None,
                                    target_allocation: Optional[Dict[str, float]] = None) -> pd.DataFrame:
    """
    Optimize rebalancing to be tax-efficient by avoiding ELSS in lock-in period.
    
    Args:
        holdings_df: Holdings DataFrame
        elss_lockin_df: DataFrame with ELSS lock-in details [scheme, purchase_date, units, lockin_end_date]
        target_allocation: Target allocation percentages
        
    Returns:
        Optimized rebalancing DataFrame
    """
    if holdings_df is None or holdings_df.empty:
        return pd.DataFrame()
    
    df = holdings_df.copy()
    
    # Identify ELSS schemes in lock-in
    if elss_lockin_df is not None and not elss_lockin_df.empty:
        today = datetime.now()
        locked_elss = elss_lockin_df[elss_lockin_df['lockin_end_date'] > today]
        locked_scheme_names = set(locked_elss['scheme'].unique())
    else:
        # Check if scheme_type indicates ELSS
        locked_scheme_names = set(df[df.get('scheme_type', '').str.upper() == 'ELSS']['scheme'].unique())
    
    # Mark schemes as locked
    df['is_locked'] = df['scheme'].isin(locked_scheme_names)
    
    # If target allocation provided, adjust to respect lock-in
    if target_allocation:
        # Calculate available (non-locked) amounts per asset class
        df['asset_class'] = df.apply(
            lambda row: 'equity' if 'ELSS' in str(row.get('scheme_type', '')).upper() 
            or 'EQUITY' in str(row.get('scheme_type', '')).upper() 
            else 'debt',
            axis=1
        )
        
        available_for_trade = df[~df['is_locked']].copy()
        locked_value = df[df['is_locked']]['current_value'].sum()
        
        # Adjust targets to account for locked value
        total_aum = df['current_value'].sum()
        locked_pct = (locked_value / total_aum) * 100 if total_aum > 0 else 0
        
        # Reduce equity target by locked ELSS percentage (since ELSS is equity)
        adjusted_target = target_allocation.copy()
        if locked_pct > 0:
            adjusted_target['equity'] = max(0, adjusted_target.get('equity', 0) - locked_pct)
    else:
        available_for_trade = df.copy()
        adjusted_target = target_allocation
    
    # Calculate rebalancing only on available funds
    if adjusted_target and not available_for_trade.empty:
        trades = calculate_rebalancing_trades(
            available_for_trade, 
            adjusted_target,
            total_aum=available_for_trade['current_value'].sum()
        )
        
        # Add note about locked funds
        if not trades.empty:
            trades['notes'] = ''
            locked_mask = trades['scheme'].isin(locked_scheme_names)
            trades.loc[locked_mask, 'notes'] = 'LOCKED - ELSS in lock-in period'
        
        return trades
    
    return pd.DataFrame()


def generate_rebalance_report(trades_df: pd.DataFrame,
                             current_allocation: Dict[str, float],
                             target_allocation: Dict[str, float],
                             output_format: str = 'html') -> str:
    """
    Generate a rebalancing report in HTML or text format.
    
    Args:
        trades_df: DataFrame with trade recommendations
        current_allocation: Current allocation percentages
        target_allocation: Target allocation percentages
        output_format: 'html' or 'text'
        
    Returns:
        Report string
    """
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    
    if output_format == 'html':
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #34495e; margin-top: 30px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #3498db; color: white; }}
                .buy {{ color: #27ae60; font-weight: bold; }}
                .sell {{ color: #e74c3c; font-weight: bold; }}
                .hold {{ color: #7f8c8d; }}
                .summary {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin-top: 20px; }}
                .allocation-box {{ display: inline-block; margin: 10px; padding: 10px; background-color: #ecf0f1; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <h1>Portfolio Rebalancing Report</h1>
            <p>Generated on: {now}</p>
        """
        
        # Allocation Summary
        html += "<h2>Allocation Summary</h2><div>"
        for asset in ['equity', 'debt', 'gold', 'cash']:
            current = current_allocation.get(asset, 0)
            target = target_allocation.get(asset, 0)
            drift = current - target
            color = "red" if abs(drift) > 5 else "green"
            html += f"""
            <div class="allocation-box">
                <strong>{asset.upper()}</strong><br>
                Current: {current:.1f}%<br>
                Target: {target:.1f}%<br>
                Drift: <span style="color: {color}">{drift:+.1f}%</span>
            </div>
            """
        html += "</div>"
        
        # Trade Recommendations
        if not trades_df.empty:
            html += "<h2>Recommended Trades</h2>"
            html += "<table><tr><th>Scheme</th><th>Asset Class</th><th>Current Value</th>"
            html += "<th>Current %</th><th>Target %</th><th>Action</th><th>Amount</th><th>Notes</th></tr>"
            
            for _, row in trades_df.iterrows():
                action_class = row['action'].lower()
                html += f"""
                <tr>
                    <td>{row['scheme']}</td>
                    <td>{row['asset_class'].upper()}</td>
                    <td>₹{row['current_value']:,.2f}</td>
                    <td>{row['current_pct']:.1f}%</td>
                    <td>{row['target_pct']:.1f}%</td>
                    <td class="{action_class}">{row['action']}</td>
                    <td>₹{row['amount']:,.2f}</td>
                    <td>{row.get('notes', '')}</td>
                </tr>
                """
            html += "</table>"
            
            # Summary statistics
            total_buy = trades_df[trades_df['action'] == 'BUY']['amount'].sum()
            total_sell = trades_df[trades_df['action'] == 'SELL']['amount'].sum()
            
            html += f"""
            <div class="summary">
                <h3>Rebalancing Summary</h3>
                <p>Total Buy Orders: ₹{total_buy:,.2f}</p>
                <p>Total Sell Orders: ₹{total_sell:,.2f}</p>
                <p>Net Cash Required: ₹{(total_buy - total_sell):,.2f}</p>
            </div>
            """
        else:
            html += "<p>No rebalancing trades required.</p>"
        
        html += "</body></html>"
        return html
    
    else:  # Text format
        text = f"""
PORTFOLIO REBALANCING REPORT
Generated: {now}

ALLOCATION SUMMARY
-----------------
"""
        for asset in ['equity', 'debt', 'gold', 'cash']:
            current = current_allocation.get(asset, 0)
            target = target_allocation.get(asset, 0)
            drift = current - target
            status = "*** REBALANCE REQUIRED ***" if abs(drift) > 5 else "OK"
            text += f"{asset.upper():10} | Current: {current:5.1f}% | Target: {target:5.1f}% | Drift: {drift:+5.1f}% {status}\n"
        
        if not trades_df.empty:
            text += "\nRECOMMENDED TRADES\n-------------------\n"
            text += f"{'Scheme':<30} {'Action':<6} {'Amount':>15} {'Notes':<30}\n"
            text += "-" * 80 + "\n"
            
            for _, row in trades_df.iterrows():
                text += f"{row['scheme']:<30} {row['action']:<6} ₹{row['amount']:>13,.2f} {row.get('notes', ''):<30}\n"
            
            total_buy = trades_df[trades_df['action'] == 'BUY']['amount'].sum()
            total_sell = trades_df[trades_df['action'] == 'SELL']['amount'].sum()
            
            text += f"\nSUMMARY\n-------\n"
            text += f"Total Buy Orders:   ₹{total_buy:,.2f}\n"
            text += f"Total Sell Orders:  ₹{total_sell:,.2f}\n"
            text += f"Net Cash Required:  ₹{(total_buy - total_sell):,.2f}\n"
        else:
            text += "\nNo rebalancing trades required.\n"
        
        return text


def calculate_drift_matrix(current_allocation: Dict[str, float],
                          target_allocation: Dict[str, float]) -> pd.DataFrame:
    """
    Create a drift matrix showing current vs target with visual indicators.
    
    Args:
        current_allocation: Current allocation percentages
        target_allocation: Target allocation percentages
        
    Returns:
        DataFrame with drift analysis
    """
    assets = ['equity', 'debt', 'gold', 'cash']
    
    data = []
    for asset in assets:
        current = current_allocation.get(asset, 0)
        target = target_allocation.get(asset, 0)
        drift = current - target
        
        if abs(drift) > 10:
            status = 'CRITICAL'
            status_code = 3
        elif abs(drift) > 5:
            status = 'WARNING'
            status_code = 2
        elif abs(drift) > 2:
            status = 'ATTENTION'
            status_code = 1
        else:
            status = 'OPTIMAL'
            status_code = 0
        
        data.append({
            'asset_class': asset.upper(),
            'current_pct': current,
            'target_pct': target,
            'drift': drift,
            'drift_abs': abs(drift),
            'status': status,
            'status_code': status_code
        })
    
    return pd.DataFrame(data)


def simulate_rebalancing_cost(trades_df: pd.DataFrame,
                              exit_load_pct: float = 1.0,
                              stt_pct: float = 0.001,
                              stamp_duty_pct: float = 0.005) -> Dict:
    """
    Estimate the cost of executing rebalancing trades.
    
    Args:
        trades_df: DataFrame with trade recommendations
        exit_load_pct: Exit load percentage
        stt_pct: Securities Transaction Tax
        stamp_duty_pct: Stamp duty on purchase
        
    Returns:
        Dictionary with cost breakdown
    """
    if trades_df.empty:
        return {
            'exit_load': 0,
            'stt': 0,
            'stamp_duty': 0,
            'total_cost': 0,
            'cost_percentage': 0
        }
    
    total_sell = trades_df[trades_df['action'] == 'SELL']['amount'].sum()
    total_buy = trades_df[trades_df['action'] == 'BUY']['amount'].sum()
    
    exit_load = total_sell * (exit_load_pct / 100)
    stt = total_sell * stt_pct
    stamp_duty = total_buy * stamp_duty_pct
    
    total_cost = exit_load + stt + stamp_duty
    total_trade_value = total_sell + total_buy
    
    cost_pct = (total_cost / total_trade_value * 100) if total_trade_value > 0 else 0
    
    return {
        'exit_load': round(exit_load, 2),
        'stt': round(stt, 2),
        'stamp_duty': round(stamp_duty, 2),
        'total_cost': round(total_cost, 2),
        'cost_percentage': round(cost_pct, 3)
    }
