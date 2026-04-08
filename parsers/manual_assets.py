"""
Manual Asset Parsers for FD, PPF, NPS CSV files.
Calculates current values using appropriate financial formulas.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import yaml


# PPF historical interest rates (Government declared)
PPF_RATES = {
    2023: 7.1,
    2024: 7.1,
    2022: 7.1,
    2021: 7.1,
    2020: 7.1,
    2019: 8.0,
    2018: 7.6,
    2017: 7.6,
    2016: 8.1,
    2015: 8.7,
    2014: 8.7,
    2013: 8.7,
    2012: 8.8,
    2011: 8.6,
    2010: 8.0,
    2009: 8.0,
    2008: 8.0,
    2007: 8.0,
    2006: 8.0,
    2005: 8.0,
    2004: 8.0,
    2003: 8.0,
}


class ValidationError(Exception):
    """Custom validation error for manual asset parsing."""
    pass


class FDParser:
    """Parser and calculator for Fixed Deposit CSV files."""
    
    REQUIRED_COLUMNS = [
        'institution', 'principal', 'interest_rate', 
        'start_date', 'maturity_date'
    ]
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.df = None
        self.errors = []
        
    def _read_file(self) -> pd.DataFrame:
        """Read CSV or Excel file based on extension."""
        ext = self.file_path.suffix.lower()
        if ext in ['.xls', '.xlsx']:
            # Read first sheet for Excel files
            return pd.read_excel(self.file_path, sheet_name=0)
        else:
            return pd.read_csv(self.file_path)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """
        Validate FD CSV/Excel file.
        
        Returns:
            (is_valid, list of error messages)
        """
        self.errors = []
        
        if not self.file_path.exists():
            self.errors.append(f"File not found: {self.file_path}")
            return False, self.errors
        
        try:
            self.df = self._read_file()
        except Exception as e:
            self.errors.append(f"Cannot read file: {e}")
            return False, self.errors
        
        # Check required columns
        missing = set(self.REQUIRED_COLUMNS) - set(self.df.columns)
        if missing:
            self.errors.append(f"Missing required columns: {missing}")
            return False, self.errors
        
        # Validate data types and formats
        for idx, row in self.df.iterrows():
            row_num = idx + 2  # +2 for header and 1-indexing
            
            # Check principal is numeric and positive
            try:
                principal = float(row['principal'])
                if principal <= 0:
                    self.errors.append(f"Row {row_num}: Principal must be positive")
            except (ValueError, TypeError):
                self.errors.append(f"Row {row_num}: Principal must be numeric")
            
            # Check interest_rate is numeric
            try:
                rate = float(row['interest_rate'])
                if rate < 0 or rate > 20:
                    self.errors.append(f"Row {row_num}: Interest rate seems invalid (0-20% expected)")
            except (ValueError, TypeError):
                self.errors.append(f"Row {row_num}: Interest rate must be numeric")
            
            # Check date formats
            for date_col in ['start_date', 'maturity_date']:
                try:
                    if pd.notna(row[date_col]):
                        pd.to_datetime(row[date_col], format='%Y-%m-%d')
                except (ValueError, TypeError):
                    self.errors.append(f"Row {row_num}: {date_col} must be YYYY-MM-DD format")
        
        return len(self.errors) == 0, self.errors
    
    def parse(self) -> pd.DataFrame:
        """
        Parse and calculate current values for FDs.
        
        Returns:
            DataFrame with calculated current values
        """
        if self.df is None:
            is_valid, errors = self.validate()
            if not is_valid:
                raise ValidationError(f"Validation failed: {errors}")
        
        df = self.df.copy()
        today = datetime.now()
        
        # Calculate current value for each FD
        current_values = []
        
        for idx, row in df.iterrows():
            try:
                principal = float(row['principal'])
                rate = float(row['interest_rate']) / 100  # Convert to decimal
                start_date = pd.to_datetime(row['start_date'])
                maturity_date = pd.to_datetime(row['maturity_date'])
                
                # Get interest type and compounding frequency
                interest_type = str(row.get('interest_type', 'compound')).lower()
                compounding_freq = int(row.get('compounding_frequency', 4)) if pd.notna(row.get('compounding_frequency')) else 4
                
                if today >= maturity_date:
                    # FD has matured - calculate maturity value
                    current_val = self._calculate_maturity_value(
                        principal, rate, start_date, maturity_date, 
                        interest_type, compounding_freq
                    )
                elif today < start_date:
                    # FD hasn't started yet
                    current_val = principal
                else:
                    # FD is active - calculate accrued value
                    current_val = self._calculate_maturity_value(
                        principal, rate, start_date, today,
                        interest_type, compounding_freq
                    )
                
                current_values.append(round(current_val, 2))
                
            except Exception as e:
                current_values.append(None)
        
        df['calculated_current_value'] = current_values
        
        # Use calculated value if current_value column is empty
        if 'current_value' not in df.columns or df['current_value'].isna().all():
            df['current_value'] = df['calculated_current_value']
        
        return df
    
    @staticmethod
    def _calculate_maturity_value(
        principal: float, 
        rate: float, 
        start_date: datetime, 
        end_date: datetime,
        interest_type: str = 'compound',
        compounding_freq: int = 4
    ) -> float:
        """
        Calculate FD maturity value.
        
        Compound interest formula: A = P(1 + r/n)^(nt)
        Simple interest formula: A = P(1 + rt)
        
        Args:
            principal: Initial deposit amount
            rate: Annual interest rate (decimal, e.g., 0.075 for 7.5%)
            start_date: Deposit date
            end_date: Maturity or calculation date
            interest_type: 'compound' or 'simple'
            compounding_freq: Times per year (1=annual, 2=semi-annual, 4=quarterly, 12=monthly)
        
        Returns:
            Maturity value
        """
        years = (end_date - start_date).days / 365.25
        
        if interest_type == 'simple':
            # Simple interest: A = P(1 + rt)
            return principal * (1 + rate * years)
        else:
            # Compound interest: A = P(1 + r/n)^(nt)
            n = compounding_freq
            return principal * (1 + rate / n) ** (n * years)


class PPFParser:
    """Parser and calculator for PPF CSV files."""
    
    REQUIRED_COLUMNS = [
        'account_number', 'financial_year', 'deposit_date', 'amount'
    ]
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.df = None
        self.errors = []
    
    def _read_file(self) -> pd.DataFrame:
        """Read CSV or Excel file based on extension."""
        ext = self.file_path.suffix.lower()
        if ext in ['.xls', '.xlsx']:
            return pd.read_excel(self.file_path, sheet_name=0)
        else:
            return pd.read_csv(self.file_path)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate PPF CSV/Excel file."""
        self.errors = []
        
        if not self.file_path.exists():
            self.errors.append(f"File not found: {self.file_path}")
            return False, self.errors
        
        try:
            self.df = self._read_file()
        except Exception as e:
            self.errors.append(f"Cannot read file: {e}")
            return False, self.errors
        
        # Check required columns
        missing = set(self.REQUIRED_COLUMNS) - set(self.df.columns)
        if missing:
            self.errors.append(f"Missing required columns: {missing}")
            return False, self.errors
        
        # Validate data
        for idx, row in self.df.iterrows():
            row_num = idx + 2
            
            # Check amount is numeric and positive
            try:
                amount = float(row['amount'])
                if amount <= 0:
                    self.errors.append(f"Row {row_num}: Amount must be positive")
                if amount > 150000:
                    self.errors.append(f"Row {row_num}: PPF max annual contribution is INR 1.5L")
            except (ValueError, TypeError):
                self.errors.append(f"Row {row_num}: Amount must be numeric")
            
            # Check financial year
            try:
                fy = int(row['financial_year'])
                if fy < 2000 or fy > datetime.now().year + 1:
                    self.errors.append(f"Row {row_num}: Financial year seems invalid")
            except (ValueError, TypeError):
                self.errors.append(f"Row {row_num}: Financial year must be integer")
            
            # Check deposit date
            try:
                if pd.notna(row['deposit_date']):
                    pd.to_datetime(row['deposit_date'], format='%Y-%m-%d')
            except (ValueError, TypeError):
                self.errors.append(f"Row {row_num}: deposit_date must be YYYY-MM-DD format")
        
        return len(self.errors) == 0, self.errors
    
    def parse(self) -> pd.DataFrame:
        """Parse and calculate PPF balances with annual compounding."""
        if self.df is None:
            is_valid, errors = self.validate()
            if not is_valid:
                raise ValidationError(f"Validation failed: {errors}")
        
        df = self.df.copy()
        today = datetime.now()
        
        # Get PPF rate for current year
        current_year = today.year
        current_rate = PPF_RATES.get(current_year, 7.1) / 100
        
        # Group by account and calculate running balance
        accounts = df['account_number'].unique()
        results = []
        
        for account in accounts:
            account_df = df[df['account_number'] == account].copy()
            account_df = account_df.sort_values('financial_year')
            
            # Calculate balance with annual compounding
            balance = 0
            for idx, row in account_df.iterrows():
                fy = int(row['financial_year'])
                amount = float(row['amount'])
                
                # Apply interest for years between deposit and now
                years_elapsed = current_year - fy
                
                # Simple compounding calculation
                rate = PPF_RATES.get(fy, 7.1) / 100
                
                # PPF compounds annually at year-end
                # Interest calculated on lowest balance between 5th and end of month
                # Simplified: compound once per year at 7.1% (current rate)
                
                if years_elapsed > 0:
                    # Compound for completed years
                    compounded_amount = amount * ((1 + current_rate) ** years_elapsed)
                else:
                    compounded_amount = amount
                
                balance += compounded_amount
            
            # Add calculated balance to each row
            account_df['calculated_balance'] = round(balance, 2)
            
            # Calculate maturity date (15 years from first deposit)
            first_deposit = pd.to_datetime(account_df['deposit_date'].iloc[0])
            maturity_date = first_deposit + timedelta(days=15*365)
            
            # Partial withdrawal eligibility (7 years from first deposit)
            lock_in_end = first_deposit + timedelta(days=7*365)
            
            account_df['maturity_date_calculated'] = maturity_date.strftime('%Y-%m-%d')
            account_df['lock_in_end_calculated'] = lock_in_end.strftime('%Y-%m-%d')
            account_df['withdrawal_eligible'] = today > lock_in_end
            
            results.append(account_df)
        
        if results:
            final_df = pd.concat(results, ignore_index=True)
            
            # Use calculated values if columns are empty
            if 'current_balance' not in final_df.columns or final_df['current_balance'].isna().all():
                final_df['current_balance'] = final_df['calculated_balance']
            if 'interest_rate' not in final_df.columns or final_df['interest_rate'].isna().all():
                final_df['interest_rate'] = current_rate * 100
                
            return final_df
        
        return df
    
    def get_account_summary(self) -> pd.DataFrame:
        """Get summary by account number with total balance."""
        df = self.parse()
        
        summary = df.groupby('account_number').agg({
            'amount': 'sum',
            'calculated_balance': 'last',
            'maturity_date_calculated': 'first',
            'lock_in_end_calculated': 'first',
            'withdrawal_eligible': 'first',
            'notes': 'first'
        }).reset_index()
        
        return summary


