"""
Portfolio Analytics Dashboard - Phase 2.
Main Streamlit app with tabs: Overview, Holdings, Allocation, Calendar, Alerts.
Includes manual assets (FD, PPF, NPS) in totals.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import get_db
from app.components.manual_uploader import ManualAssetUploader
from app.components.alerts import AlertEngine
from app.components.calendar import LiquidityCalendar

# Page configuration
st.set_page_config(
    page_title="Portfolio Analytics",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize components
@st.cache_resource
def get_database():
    return get_db()

@st.cache_data(ttl=300)
def load_portfolio_data(_db):
    """Load all portfolio data from database."""
    data = {
        'mf_holdings': _db.get_mf_holdings(),
        'mf_transactions': _db.get_mf_transactions(),
        'fd': _db.get_manual_assets('fd'),
        'ppf': _db.get_manual_assets('ppf'),
        'nps': _db.get_manual_assets('nps'),
        'cash': _db.get_manual_assets('cash')
    }
    
    # Get portfolio totals
    data['totals'] = _db.get_total_portfolio_value()
    
    return data


def format_inr(value):
    """Format value as Indian Rupees."""
    return f"₹{value:,.0f}"


def render_sidebar():
    """Render sidebar navigation and controls."""
    st.sidebar.title("📊 Portfolio Analytics")
    st.sidebar.markdown("---")
    
    # Navigation
    page = st.sidebar.radio(
        "Navigation",
        ["Overview", "Holdings", "Allocation", "Calendar", "Alerts", "Upload Data"]
    )
    
    st.sidebar.markdown("---")
    
    # Quick stats
    db = get_database()
    totals = db.get_total_portfolio_value()
    
    st.sidebar.subheader("Quick Stats")
    st.sidebar.metric("Total Portfolio", format_inr(totals['total']))
    st.sidebar.metric("Mutual Funds", format_inr(totals['mf_value']))
    st.sidebar.metric("Manual Assets", format_inr(totals['manual_total']))
    
    st.sidebar.markdown("---")
    st.sidebar.caption("Phase 2 • Last updated: " + totals['last_updated'][:10])
    
    return page


def render_overview(data):
    """Render Overview tab with portfolio summary."""
    st.header("📈 Portfolio Overview")
    
    totals = data['totals']
    
    # Top-level metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Portfolio", format_inr(totals['total']))
    with col2:
        st.metric("Mutual Funds", format_inr(totals['mf_value']))
    with col3:
        st.metric("Fixed Deposits", format_inr(totals['fd_value']))
    with col4:
        st.metric("PPF + NPS", format_inr(totals['ppf_value'] + totals['nps_value']))
    
    st.markdown("---")
    
    # Asset breakdown
    st.subheader("Asset Breakdown")
    
    breakdown_data = {
        'Asset Type': ['Mutual Funds', 'Fixed Deposits', 'PPF', 'NPS', 'Cash'],
        'Value': [
            totals['mf_value'],
            totals['fd_value'],
            totals['ppf_value'],
            totals['nps_value'],
            totals['cash_value']
        ]
    }
    breakdown_df = pd.DataFrame(breakdown_data)
    breakdown_df = breakdown_df[breakdown_df['Value'] > 0]
    
    if not breakdown_df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart
            fig = px.pie(
                breakdown_df, 
                values='Value', 
                names='Asset Type',
                title="Portfolio Composition",
                hole=0.4
            )
            fig.update_traces(textinfo='label+percent', textposition='outside')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Bar chart
            fig = px.bar(
                breakdown_df,
                x='Asset Type',
                y='Value',
                title="Asset Values",
                text=breakdown_df['Value'].apply(lambda x: f"₹{x/100000:.1f}L")
            )
            fig.update_layout(yaxis_title="Value (₹)", xaxis_title="")
            st.plotly_chart(fig, use_container_width=True)
    
    # Detailed tables
    st.markdown("---")
    st.subheader("Detailed Holdings")
    
    tabs = st.tabs(["Mutual Funds", "Fixed Deposits", "PPF", "NPS", "Cash"])
    
    with tabs[0]:
        if not data['mf_holdings'].empty:
            display_cols = ['scheme_name', 'amc', 'category', 'units', 'nav', 'current_value']
            available_cols = [c for c in display_cols if c in data['mf_holdings'].columns]
            st.dataframe(data['mf_holdings'][available_cols], use_container_width=True)
        else:
            st.info("No mutual fund holdings found. Upload CAS data in Phase 1.")
    
    with tabs[1]:
        if not data['fd'].empty:
            display_cols = ['institution', 'account_number', 'principal', 'interest_rate', 'maturity_date', 'current_value']
            available_cols = [c for c in display_cols if c in data['fd'].columns]
            st.dataframe(data['fd'][available_cols], use_container_width=True)
            
            # Show maturing soon
            upcoming = data['fd'][pd.to_datetime(data['fd']['maturity_date']) <= pd.Timestamp.now() + pd.Timedelta(days=90)]
            if not upcoming.empty:
                st.warning(f"⚠️ {len(upcoming)} FDs maturing in next 90 days")
        else:
            st.info("No FDs found. Use Upload Data tab to add FDs.")
    
    with tabs[2]:
        if not data['ppf'].empty:
            display_cols = ['account_number', 'financial_year', 'amount', 'current_balance', 'lock_in_end']
            available_cols = [c for c in display_cols if c in data['ppf'].columns]
            st.dataframe(data['ppf'][available_cols], use_container_width=True)
        else:
            st.info("No PPF accounts found. Use Upload Data tab to add PPF.")
    
    with tabs[3]:
        if not data['nps'].empty:
            display_cols = ['pran', 'tier', 'allocation_type', 'allocation_percentage', 'current_value']
            available_cols = [c for c in display_cols if c in data['nps'].columns]
            st.dataframe(data['nps'][available_cols], use_container_width=True)
        else:
            st.info("No NPS accounts found. Use Upload Data tab to add NPS.")
    
    with tabs[4]:
        if not data['cash'].empty:
            display_cols = ['account_name', 'account_type', 'balance', 'currency']
            available_cols = [c for c in display_cols if c in data['cash'].columns]
            st.dataframe(data['cash'][available_cols], use_container_width=True)
        else:
            st.info("No cash holdings found.")


def render_holdings(data):
    """Render detailed Holdings tab."""
    st.header("📋 Holdings Analysis")
    
    # Combine all holdings for analysis
    holdings_list = []
    
    # MF holdings
    if not data['mf_holdings'].empty:
        mf = data['mf_holdings'].copy()
        mf['type'] = 'Mutual Fund'
        mf['display_name'] = mf.get('scheme_name', 'Unknown')
        holdings_list.append(mf[['display_name', 'type', 'current_value', 'category']])
    
    # FD holdings
    if not data['fd'].empty:
        fd = data['fd'].copy()
        fd['type'] = 'FD'
        fd['display_name'] = fd['institution'] + ' FD'
        fd['category'] = 'Fixed Income'
        holdings_list.append(fd[['display_name', 'type', 'current_value', 'category']])
    
    # PPF holdings (aggregate by account)
    if not data['ppf'].empty:
        ppf_summary = data['ppf'].groupby('account_number').agg({
            'current_balance': 'last'
        }).reset_index()
        ppf_summary['type'] = 'PPF'
        ppf_summary['display_name'] = 'PPF ' + ppf_summary['account_number'].astype(str)
        ppf_summary['category'] = 'Tax-Saving'
        ppf_summary = ppf_summary.rename(columns={'current_balance': 'current_value'})
        holdings_list.append(ppf_summary[['display_name', 'type', 'current_value', 'category']])
    
    # NPS holdings (aggregate by PRAN tier)
    if not data['nps'].empty:
        nps_summary = data['nps'].groupby(['pran', 'tier']).agg({
            'current_value': 'sum'
        }).reset_index()
        nps_summary['type'] = 'NPS'
        nps_summary['display_name'] = 'NPS ' + nps_summary['pran'].astype(str).str[:8] + '... Tier ' + nps_summary['tier'].astype(str)
        nps_summary['category'] = nps_summary['tier'].map({1: 'Retirement-Locked', 2: 'Retirement-Flexible'})
        holdings_list.append(nps_summary[['display_name', 'type', 'current_value', 'category']])
    
    if holdings_list:
        all_holdings = pd.concat(holdings_list, ignore_index=True)
        all_holdings = all_holdings.sort_values('current_value', ascending=False)
        
        # Top holdings
        st.subheader("Top Holdings")
        st.dataframe(
            all_holdings.head(20),
            use_container_width=True,
            hide_index=True
        )
        
        # Category breakdown
        st.subheader("Category Breakdown")
        category_summary = all_holdings.groupby('category')['current_value'].sum().reset_index()
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.pie(
                category_summary,
                values='current_value',
                names='category',
                title="By Category"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            fig = px.bar(
                category_summary,
                x='category',
                y='current_value',
                title="Category Values"
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Type breakdown
        st.subheader("Asset Type Distribution")
        type_summary = all_holdings.groupby('type')['current_value'].sum().reset_index()
        st.dataframe(type_summary, use_container_width=True)
    else:
        st.info("No holdings data available. Please upload data first.")


def render_allocation(data):
    """Render Allocation tab with target vs actual analysis."""
    st.header("⚖️ Asset Allocation")
    
    # Calculate current allocation
    totals = data['totals']
    total = totals['total']
    
    if total == 0:
        st.warning("No portfolio data available.")
        return
    
    # Simplified asset class mapping
    equity_value = 0
    debt_value = totals['fd_value'] + totals['ppf_value']
    retirement_value = totals['nps_value']
    cash_value = totals['cash_value']
    
    # Estimate MF equity/debt split (simplified)
    if not data['mf_holdings'].empty:
        mf_equity_keywords = ['equity', 'growth', 'midcap', 'smallcap', 'flexi', 'elss']
        mf_debt_keywords = ['debt', 'bond', 'gilt', 'liquid', 'money market']
        
        for idx, row in data['mf_holdings'].iterrows():
            scheme = str(row.get('scheme_name', '')).lower()
            value = float(row.get('current_value', 0))
            
            if any(k in scheme for k in mf_equity_keywords):
                equity_value += value
            elif any(k in scheme for k in mf_debt_keywords):
                debt_value += value
            else:
                # Default to equity for balanced/diversified
                equity_value += value
    else:
        equity_value += totals['mf_value']
    
    current_allocation = {
        'Equity': equity_value / total,
        'Debt': debt_value / total,
        'Retirement (NPS)': retirement_value / total,
        'Cash': cash_value / total
    }
    
    # Default target allocation (can be customized)
    target_allocation = {
        'Equity': 0.60,
        'Debt': 0.25,
        'Retirement (NPS)': 0.10,
        'Cash': 0.05
    }
    
    # Display allocation comparison
    st.subheader("Current vs Target Allocation")
    
    alloc_df = pd.DataFrame({
        'Asset Class': list(current_allocation.keys()),
        'Current %': [f"{v:.1%}" for v in current_allocation.values()],
        'Current Value': [format_inr(v * total) for v in current_allocation.values()],
        'Target %': [f"{target_allocation[k]:.1%}" for k in current_allocation.keys()],
    })
    
    st.dataframe(alloc_df, use_container_width=True, hide_index=True)
    
    # Visual comparison
    col1, col2 = st.columns(2)
    
    with col1:
        fig = go.Figure(data=[
            go.Bar(name='Current', x=list(current_allocation.keys()), 
                   y=list(current_allocation.values()), marker_color='blue'),
            go.Bar(name='Target', x=list(target_allocation.keys()), 
                   y=list(target_allocation.values()), marker_color='green')
        ])
        fig.update_layout(
            title="Allocation: Current vs Target",
            barmode='group',
            yaxis=dict(tickformat='.0%')
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Sunburst chart of actual values
        fig = px.sunburst(
            names=['Portfolio'] + list(current_allocation.keys()),
            parents=[''] + ['Portfolio'] * len(current_allocation),
            values=[total] + list(current_allocation.values()),
            title="Portfolio Structure"
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Rebalancing recommendations
    st.subheader("Rebalancing Analysis")
    
    recommendations = []
    for asset, current_pct in current_allocation.items():
        target_pct = target_allocation.get(asset, 0)
        diff_pct = current_pct - target_pct
        diff_value = diff_pct * total
        
        if abs(diff_pct) > 0.05:  # 5% threshold
            if diff_pct > 0:
                action = f"REDUCE {asset} by {format_inr(diff_value)}"
            else:
                action = f"INCREASE {asset} by {format_inr(abs(diff_value))}"
            recommendations.append({
                'Asset Class': asset,
                'Current': f"{current_pct:.1%}",
                'Target': f"{target_pct:.1%}",
                'Difference': f"{diff_pct:+.1%}",
                'Action Required': action
            })
    
    if recommendations:
        rec_df = pd.DataFrame(recommendations)
        st.dataframe(rec_df, use_container_width=True)
    else:
        st.success("✅ Allocation is within target ranges!")


def render_calendar(data):
    """Render Calendar tab with liquidity events."""
    st.header("📅 Liquidity Calendar")
    
    # Initialize calendar
    calendar = LiquidityCalendar()
    
    # Add events from data
    calendar.add_fd_maturities(data['fd'])
    calendar.add_elss_lockins(data['mf_transactions'])
    calendar.add_sip_dates(data['mf_transactions'])
    calendar.add_ppf_withdrawals(data['ppf'])
    calendar.add_nps_tier2_withdrawal(data['nps'])
    
    # Get calendar DataFrame
    cal_df = calendar.get_calendar_df()
    
    if cal_df.empty:
        st.info("No upcoming liquidity events found.")
        return
    
    # Filters
    st.subheader("Filters")
    col1, col2 = st.columns(2)
    
    with col1:
        asset_types = cal_df['asset_type'].unique().tolist()
        selected_types = st.multiselect(
            "Asset Types",
            asset_types,
            default=asset_types
        )
    
    with col2:
        days_ahead = st.slider("Days Ahead", 30, 365, 90, step=30)
    
    # Filter data
    filtered_df = cal_df[
        (cal_df['asset_type'].isin(selected_types)) &
        (cal_df['days_until'] <= days_ahead)
    ].copy()
    
    if filtered_df.empty:
        st.info("No events match the selected filters.")
        return
    
    # Summary metrics
    st.markdown("---")
    st.subheader("Upcoming Liquidity Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Events", len(filtered_df))
    with col2:
        total_value = filtered_df['value'].sum()
        st.metric("Total Value", format_inr(total_value))
    with col3:
        next_30 = filtered_df[filtered_df['days_until'] <= 30]['value'].sum()
        st.metric("Next 30 Days", format_inr(next_30))
    with col4:
        next_90 = filtered_df[filtered_df['days_until'] <= 90]['value'].sum()
        st.metric("Next 90 Days", format_inr(next_90))
    
    # Calendar view
    st.markdown("---")
    st.subheader("Upcoming Events")
    
    # Group by month for better visualization
    filtered_df['month'] = pd.to_datetime(filtered_df['date']).dt.to_period('M').astype(str)
    
    for month, month_df in filtered_df.groupby('month'):
        with st.expander(f"📆 {month} ({len(month_df)} events)"):
            for idx, row in month_df.iterrows():
                col1, col2, col3 = st.columns([3, 2, 3])
                
                with col1:
                    st.markdown(f"**{row['title']}**")
                    st.caption(f"📅 {row['date']} | 🏷️ {row['asset_type']}")
                
                with col2:
                    st.markdown(f"**{format_inr(row['value'])}**")
                    st.caption(f"⏰ {row['days_until']} days")
                
                with col3:
                    st.info(row['actionable'])
    
    # Full table
    st.markdown("---")
    st.subheader("All Events")
    display_df = filtered_df[['date', 'event_type', 'title', 'value', 'asset_type', 'days_until', 'actionable']]
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def render_alerts(data):
    """Render Alerts tab with portfolio health indicators."""
    st.header("🚨 Portfolio Alerts")
    
    # Initialize alert engine
    engine = AlertEngine()
    
    # Prepare data for alerts
    holdings_df = data['mf_holdings'].copy() if not data['mf_holdings'].empty else pd.DataFrame()
    
    # Create combined holdings for concentration checks
    combined_holdings = []
    
    if not data['mf_holdings'].empty:
        mf = data['mf_holdings'][['scheme_name', 'current_value']].copy()
        combined_holdings.append(mf)
    
    if not data['fd'].empty:
        fd = data['fd'].copy()
        fd['scheme_name'] = fd['institution'] + ' FD'
        combined_holdings.append(fd[['scheme_name', 'current_value']])
    
    if combined_holdings:
        all_holdings = pd.concat(combined_holdings, ignore_index=True)
    else:
        all_holdings = pd.DataFrame()
    
    totals = data['totals']
    
    # Generate alerts report
    report = engine.generate_alerts_report(
        holdings_df=all_holdings,
        transactions_df=data['mf_transactions'],
        cash_value=totals['cash_value'],
        total_portfolio_value=totals['total'],
        fds_df=data['fd']
    )
    
    # Summary cards
    st.subheader("Alert Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.error(f"🔴 Critical: {report['summary']['critical_count']}")
    with col2:
        st.warning(f"🟡 Warnings: {report['summary']['warning_count']}")
    with col3:
        st.info(f"🔵 Info: {report['summary']['info_count']}")
    with col4:
        st.success(f"🟢 OK: {report['summary']['ok_count']}")
    
    st.markdown("---")
    
    # Display alerts by severity
    if report['critical']:
        st.subheader("🔴 Critical Alerts")
        for alert in report['critical']:
            with st.container():
                st.error(f"**{alert['title']}**")
                st.write(alert['message'])
                st.caption(f"💡 {alert['actionable']}")
                st.markdown("---")
    
    if report['warnings']:
        st.subheader("🟡 Warning Alerts")
        for alert in report['warnings']:
            with st.container():
                st.warning(f"**{alert['title']}**")
                st.write(alert['message'])
                st.caption(f"💡 {alert['actionable']}")
                st.markdown("---")
    
    if report['info']:
        st.subheader("🔵 Information")
        for alert in report['info']:
            with st.container():
                st.info(f"**{alert['title']}**")
                st.write(alert['message'])
                st.caption(f"💡 {alert['actionable']}")
    
    if report['ok']:
        st.subheader("🟢 Healthy Indicators")
        for alert in report['ok']:
            with st.container():
                st.success(f"**{alert['title']}**")
                st.write(alert['message'])
    
    # If no alerts
    if report['summary']['total'] == 0:
        st.success("✅ No alerts generated. Portfolio looks healthy!")
    
    # Export option
    st.markdown("---")
    if st.button("📥 Export Alerts Report"):
        import json
        report_json = json.dumps(report, indent=2)
        st.download_button(
            "Download JSON",
            report_json,
            file_name=f"alerts_report_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json"
        )


def render_upload(data):
    """Render Upload Data tab."""
    st.header("📤 Upload Manual Assets")
    
    uploader = ManualAssetUploader()
    uploader.render()


def main():
    """Main dashboard entry point."""
    # Load data
    db = get_database()
    data = load_portfolio_data(db)
    
    # Render sidebar and get selected page
    page = render_sidebar()
    
    # Render selected page
    if page == "Overview":
        render_overview(data)
    elif page == "Holdings":
        render_holdings(data)
    elif page == "Allocation":
        render_allocation(data)
    elif page == "Calendar":
        render_calendar(data)
    elif page == "Alerts":
        render_alerts(data)
    elif page == "Upload Data":
        render_upload(data)


if __name__ == "__main__":
    from datetime import datetime
    main()
