"""
Tax Tracker Module
Calculates tax liability, classifies gains, and identifies tax loss harvesting opportunities.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta


# Tax rules for India FY 2025-26
TAX_RULES = {
    'equity': {
        'stcg_rate': 0.20,  # 20% if held < 1 year
        'ltcg_rate': 0.125,  # 12.5% beyond ₹1.25L exemption
        'ltcg_exemption': 125000,  # ₹1.25L exemption per year
        'holding_period_days': 365
    },
    'debt': {
        'stcg_method': 'slab',  # Slab rate if < 3 years
        'ltcg_rate': 0.20,  # 20% with indexation if > 3 years
        'holding_period_days': 1095  # 3 years
    },
    'gold': {
        'stcg_method': 'slab',
        'ltcg_rate': 0.20,
        'holding_period_days': 1095
    }
}


def classify_gains(holdings_df: pd.DataFrame,
                  purchase_date_col: str = 'purchase_date',
                  current_value_col: str = 'current_value',
                  cost_basis_col: str = 'cost_basis',
                  scheme_type_col: str = 'scheme_type') -> pd.DataFrame:
    """
    Classify holdings by gain type (STCG vs LTCG).
    
    Args:
        holdings_df: DataFrame with holdings
        purchase_date_col: Column name for purchase date
        current_value_col: Column name for current value
        cost_basis_col: Column name for cost basis
        scheme_type_col: Column name for scheme type
        
    Returns:
        DataFrame with gain classification
    """
    if holdings_df is None or holdings_df.empty:
        return pd.DataFrame()
    
    df = holdings_df.copy()
    today = datetime.now()
    
    # Ensure date column is datetime
    df[purchase_date_col] = pd.to_datetime(df[purchase_date_col])
    
    # Calculate holding period
    df['holding_days'] = (today - df[purchase_date_col]).dt.days
    df['holding_years'] = df['holding_days'] / 365.25
    
    # Classify asset type
    def get_asset_type(scheme_type):
        if pd.isna(scheme_type):
            return 'equity'
        scheme_upper = str(scheme_type).upper()
        if any(x in scheme_upper for x in ['ELSS', 'EQUITY', 'INDEX', 'ETF']):
            return 'equity'
        elif any(x in scheme_upper for x in ['GOLD', 'SGB']):
            return 'gold'
        else:
            return 'debt'
    
    df['asset_type'] = df[scheme_type_col].apply(get_asset_type)
    
    # Classify gains
    def classify_gain(row):
        asset_type = row['asset_type']
        holding_days = row['holding_days']
        
        rules = TAX_RULES.get(asset_type, TAX_RULES['equity'])
        threshold = rules['holding_period_days']
        
        if holding_days < threshold:
            return 'STCG'
        else:
            return 'LTCG'
    
    df['gain_type'] = df.apply(classify_gain, axis=1)
    
    # Calculate unrealized gains/losses
    df['unrealized_gain'] = df[current_value_col] - df[cost_basis_col]
    df['unrealized_gain_pct'] = (df['unrealized_gain'] / df[cost_basis_col]) * 100
    
    # Flag profitable vs loss positions
    df['is_profit'] = df['unrealized_gain'] > 0
    df['is_loss'] = df['unrealized_gain'] < 0
    
    return df


def calculate_tax_liability_if_sold(holdings_df: pd.DataFrame,
                                   user_tax_slab: float = 0.30) -> Dict:
    """
    Calculate estimated tax liability if all holdings are sold today.
    
    Args:
        holdings_df: DataFrame with holdings (output from classify_gains)
        user_tax_slab: User's income tax slab rate
        
    Returns:
        Dictionary with tax liability breakdown
    """
    if holdings_df is None or holdings_df.empty:
        return {
            'total_tax': 0,
            'equity_stcg_tax': 0,
            'equity_ltcg_tax': 0,
            'debt_stcg_tax': 0,
            'debt_ltcg_tax': 0,
            'total_gains': 0,
            'total_losses': 0,
            'net_taxable_gains': 0
        }
    
    # Classify if not already done
    if 'gain_type' not in holdings_df.columns:
        df = classify_gains(holdings_df)
    else:
        df = holdings_df.copy()
    
    tax_summary = {
        'total_tax': 0,
        'equity_stcg_tax': 0,
        'equity_ltcg_tax': 0,
        'debt_stcg_tax': 0,
        'debt_ltcg_tax': 0,
        'gold_stcg_tax': 0,
        'gold_ltcg_tax': 0,
        'total_gains': 0,
        'total_losses': 0,
        'net_taxable_gains': 0,
        'details': []
    }
    
    # Group by asset type and gain type
    for _, row in df.iterrows():
        asset_type = row['asset_type']
        gain_type = row['gain_type']
        unrealized_gain = row['unrealized_gain']
        
        if unrealized_gain > 0:
            tax_summary['total_gains'] += unrealized_gain
        else:
            tax_summary['total_losses'] += abs(unrealized_gain)
        
        # Calculate tax
        if unrealized_gain > 0:
            rules = TAX_RULES.get(asset_type, TAX_RULES['equity'])
            
            if gain_type == 'STCG':
                if asset_type == 'equity':
                    tax = unrealized_gain * rules['stcg_rate']
                    tax_summary['equity_stcg_tax'] += tax
                else:
                    # Debt/Gold STCG at slab rate
                    tax = unrealized_gain * user_tax_slab
                    if asset_type == 'debt':
                        tax_summary['debt_stcg_tax'] += tax
                    else:
                        tax_summary['gold_stcg_tax'] += tax
            else:  # LTCG
                if asset_type == 'equity':
                    # Apply exemption
                    taxable_gain = max(0, unrealized_gain - rules['ltcg_exemption'])
                    tax = taxable_gain * rules['ltcg_rate']
                    tax_summary['equity_ltcg_tax'] += tax
                else:
                    tax = unrealized_gain * rules['ltcg_rate']
                    if asset_type == 'debt':
                        tax_summary['debt_ltcg_tax'] += tax
                    else:
                        tax_summary['gold_ltcg_tax'] += tax
        
        tax_summary['details'].append({
            'scheme': row.get('scheme', 'Unknown'),
            'asset_type': asset_type,
            'gain_type': gain_type,
            'unrealized_gain': unrealized_gain,
            'estimated_tax': tax if unrealized_gain > 0 else 0
        })
    
    tax_summary['total_tax'] = (
        tax_summary['equity_stcg_tax'] + 
        tax_summary['equity_ltcg_tax'] +
        tax_summary['debt_stcg_tax'] + 
        tax_summary['debt_ltcg_tax'] +
        tax_summary['gold_stcg_tax'] +
        tax_summary['gold_ltcg_tax']
    )
    
    tax_summary['net_taxable_gains'] = tax_summary['total_gains'] - tax_summary['total_losses']
    
    # Round all numeric values
    for key in ['total_tax', 'equity_stcg_tax', 'equity_ltcg_tax', 
                'debt_stcg_tax', 'debt_ltcg_tax', 'gold_stcg_tax', 'gold_ltcg_tax',
                'total_gains', 'total_losses', 'net_taxable_gains']:
        tax_summary[key] = round(tax_summary[key], 2)
    
    return tax_summary


def identify_harvest_opportunities(holdings_df: pd.DataFrame,
                                  min_loss_threshold: float = 1000) -> pd.DataFrame:
    """
    Identify tax loss harvesting opportunities.
    
    Args:
        holdings_df: DataFrame with holdings
        min_loss_threshold: Minimum loss amount to consider for harvesting
        
    Returns:
        DataFrame with harvesting opportunities
    """
    if holdings_df is None or holdings_df.empty:
        return pd.DataFrame()
    
    # Classify gains
    if 'gain_type' not in holdings_df.columns:
        df = classify_gains(holdings_df)
    else:
        df = holdings_df.copy()
    
    # Filter for loss positions only
    loss_positions = df[df['is_loss'] == True].copy()
    
    # Filter by threshold
    loss_positions = loss_positions[abs(loss_positions['unrealized_gain']) >= min_loss_threshold]
    
    if loss_positions.empty:
        return pd.DataFrame()
    
    # Sort by loss amount (most loss first)
    loss_positions = loss_positions.sort_values('unrealized_gain', ascending=True)
    
    # Add harvest value
    loss_positions['harvest_value'] = abs(loss_positions['unrealized_gain'])
    
    # Calculate tax savings (assume 20% rate for estimation)
    loss_positions['potential_tax_savings'] = loss_positions['harvest_value'] * 0.20
    
    return loss_positions[[
        'scheme', 'asset_type', 'purchase_date', 'cost_basis', 
        'current_value', 'unrealized_gain', 'harvest_value',
        'potential_tax_savings'
    ]]


def tax_loss_harvesting_suggestions(holdings_df: pd.DataFrame,
                                   min_loss_threshold: float = 1000,
                                   max_harvests: int = 5) -> List[Dict]:
    """
    Generate specific tax loss harvesting recommendations.
    
    Args:
        holdings_df: DataFrame with holdings
        min_loss_threshold: Minimum loss to harvest
        max_harvests: Maximum number of suggestions to return
        
    Returns:
        List of recommendation dictionaries
    """
    opportunities = identify_harvest_opportunities(holdings_df, min_loss_threshold)
    
    if opportunities.empty:
        return []
    
    suggestions = []
    
    for i, (_, row) in enumerate(opportunities.iterrows()):
        if i >= max_harvests:
            break
        
        suggestion = {
            'priority': i + 1,
            'action': 'HARVEST',
            'scheme': row['scheme'],
            'asset_type': row['asset_type'],
            'loss_amount': row['harvest_value'],
            'potential_tax_savings': row['potential_tax_savings'],
            'suggestion': f"Sell {row['scheme']} to realize loss of ₹{row['harvest_value']:,.2f}",
            'reinvest_strategy': f"Wait 1 month, then buy similar fund in same category to maintain allocation",
            'wash_sale_warning': "Avoid buying same/identical fund within 30 days to prevent wash sale rules",
            'timeline': 'Execute before March 31 for current FY benefits'
        }
        
        suggestions.append(suggestion)
    
    return suggestions


def get_tax_efficient_exit_strategy(holdings_df: pd.DataFrame,
                                   target_amount: float,
                                   user_tax_slab: float = 0.30) -> pd.DataFrame:
    """
    Suggest which holdings to sell for tax-efficient exit.
    
    Args:
        holdings_df: DataFrame with holdings
        target_amount: Target amount to raise
        user_tax_slab: User's tax slab rate
        
    Returns:
        DataFrame with recommended exit order
    """
    if holdings_df is None or holdings_df.empty:
        return pd.DataFrame()
    
    # Classify gains
    if 'gain_type' not in holdings_df.columns:
        df = classify_gains(holdings_df)
    else:
        df = holdings_df.copy()
    
    # Calculate effective tax rate for each position
    def get_tax_priority(row):
        asset_type = row['asset_type']
        gain_type = row['gain_type']
        is_loss = row['is_loss']
        
        if is_loss:
            return 0  # Losses first (tax benefit)
        elif gain_type == 'LTCG' and asset_type == 'equity':
            return 1  # LTCG equity (12.5% after exemption)
        elif gain_type == 'LTCG' and asset_type in ['debt', 'gold']:
            return 2  # LTCG debt (20% with indexation)
        elif gain_type == 'STCG' and asset_type == 'equity':
            return 3  # STCG equity (20%)
        else:
            return 4  # STCG debt/gold at slab rate
    
    df['tax_priority'] = df.apply(get_tax_priority, axis=1)
    
    # Sort by tax priority
    df = df.sort_values(['tax_priority', 'holding_days'], ascending=[True, False])
    
    # Select holdings to meet target
    selected = []
    accumulated = 0
    
    for _, row in df.iterrows():
        if accumulated >= target_amount:
            break
        
        available = row['current_value']
        to_use = min(available, target_amount - accumulated)
        
        selected.append({
            'scheme': row['scheme'],
            'asset_type': row['asset_type'],
            'gain_type': row['gain_type'],
            'current_value': row['current_value'],
            'unrealized_gain': row['unrealized_gain'],
            'amount_to_sell': to_use,
            'tax_priority': row['tax_priority'],
            'reason': get_exit_reason(row['tax_priority'])
        })
        
        accumulated += to_use
    
    return pd.DataFrame(selected)


def get_exit_reason(priority: int) -> str:
    """Get human-readable reason for exit priority."""
    reasons = {
        0: "Harvest tax loss",
        1: "LTCG Equity - lowest tax rate",
        2: "LTCG Debt - with indexation benefit",
        3: "STCG Equity - moderate tax rate",
        4: "STCG Debt - highest tax rate (avoid if possible)"
    }
    return reasons.get(priority, "Unknown")


def calculate_carry_forward_losses(holdings_df: pd.DataFrame,
                                  previous_year_losses: float = 0) -> Dict:
    """
    Calculate capital losses available for carry forward.
    
    Args:
        holdings_df: DataFrame with holdings
        previous_year_losses: Losses from previous years
        
    Returns:
        Dictionary with loss carry forward details
    """
    if holdings_df is None or holdings_df.empty:
        return {
            'current_year_stcg_losses': 0,
            'current_year_ltcg_losses': 0,
            'carry_forward_stcg': previous_year_losses if previous_year_losses else 0,
            'carry_forward_ltcg': 0,
            'usable_against_stcg': 0,
            'usable_against_ltcg': 0
        }
    
    # Classify gains
    if 'gain_type' not in holdings_df.columns:
        df = classify_gains(holdings_df)
    else:
        df = holdings_df.copy()
    
    # Separate STCG and LTCG losses
    stcg_losses = df[(df['gain_type'] == 'STCG') & (df['is_loss'] == True)]['unrealized_gain'].sum()
    ltcg_losses = df[(df['gain_type'] == 'LTCG') & (df['is_loss'] == True)]['unrealized_gain'].sum()
    
    stcg_losses = abs(stcg_losses)
    ltcg_losses = abs(ltcg_losses)
    
    return {
        'current_year_stcg_losses': round(stcg_losses, 2),
        'current_year_ltcg_losses': round(ltcg_losses, 2),
        'carry_forward_stcg': round(previous_year_losses + stcg_losses, 2),
        'carry_forward_ltcg': round(ltcg_losses, 2),
        'usable_against_stcg': round(previous_year_losses + stcg_losses, 2),
        'usable_against_ltcg': round(ltcg_losses, 2),
        'notes': [
            'STCG losses can offset STCG gains only',
            'LTCG losses can offset LTCG gains only',
            'Unutilized losses can be carried forward for 8 years'
        ]
    }


def generate_tax_report(holdings_df: pd.DataFrame,
                       user_tax_slab: float = 0.30,
                       output_format: str = 'html') -> str:
    """
    Generate comprehensive tax report.
    
    Args:
        holdings_df: DataFrame with holdings
        user_tax_slab: User's income tax slab
        output_format: 'html' or 'text'
        
    Returns:
        Report string
    """
    now = datetime.now().strftime('%Y-%m-%d')
    
    # Classify gains
    df = classify_gains(holdings_df)
    
    # Calculate tax liability
    tax_liability = calculate_tax_liability_if_sold(df, user_tax_slab)
    
    # Get harvesting opportunities
    harvest_opps = identify_harvest_opportunities(df)
    
    if output_format == 'html':
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #2c3e50; }}
                h2 {{ color: #34495e; margin-top: 30px; }}
                table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
                th {{ background-color: #3498db; color: white; }}
                .gain {{ color: #27ae60; }}
                .loss {{ color: #e74c3c; }}
                .summary {{ background-color: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .highlight {{ background-color: #fff3cd; padding: 10px; border-left: 4px solid #ffc107; }}
            </style>
        </head>
        <body>
            <h1>Tax Analysis Report - FY 2025-26</h1>
            <p>Generated: {now}</p>
            
            <div class="summary">
                <h2>Tax Liability Summary</h2>
                <p>Total Unrealized Gains: ₹{tax_liability['total_gains']:,.2f}</p>
                <p>Total Unrealized Losses: ₹{tax_liability['total_losses']:,.2f}</p>
                <p><strong>Estimated Tax if Sold Today: ₹{tax_liability['total_tax']:,.2f}</strong></p>
            </div>
            
            <h2>Tax Breakdown by Asset Type</h2>
            <table>
                <tr><th>Type</th><th>STCG Tax</th><th>LTCG Tax</th></tr>
                <tr>
                    <td>Equity</td>
                    <td>₹{tax_liability['equity_stcg_tax']:,.2f}</td>
                    <td>₹{tax_liability['equity_ltcg_tax']:,.2f}</td>
                </tr>
                <tr>
                    <td>Debt</td>
                    <td>₹{tax_liability['debt_stcg_tax']:,.2f}</td>
                    <td>₹{tax_liability['debt_ltcg_tax']:,.2f}</td>
                </tr>
                <tr>
                    <td>Gold</td>
                    <td>₹{tax_liability['gold_stcg_tax']:,.2f}</td>
                    <td>₹{tax_liability['gold_ltcg_tax']:,.2f}</td>
                </tr>
            </table>
            
            <h2>Tax Loss Harvesting Opportunities</h2>
        """
        
        if not harvest_opps.empty:
            html += """
            <div class="highlight">
                <strong>Action Required:</strong> Consider harvesting these losses before March 31st
            </div>
            <table>
                <tr><th>Scheme</th><th>Loss Amount</th><th>Potential Tax Savings</th></tr>
            """
            for _, row in harvest_opps.head(5).iterrows():
                html += f"""
                <tr>
                    <td>{row['scheme']}</td>
                    <td class="loss">₹{row['harvest_value']:,.2f}</td>
                    <td>₹{row['potential_tax_savings']:,.2f}</td>
                </tr>
                """
            html += "</table>"
        else:
            html += "<p>No significant loss harvesting opportunities found.</p>"
        
        html += """
            <h2>Tax Rules Reference (FY 2025-26)</h2>
            <ul>
                <li><strong>Equity STCG:</strong> 20% if held &lt; 1 year</li>
                <li><strong>Equity LTCG:</strong> 12.5% beyond ₹1.25L exemption/year</li>
                <li><strong>Debt STCG:</strong> Slab rate if held &lt; 3 years</li>
                <li><strong>Debt LTCG:</strong> 20% with indexation if held &gt; 3 years</li>
            </ul>
        </body></html>
        """
        return html
    
    else:  # Text format
        text = f"""
TAX ANALYSIS REPORT - FY 2025-26
Generated: {now}

TAX LIABILITY SUMMARY
---------------------
Total Unrealized Gains:  ₹{tax_liability['total_gains']:,.2f}
Total Unrealized Losses: ₹{tax_liability['total_losses']:,.2f}
Net Taxable Gains:       ₹{tax_liability['net_taxable_gains']:,.2f}
Estimated Tax if Sold:   ₹{tax_liability['total_tax']:,.2f}

TAX BREAKDOWN BY TYPE
---------------------
Equity STCG: ₹{tax_liability['equity_stcg_tax']:,.2f}
Equity LTCG: ₹{tax_liability['equity_ltcg_tax']:,.2f}
Debt STCG:   ₹{tax_liability['debt_stcg_tax']:,.2f}
Debt LTCG:   ₹{tax_liability['debt_ltcg_tax']:,.2f}

TAX LOSS HARVESTING
-------------------
"""
        if not harvest_opps.empty:
            text += "Opportunities Found:\n"
            for _, row in harvest_opps.head(5).iterrows():
                text += f"- {row['scheme']}: Loss ₹{row['harvest_value']:,.2f} (Save ₹{row['potential_tax_savings']:,.2f} tax)\n"
        else:
            text += "No significant opportunities found.\n"
        
        text += """
TAX RULES FY 2025-26
--------------------
Equity STCG: 20% (< 1 year)
Equity LTCG: 12.5% beyond ₹1.25L exemption (> 1 year)
Debt STCG: Slab rate (< 3 years)
Debt LTCG: 20% with indexation (> 3 years)
"""
        return text