class NPSParser:
    """Parser and calculator for NPS CSV files."""
    
    REQUIRED_COLUMNS = [
        'pran', 'tier', 'allocation_type', 'allocation_percentage', 'current_value'
    ]
    
    VALID_ALLOCATIONS = ['equity', 'corporate_bond', 'govt_securities', 'alternate', 'g', 'c', 'e', 'a']
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.df = None
        self.errors = []
    
    def _read_file(self) -> pd.DataFrame:
        """Read CSV or Excel file based on extension."""
        ext = self.file_path.suffix.lower()
        if ext in ['.xls', '.xlsx']:
            return pd.read_excel(self.file_path, sheet_name=0)
        else:
            return pd.read_csv(self.file_path)
    
    def validate(self) -> Tuple[bool, List[str]]:
        """Validate NPS CSV/Excel file."""
        self.errors = []
        
        if not self.file_path.exists():
            self.errors.append(f"File not found: {self.file_path}")
            return False, self.errors
        
        try:
            self.df = self._read_file()
        except Exception as e:
            self.errors.append(f"Cannot read file: {e}")
            return False, self.errors
        
        # Check required columns
        missing = set(self.REQUIRED_COLUMNS) - set(self.df.columns)
        if missing:
            self.errors.append(f"Missing required columns: {missing}")
            return False, self.errors
        
        # Validate each row
        for idx, row in self.df.iterrows():
            row_num = idx + 2
            
            # Check PRAN format (12 digits)
            pran = str(row['pran'])
            if not pran.isdigit() or len(pran) != 12:
                self.errors.append(f"Row {row_num}: PRAN must be 12 digits")
            
            # Check tier
            try:
                tier = int(row['tier'])
                if tier not in [1, 2]:
                    self.errors.append(f"Row {row_num}: Tier must be 1 or 2")
            except (ValueError, TypeError):
                self.errors.append(f"Row {row_num}: Tier must be 1 or 2")
            
            # Check allocation type
            allocation = str(row['allocation_type']).lower()
            if allocation not in self.VALID_ALLOCATIONS:
                self.errors.append(f"Row {row_num}: Invalid allocation_type. Use: {self.VALID_ALLOCATIONS}")
            
            # Check allocation percentage
            try:
                pct = float(row['allocation_percentage'])
                if pct < 0 or pct > 100:
                    self.errors.append(f"Row {row_num}: Allocation percentage must be 0-100")
            except (ValueError, TypeError):
                self.errors.append(f"Row {row_num}: Allocation percentage must be numeric")
            
            # Check current value
            try:
                val = float(row['current_value'])
                if val < 0:
                    self.errors.append(f"Row {row_num}: Current value cannot be negative")
            except (ValueError, TypeError):
                self.errors.append(f"Row {row_num}: Current value must be numeric")
        
        # Check allocation percentages sum to 100% per PRAN+Tier
        if len(self.errors) == 0:
            df = self.df.copy()
            df['pran_tier'] = df['pran'].astype(str) + '_T' + df['tier'].astype(str)
            
            for pran_tier, group in df.groupby('pran_tier'):
                total_pct = group['allocation_percentage'].sum()
                if abs(total_pct - 100) > 0.1:  # Allow 0.1% rounding error
                    self.errors.append(f"PRAN {pran_tier}: Allocation percentages sum to {total_pct}%, should be 100%")
        
        return len(self.errors) == 0, self.errors
    
    def parse(self) -> pd.DataFrame:
        """Parse NPS data and aggregate by PRAN and Tier."""
        if self.df is None:
            is_valid, errors = self.validate()
            if not is_valid:
                raise ValidationError(f"Validation failed: {errors}")
        
        df = self.df.copy()
        
        # Normalize allocation types
        allocation_map = {
            'e': 'equity', 'equity': 'equity',
            'c': 'corporate_bond', 'corporate_bond': 'corporate_bond',
            'g': 'govt_securities', 'govt_securities': 'govt_securities',
            'a': 'alternate', 'alternate': 'alternate'
        }
        df['allocation_type'] = df['allocation_type'].str.lower().map(allocation_map)
        
        # Calculate tier totals
        tier_summary = df.groupby(['pran', 'tier']).agg({
            'current_value': 'sum',
            'contributions_ytd': 'sum',
            'returns_since_inception': 'mean',
            'notes': 'first'
        }).reset_index()
        
        tier_summary['tier_name'] = tier_summary['tier'].map({1: 'Tier 1 (Retirement)', 2: 'Tier 2 (Flexible)'})
        tier_summary['is_withdrawable'] = tier_summary['tier'] == 2
        
        return tier_summary
    
    def get_allocation_breakdown(self) -> pd.DataFrame:
        """Get detailed allocation breakdown by asset class."""
        df = self.parse()
        
        # Get detailed allocation
        detailed = self.df.copy()
        allocation_map = {
            'e': 'equity', 'equity': 'equity',
            'c': 'corporate_bond', 'corporate_bond': 'corporate_bond',
            'g': 'govt_securities', 'govt_securities': 'govt_securities',
            'a': 'alternate', 'alternate': 'alternate'
        }
        detailed['allocation_type'] = detailed['allocation_type'].str.lower().map(allocation_map)
        
        # Calculate value by allocation type
        detailed['allocation_value'] = (
            detailed['current_value'] * detailed['allocation_percentage'] / 100
        )
        
        return detailed


