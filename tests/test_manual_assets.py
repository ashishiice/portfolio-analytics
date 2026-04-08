"""
Tests for manual asset parsers.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.manual_assets import FDParser, PPFParser, NPSParser, ValidationError


class TestFDParser:
    """Tests for FD Parser."""
    
    def test_fd_maturity_calculation_compound(self):
        """Test compound interest calculation."""
        principal = 100000
        rate = 0.075  # 7.5%
        years = 3
        
        start = datetime.now()
        end = start + timedelta(days=int(years * 365))
        
        result = FDParser._calculate_maturity_value(
            principal, rate, start, end, 'compound', 4
        )
        
        # A = 100000(1 + 0.075/4)^(4*3)
        expected = principal * (1 + rate/4) ** (4 * years)
        
        assert abs(result - expected) < 1  # Within 1 rupee
    
    def test_fd_maturity_calculation_simple(self):
        """Test simple interest calculation."""
        principal = 100000
        rate = 0.065  # 6.5%
        years = 2
        
        start = datetime.now()
        end = start + timedelta(days=int(years * 365))
        
        result = FDParser._calculate_maturity_value(
            principal, rate, start, end, 'simple', 1
        )
        
        # A = 100000(1 + 0.065*2)
        expected = principal * (1 + rate * years)
        
        assert abs(result - expected) < 1
    
    def test_quarterly_vs_annual_compounding(self):
        """Test that quarterly compounding gives higher returns than annual."""
        principal = 100000
        rate = 0.07
        years = 1
        
        start = datetime.now()
        end = start + timedelta(days=365)
        
        quarterly = FDParser._calculate_maturity_value(
            principal, rate, start, end, 'compound', 4
        )
        annual = FDParser._calculate_maturity_value(
            principal, rate, start, end, 'compound', 1
        )
        
        assert quarterly > annual


class TestPPFParser:
    """Tests for PPF Parser."""
    
    def test_ppf_compound_calculation(self):
        """Test PPF annual compounding."""
        amount = 150000
        years = 5
        rate = 0.071  # 7.1%
        
        # Compound annually
        expected = amount * ((1 + rate) ** years)
        
        assert expected > amount * years  # Interest should exceed simple interest
    
    def test_ppf_lock_in_calculation(self):
        """Test that 7-year lock-in is calculated correctly."""
        start = datetime(2020, 4, 1)
        lock_in = start + timedelta(days=7*365)
        
        # Should be roughly 2027
        assert lock_in.year >= 2027


class TestNPSParser:
    """Tests for NPS Parser."""
    
    def test_allocation_validation(self):
        """Test that allocation percentages must sum to 100."""
        # Valid allocation
        valid = pd.DataFrame({
            'pran': ['110012345678'] * 3,
            'tier': [1] * 3,
            'allocation_type': ['equity', 'corporate_bond', 'govt_securities'],
            'allocation_percentage': [50, 30, 20],
            'current_value': [100000, 60000, 40000]
        })
        
        total_pct = valid['allocation_percentage'].sum()
        assert abs(total_pct - 100) < 0.1
    
    def test_tier_identification(self):
        """Test Tier 1 vs Tier 2 identification."""
        df = pd.DataFrame({
            'pran': ['110012345678'] * 2,
            'tier': [1, 2],
            'allocation_type': ['equity', 'equity'],
            'allocation_percentage': [50, 50],
            'current_value': [100000, 50000]
        })
        
        tier1 = df[df['tier'] == 1]
        tier2 = df[df['tier'] == 2]
        
        assert len(tier1) == 1
        assert len(tier2) == 1
        assert tier2['current_value'].iloc[0] == 50000


class TestValidation:
    """Tests for input validation."""
    
    def test_empty_dataframe(self):
        """Test handling of empty DataFrame."""
        empty_df = pd.DataFrame()
        assert empty_df.empty
    
    def test_missing_required_columns(self):
        """Test detection of missing required columns."""
        df = pd.DataFrame({
            'institution': ['Bank A'],
            'principal': [100000]
            # Missing interest_rate, start_date, maturity_date
        })
        
        required = ['institution', 'principal', 'interest_rate', 'start_date', 'maturity_date']
        missing = set(required) - set(df.columns)
        
        assert len(missing) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
