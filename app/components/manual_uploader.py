"""
Streamlit Component for Manual Asset CSV Upload.
Handles FD, PPF, NPS uploads with validation, preview, and database save.
"""

import pandas as pd
from pathlib import Path
from typing import Optional, Dict, List, Tuple
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from parsers.manual_assets import FDParser, PPFParser, NPSParser, ValidationError
from utils.database import get_db

# Streamlit is optional - only needed for UI
try:
    import streamlit as st
    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False
    st = None


class ManualAssetUploader:
    """Streamlit component for uploading manual assets."""
    
    ASSET_TYPES = {
        'FD': {
            'name': 'Fixed Deposits',
            'description': 'Bank and post office fixed deposits',
            'template': 'templates/fd_template.csv',
            'parser': FDParser,
            'db_type': 'fd'
        },
        'PPF': {
            'name': 'Public Provident Fund',
            'description': 'PPF accounts with yearly contribution tracking',
            'template': 'templates/ppf_template.csv',
            'parser': PPFParser,
            'db_type': 'ppf'
        },
        'NPS': {
            'name': 'National Pension System',
            'description': 'NPS Tier 1 & Tier 2 allocations',
            'template': 'templates/nps_template.csv',
            'parser': NPSParser,
            'db_type': 'nps'
        }
    }
    
    def __init__(self):
        self.db = get_db()
        self.uploaded_data: Dict[str, pd.DataFrame] = {}
        self.validation_errors: Dict[str, List[str]] = {}
    
    def render(self):
        """Render the uploader component in Streamlit."""
        if not HAS_STREAMLIT or st is None:
            print("ERROR: Streamlit not available. Install with: pip install streamlit")
            return
        st.header("📤 Manual Asset Upload")
        st.markdown("Upload CSV files for non-Mutual Fund assets (FD, PPF, NPS)")
        
        # Tabs for different asset types
        tabs = st.tabs([f"{info['name']}" for info in self.ASSET_TYPES.values()])
        
        for idx, (asset_code, asset_info) in enumerate(self.ASSET_TYPES.items()):
            with tabs[idx]:
                self._render_asset_upload(asset_code, asset_info)
        
        # Summary section
        if self.uploaded_data:
            st.divider()
            st.subheader("📊 Upload Summary")
            self._render_summary()
    
    def _render_asset_upload(self, asset_code: str, asset_info: Dict):
        """Render upload section for a specific asset type."""
        st.markdown(f"**{asset_info['description']}**")
        
        # Download template button
        template_path = Path(asset_info['template'])
        if template_path.exists():
            with open(template_path, 'r') as f:
                template_content = f.read()
            st.download_button(
                label=f"📥 Download {asset_code} Template",
                data=template_content,
                file_name=f"{asset_code.lower()}_template.csv",
                mime="text/csv",
                key=f"download_{asset_code}"
            )
        
        # File uploader
        uploaded_file = st.file_uploader(
            f"Upload {asset_code} CSV or Excel",
            type=['csv', 'xls', 'xlsx'],
            key=f"upload_{asset_code}"
        )
        
        if uploaded_file is not None:
            self._process_upload(asset_code, asset_info, uploaded_file)
    
    def _process_upload(self, asset_code: str, asset_info: Dict, uploaded_file):
        """Process uploaded file with validation and preview."""
        st.subheader("🔍 Validation & Preview")
        
        # Determine file extension from uploaded file name
        file_name = uploaded_file.name
        file_ext = file_name.split('.')[-1].lower() if '.' in file_name else 'csv'
        
        # Save uploaded file temporarily with correct extension
        temp_path = f"/tmp/uploaded_{asset_code.lower()}.{file_ext}"
        with open(temp_path, 'wb') as f:
            f.write(uploaded_file.getvalue())
        
        # Validate
        parser_class = asset_info['parser']
        parser = parser_class(temp_path)
        
        is_valid, errors = parser.validate()
        
        if not is_valid:
            self.validation_errors[asset_code] = errors
            st.error("❌ Validation Failed")
            for error in errors:
                st.error(f"• {error}")
            return
        
        # Validation passed
        st.success(f"✅ Validation Passed - {len(parser.df)} records found")
        
        # Parse and calculate
        try:
            df = parser.parse()
            self.uploaded_data[asset_code] = df
            
            # Show preview
            st.markdown("**Preview:**")
            
            # Select columns for display based on asset type
            if asset_code == 'FD':
                display_cols = ['institution', 'principal', 'interest_rate', 
                              'maturity_date', 'calculated_current_value']
            elif asset_code == 'PPF':
                display_cols = ['account_number', 'financial_year', 'amount', 
                              'calculated_balance', 'lock_in_end_calculated']
            else:  # NPS
                display_cols = ['pran', 'tier', 'allocation_type', 
                              'allocation_percentage', 'current_value']
            
            # Show only available columns
            display_cols = [c for c in display_cols if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True)
            
            # Show totals
            if asset_code == 'FD':
                total = df['calculated_current_value'].sum()
                st.metric("Total FD Value", f"₹{total:,.0f}")
            elif asset_code == 'PPF':
                # Get unique accounts and their latest balance
                if 'account_number' in df.columns:
                    summary = df.groupby('account_number')['calculated_balance'].last()
                    for acct, bal in summary.items():
                        st.metric(f"PPF {acct}", f"₹{bal:,.0f}")
            elif asset_code == 'NPS':
                tier1 = df[df['tier'] == 1]['current_value'].sum()
                tier2 = df[df['tier'] == 2]['current_value'].sum()
                col1, col2 = st.columns(2)
                col1.metric("Tier 1 (Locked)", f"₹{tier1:,.0f}")
                col2.metric("Tier 2 (Liquid)", f"₹{tier2:,.0f}")
            
            # Save button
            if st.button(f"💾 Save {asset_code} to Database", key=f"save_{asset_code}"):
                self._save_to_database(asset_code, asset_info, df)
                
        except ValidationError as e:
            st.error(f"Parsing error: {e}")
        except Exception as e:
            st.error(f"Error processing file: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    def _save_to_database(self, asset_code: str, asset_info: Dict, df: pd.DataFrame):
        """Save parsed data to database."""
        db_type = asset_info['db_type']
        
        try:
            records_added = 0
            
            if asset_code == 'FD':
                for idx, row in df.iterrows():
                    data = {
                        'institution': row['institution'],
                        'account_number': str(row.get('account_number', '')),
                        'principal': float(row['principal']),
                        'interest_rate': float(row['interest_rate']),
                        'start_date': row['start_date'],
                        'maturity_date': row['maturity_date'],
                        'interest_type': str(row.get('interest_type', 'compound')),
                        'compounding_frequency': int(row.get('compounding_frequency', 4)),
                        'current_value': float(row.get('calculated_current_value', row.get('current_value', 0))),
                        'notes': str(row.get('notes', ''))
                    }
                    self.db.add_manual_asset('fd', data)
                    records_added += 1
                    
            elif asset_code == 'PPF':
                for idx, row in df.iterrows():
                    data = {
                        'account_number': str(row['account_number']),
                        'financial_year': int(row['financial_year']),
                        'deposit_date': row['deposit_date'],
                        'amount': float(row['amount']),
                        'interest_rate': float(row.get('interest_rate', 7.1)),
                        'current_balance': float(row.get('calculated_balance', row.get('current_balance', 0))),
                        'maturity_date': row.get('maturity_date', row.get('maturity_date_calculated')),
                        'lock_in_end': row.get('lock_in_end', row.get('lock_in_end_calculated')),
                        'notes': str(row.get('notes', ''))
                    }
                    self.db.add_manual_asset('ppf', data)
                    records_added += 1
                    
            elif asset_code == 'NPS':
                for idx, row in df.iterrows():
                    data = {
                        'pran': str(row['pran']),
                        'tier': int(row['tier']),
                        'allocation_type': str(row['allocation_type']),
                        'allocation_percentage': float(row['allocation_percentage']),
                        'current_value': float(row['current_value']),
                        'contributions_ytd': float(row.get('contributions_ytd', 0)),
                        'returns_since_inception': float(row.get('returns_since_inception', 0)),
                        'notes': str(row.get('notes', ''))
                    }
                    self.db.add_manual_asset('nps', data)
                    records_added += 1
            
            st.success(f"✅ Saved {records_added} {asset_code} records to database!")
            
        except Exception as e:
            st.error(f"❌ Error saving to database: {e}")
            import traceback
            st.code(traceback.format_exc())
    
    def _render_summary(self):
        """Render summary of all uploaded data."""
        total_value = 0
        
        for asset_code, df in self.uploaded_data.items():
            if asset_code == 'FD':
                value = df['calculated_current_value'].sum()
            elif asset_code == 'PPF':
                value = df['calculated_balance'].sum()
            else:  # NPS
                value = df['current_value'].sum()
            
            total_value += value
            st.write(f"• {self.ASSET_TYPES[asset_code]['name']}: ₹{value:,.0f}")
        
        st.metric("Total Manual Assets Value", f"₹{total_value:,.0f}")
    
    def get_uploaded_summary(self) -> Dict:
        """Get summary of uploaded data for use in other components."""
        summary = {
            'uploaded_types': list(self.uploaded_data.keys()),
            'total_records': sum(len(df) for df in self.uploaded_data.values()),
            'total_value': 0
        }
        
        for asset_code, df in self.uploaded_data.items():
            if asset_code == 'FD':
                value = df['calculated_current_value'].sum()
            elif asset_code == 'PPF':
                value = df['calculated_balance'].sum()
            else:  # NPS
                value = df['current_value'].sum()
            
            summary['total_value'] += value
            summary[f'{asset_code.lower()}_value'] = value
        
        return summary


def render_manual_uploader():
    """Standalone function to render the uploader component."""
    uploader = ManualAssetUploader()
    uploader.render()
    return uploader


# For standalone testing
if __name__ == "__main__":
    st.set_page_config(page_title="Manual Asset Uploader", layout="wide")
    render_manual_uploader()
