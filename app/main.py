"""
Portfolio Analytics Tool - Streamlit Dashboard
Main entry point for the portfolio analytics application.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path for imports
current_dir = Path(__file__).parent
parent_dir = current_dir.parent
sys.path.insert(0, str(parent_dir))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

from database import PortfolioDatabase, get_default_db, Holding, Transaction
from api.amfi_provider import get_amfi_provider
from parsers.cas_parser import CASParser, parse_cas
from utils.xirr import calculate_xirr_safe, format_xirr


# Page configuration
st.set_page_config(
    page_title="Portfolio Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Initialize session state variables."""
    if 'db' not in st.session_state:
        st.session_state.db = get_default_db()
    if 'nav_provider' not in st.session_state:
        st.session_state.nav_provider = get_amfi_provider()
    if 'holdings_df' not in st.session_state:
        st.session_state.holdings_df = pd.DataFrame()
    if 'transactions_df' not in st.session_state:
        st.session_state.transactions_df = pd.DataFrame()


def format_currency(value: float) -> str:
    """Format value as Indian currency."""
    if value is None or pd.isna(value):
        return "₹0.00"
    return f"₹{value:,.2f}"


def format_percentage(value: float) -> str:
    """Format value as percentage."""
    if value is None or pd.isna(value):
        return "0.00%"
    return f"{value:.2f}%"


def load_holdings_from_db() -> pd.DataFrame:
    """Load holdings from database with calculated values."""
    db = st.session_state.db
    holdings = db.get_all_holdings()
    
    if not holdings:
        return pd.DataFrame()
    
    data = []
    for h in holdings:
        current_value = h.units * h.current_nav if h.current_nav else 0
        unrealized_gain = current_value - h.purchase_value if h.purchase_value else 0
        
        # Calculate XIRR
        cashflows = db.get_cashflows_for_xirr(h.isin)
        if current_value > 0:
            cashflows.append((datetime.now(), current_value))
        xirr = calculate_xirr_safe(cashflows)
        
        data.append({
            'ID': h.id,
            'ISIN': h.isin,
            'Scheme Name': h.scheme_name,
            'Category': h.category,
            'Folio': h.folio,
            'AMC': h.amc,
            'Units': h.units,
            'Purchase Value': h.purchase_value,
            'Current NAV': h.current_nav,
            'Current Value': current_value,
            'Unrealized Gain': unrealized_gain,
            'XIRR': xirr * 100 if xirr else 0,  # Store as percentage
            'Last Updated': h.last_updated
        })
    
    return pd.DataFrame(data)


def render_sidebar():
    """Render sidebar with file upload and controls."""
    st.sidebar.title("📊 Portfolio Analytics")
    st.sidebar.markdown("---")
    
    st.sidebar.header("Import CAS Statement")
    
    uploaded_file = st.sidebar.file_uploader(
        "Upload CAS (PDF, CSV, or Excel)",
        type=['pdf', 'csv', 'xls', 'xlsx'],
        help="Upload your Consolidated Account Statement from Karvy or CAMS (PDF, CSV, XLS, XLSX)"
    )
    
    if uploaded_file is not None:
        # Save uploaded file temporarily
        temp_path = parent_dir / 'temp_uploaded_file'
        temp_path.write_bytes(uploaded_file.getvalue())
        
        if st.sidebar.button("Parse CAS", type="primary"):
            with st.spinner("Parsing CAS statement..."):
                try:
                    parser = CASParser()
                    result = parser.parse(str(temp_path))
                    
                    # Store in session state
                    st.session_state.holdings_df = pd.DataFrame(result['holdings'])
                    st.session_state.transactions_df = pd.DataFrame(result['transactions'])
                    
                    # Save to database
                    db = st.session_state.db
                    
                    for holding_data in result['holdings']:
                        holding = Holding(
                            id=None,
                            isin=holding_data['isin'],
                            scheme_name=holding_data['scheme_name'],
                            category=holding_data.get('category', ''),
                            units=holding_data['units'],
                            purchase_value=holding_data.get('purchase_value', 0),
                            purchase_date=holding_data.get('purchase_date', ''),
                            folio=holding_data['folio'],
                            amc=holding_data.get('amc', ''),
                            current_nav=holding_data.get('current_nav'),
                            last_updated=datetime.now().isoformat()
                        )
                        db.add_holding(holding)
                    
                    for tx_data in result['transactions']:
                        transaction = Transaction(
                            id=None,
                            isin=tx_data.get('isin', ''),
                            type=tx_data.get('type', 'PURCHASE'),
                            date=tx_data['date'],
                            amount=tx_data['amount'],
                            units=tx_data.get('units', 0),
                            nav=tx_data.get('nav', 0),
                            folio=tx_data.get('folio'),
                            scheme_name=tx_data.get('scheme_name')
                        )
                        db.add_transaction(transaction)
                    
                    st.sidebar.success(f"✅ Imported {len(result['holdings'])} holdings")
                    
                except Exception as e:
                    st.sidebar.error(f"❌ Error parsing CAS: {str(e)}")
                finally:
                    # Clean up temp file
                    if temp_path.exists():
                        temp_path.unlink()
    
    st.sidebar.markdown("---")
    st.sidebar.header("NAV Updates")
    
    if st.sidebar.button("🔄 Update NAVs", type="secondary"):
        with st.spinner("Fetching latest NAVs from AMFI..."):
            try:
                provider = st.session_state.nav_provider
                db = st.session_state.db
                holdings = db.get_all_holdings()
                
                updated = 0
                failed = 0
                
                for holding in holdings:
                    nav = provider.get_nav(holding.isin)
                    if nav:
                        db.update_nav(holding.isin, holding.folio, nav)
                        updated += 1
                    else:
                        failed += 1
                
                st.sidebar.success(f"✅ Updated {updated} NAVs")
                if failed > 0:
                    st.sidebar.warning(f"⚠️ Failed to update {failed} NAVs")
                
                # Refresh holdings
                st.rerun()
                
            except Exception as e:
                st.sidebar.error(f"❌ Error updating NAVs: {str(e)}")
    
    st.sidebar.markdown("---")
    st.sidebar.header("Data Management")
    
    if st.sidebar.button("🗑️ Clear All Data", type="secondary"):
        confirm = st.sidebar.checkbox("Confirm deletion")
        if confirm:
            db = st.session_state.db
            db.clear_all_data()
            st.sidebar.success("✅ All data cleared")
            st.rerun()