def parse_manual_asset(asset_type: str, file_path: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    Universal parser dispatcher for manual assets.
    
    Args:
        asset_type: 'fd', 'ppf', or 'nps'
        file_path: Path to CSV file
    
    Returns:
        (DataFrame, list of validation errors if any)
    """
    asset_type = asset_type.lower()
    
    try:
        if asset_type == 'fd':
            parser = FDParser(file_path)
            is_valid, errors = parser.validate()
            if not is_valid:
                return pd.DataFrame(), errors
            return parser.parse(), []
            
        elif asset_type == 'ppf':
            parser = PPFParser(file_path)
            is_valid, errors = parser.validate()
            if not is_valid:
                return pd.DataFrame(), errors
            return parser.parse(), []
            
        elif asset_type == 'nps':
            parser = NPSParser(file_path)
            is_valid, errors = parser.validate()
            if not is_valid:
                return pd.DataFrame(), errors
            return parser.parse(), []
            
        else:
            return pd.DataFrame(), [f"Unknown asset type: {asset_type}"]
            
    except ValidationError as e:
        return pd.DataFrame(), [str(e)]
    except Exception as e:
        return pd.DataFrame(), [f"Parsing error: {e}"]


def get_upcoming_maturities(fds_df: pd.DataFrame, days: int = 90) -> pd.DataFrame:
    """
    Get FDs maturing within specified days.
    
    Args:
        fds_df: DataFrame with FD data (must have maturity_date column)
        days: Number of days to look ahead
    
    Returns:
        DataFrame with upcoming maturities
    """
    if fds_df.empty or 'maturity_date' not in fds_df.columns:
        return pd.DataFrame()
    
    today = datetime.now()
    cutoff = today + timedelta(days=days)
    
    fds_df['maturity_date'] = pd.to_datetime(fds_df['maturity_date'])
    
    upcoming = fds_df[
        (fds_df['maturity_date'] >= today) & 
        (fds_df['maturity_date'] <= cutoff)
    ].copy()
    
    upcoming['days_to_maturity'] = (upcoming['maturity_date'] - today).dt.days
    
    return upcoming.sort_values('maturity_date')


def get_ppf_withdrawal_eligible(ppf_df: pd.DataFrame) -> pd.DataFrame:
    """
    Get PPF accounts eligible for partial withdrawal.
    
    PPF allows partial withdrawal after 7 years from account opening.
    Maximum 50% of balance at end of 4th preceding year or preceding year, whichever is lower.
    
    Args:
        ppf_df: DataFrame with PPF data
    
    Returns:
        DataFrame with eligible accounts
    """
    if ppf_df.empty:
        return pd.DataFrame()
    
    today = datetime.now()
    
    # Check for calculated column or use lock_in_end
    if 'lock_in_end_calculated' in ppf_df.columns:
        ppf_df['lock_in_end'] = pd.to_datetime(ppf_df['lock_in_end_calculated'])
    elif 'lock_in_end' in ppf_df.columns:
        ppf_df['lock_in_end'] = pd.to_datetime(ppf_df['lock_in_end'])
    else:
        return pd.DataFrame()
    
    eligible = ppf_df[ppf_df['lock_in_end'] <= today].copy()
    
    if not eligible.empty and 'calculated_balance' in eligible.columns:
        # Estimate max withdrawal (50% of balance, simplified)
        eligible['max_withdrawal'] = eligible['calculated_balance'] * 0.5
    
    return eligible