def render_dashboard():
    """Render main dashboard content."""
    st.title("📊 Portfolio Analytics Dashboard")
    
    # Load holdings from database
    holdings_df = load_holdings_from_db()
    
    if holdings_df.empty:
        st.info("👋 Welcome! Please upload a CAS statement using the sidebar to get started.")
        
        # Show sample dashboard layout
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total AUM", "₹0.00")
        with col2:
            st.metric("Invested", "₹0.00")
        with col3:
            st.metric("Unrealized Gains", "₹0.00")
        with col4:
            st.metric("XIRR", "0.00%")
        
        st.markdown("---")
        st.markdown("### How to use this tool:")
        st.markdown("""
        1. **Upload CAS**: Upload your Consolidated Account Statement (PDF or CSV) from Karvy/CAMS
        2. **Update NAVs**: Click 'Update NAVs' to fetch current market values from AMFI
        3. **View Analytics**: Explore your portfolio summary, holdings, and asset allocation
        """)
        return
    
    # Calculate portfolio metrics
    total_aum = holdings_df['Current Value'].sum()
    total_invested = holdings_df['Purchase Value'].sum()
    total_gain = holdings_df['Unrealized Gain'].sum()
    
    # Calculate overall XIRR
    db = st.session_state.db
    all_cashflows = []
    for _, row in holdings_df.iterrows():
        cf = db.get_cashflows_for_xirr(row['ISIN'])
        all_cashflows.extend(cf)
    if total_aum > 0:
        all_cashflows.append((datetime.now(), total_aum))
    portfolio_xirr = calculate_xirr_safe(all_cashflows)
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total AUM",
            format_currency(total_aum),
            help="Current market value of all holdings"
        )
    
    with col2:
        st.metric(
            "Total Invested",
            format_currency(total_invested),
            help="Total amount invested"
        )
    
    with col3:
        gain_color = "normal" if total_gain >= 0 else "inverse"
        st.metric(
            "Unrealized Gains",
            format_currency(total_gain),
            format_percentage((total_gain / total_invested * 100) if total_invested > 0 else 0),
            delta_color=gain_color
        )
    
    with col4:
        st.metric(
            "Portfolio XIRR",
            format_xirr(portfolio_xirr),
            help="Extended Internal Rate of Return"
        )
    
    st.markdown("---")
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Asset Allocation by Category")
        
        category_data = holdings_df.groupby('Category')['Current Value'].sum().reset_index()
        if not category_data.empty:
            fig = px.pie(
                category_data,
                values='Current Value',
                names='Category',
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            fig.update_layout(showlegend=False, height=350)
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Allocation by AMC")
        
        amc_data = holdings_df.groupby('AMC')['Current Value'].sum().reset_index()
        amc_data = amc_data.sort_values('Current Value', ascending=False).head(10)
        if not amc_data.empty:
            fig = px.bar(
                amc_data,
                x='AMC',
                y='Current Value',
                color='Current Value',
                color_continuous_scale='Viridis'
            )
            fig.update_layout(
                xaxis_title="AMC",
                yaxis_title="Value (₹)",
                height=350,
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Holdings table
    st.subheader("Holdings Detail")
    
    # Format for display
    display_df = holdings_df[[
        'Scheme Name', 'Category', 'Folio', 'Units', 
        'Current NAV', 'Current Value', 'Unrealized Gain', 'XIRR'
    ]].copy()
    
    display_df['Current NAV'] = display_df['Current NAV'].apply(format_currency)
    display_df['Current Value'] = display_df['Current Value'].apply(format_currency)
    display_df['Unrealized Gain'] = display_df['Unrealized Gain'].apply(format_currency)
    display_df['XIRR'] = display_df['XIRR'].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "N/A")
    display_df['Units'] = display_df['Units'].apply(lambda x: f"{x:,.3f}")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        height=400
    )
    
    # Download option
    csv = holdings_df.to_csv(index=False)
    st.download_button(
        label="📥 Download Holdings as CSV",
        data=csv,
        file_name=f"portfolio_holdings_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )


def main():
    """Main application entry point."""
    init_session_state()
    render_sidebar()
    render_dashboard()


if __name__ == "__main__":
    main()
