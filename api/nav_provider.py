"""
Abstract Base Class for NAV Providers
Defines the interface for fetching NAV data from various sources.
"""

from abc import ABC, abstractmethod
from datetime import datetime, date
from typing import Optional, List, Dict, Any
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class NavProvider(ABC):
    """
    Abstract base class for NAV data providers.
    
    Implementations should provide methods to fetch current and historical
    NAV data for mutual funds identified by ISIN.
    """
    
    def __init__(self, name: str, source_url: Optional[str] = None):
        """
        Initialize the NAV provider.
        
        Args:
            name: Name of the provider
            source_url: Base URL for the data source
        """
        self.name = name
        self.source_url = source_url
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def get_nav(self, isin: str, nav_date: Optional[str] = None) -> Optional[float]:
        """
        Get NAV for a specific ISIN and date.
        
        Args:
            isin: ISIN code of the mutual fund
            nav_date: Date in 'YYYY-MM-DD' format. If None, returns latest NAV.
        
        Returns:
            NAV value as float, or None if not available
        """
        pass
    
    @abstractmethod
    def get_historical_nav(
        self, 
        isin: str, 
        from_date: str, 
        to_date: str
    ) -> pd.DataFrame:
        """
        Get historical NAV data for a date range.
        
        Args:
            isin: ISIN code of the mutual fund
            from_date: Start date in 'YYYY-MM-DD' format
            to_date: End date in 'YYYY-MM-DD' format
        
        Returns:
            DataFrame with columns: ['date', 'nav']
        """
        pass
    
    @abstractmethod
    def get_latest_navs(self) -> pd.DataFrame:
        """
        Get latest NAV for all available schemes.
        
        Returns:
            DataFrame with columns: ['isin', 'scheme_name', 'nav', 'date', ...]
        """
        pass
    
    def get_scheme_info(self, isin: str) -> Optional[Dict[str, Any]]:
        """
        Get scheme information for an ISIN.
        
        Args:
            isin: ISIN code of the mutual fund
        
        Returns:
            Dictionary with scheme details, or None if not found
        """
        # Default implementation - override for providers with scheme info
        return None
    
    def search_schemes(self, keyword: str) -> pd.DataFrame:
        """
        Search for schemes by keyword.
        
        Args:
            keyword: Search term
        
        Returns:
            DataFrame with matching schemes
        """
        # Default implementation - returns empty DataFrame
        return pd.DataFrame()
    
    def is_available(self) -> bool:
        """
        Check if the provider is available and accessible.
        
        Returns:
            True if provider is available
        """
        try:
            # Try to fetch latest NAVs
            df = self.get_latest_navs()
            return len(df) > 0
        except Exception as e:
            self.logger.error(f"Provider availability check failed: {e}")
            return False
    
    def validate_isin(self, isin: str) -> bool:
        """
        Validate ISIN format.
        
        Args:
            isin: ISIN code to validate
        
        Returns:
            True if valid ISIN format
        """
        # ISIN format: 2 letters (country) + 9 alphanumeric (NSDL) + 1 check digit
        if not isin or len(isin) != 12:
            return False
        
        # Country code for India
        if not isin.startswith('IN'):
            return False
        
        # Check alphanumeric
        if not isin[2:11].isalnum():
            return False
        
        return True
    
    def _parse_date(self, date_str: str) -> Optional[date]:
        """
        Parse date string to date object.
        
        Args:
            date_str: Date string in various formats
        
        Returns:
            date object or None
        """
        formats = [
            '%Y-%m-%d',
            '%d-%m-%Y',
            '%d/%m/%Y',
            '%Y/%m/%d',
            '%d-%b-%Y',
            '%d-%B-%Y'
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        return None


class NavProviderError(Exception):
    """Base exception for NAV provider errors."""
    pass


class IsinNotFoundError(NavProviderError):
    """Raised when ISIN is not found in provider data."""
    pass


class DateNotFoundError(NavProviderError):
    """Raised when NAV is not available for requested date."""
    pass


class ProviderUnavailableError(NavProviderError):
    """Raised when provider is unavailable."""
    pass


# Example concrete implementation for testing
class MockNavProvider(NavProvider):
    """Mock provider for testing purposes."""
    
    def __init__(self, mock_data: Optional[Dict] = None):
        super().__init__("MockProvider", "mock://localhost")
        self.mock_data = mock_data or {}
    
    def get_nav(self, isin: str, nav_date: Optional[str] = None) -> Optional[float]:
        """Get NAV from mock data."""
        if isin not in self.mock_data:
            return None
        
        data = self.mock_data[isin]
        if nav_date:
            return data.get('historical', {}).get(nav_date, data.get('latest'))
        return data.get('latest')
    
    def get_historical_nav(
        self, 
        isin: str, 
        from_date: str, 
        to_date: str
    ) -> pd.DataFrame:
        """Get historical NAV from mock data."""
        if isin not in self.mock_data:
            return pd.DataFrame(columns=['date', 'nav'])
        
        historical = self.mock_data[isin].get('historical', {})
        
        # Filter by date range
        filtered = {
            d: v for d, v in historical.items()
            if from_date <= d <= to_date
        }
        
        return pd.DataFrame([
            {'date': d, 'nav': v} for d, v in filtered.items()
        ]).sort_values('date')
    
    def get_latest_navs(self) -> pd.DataFrame:
        """Get latest NAVs from mock data."""
        data = []
        for isin, info in self.mock_data.items():
            data.append({
                'isin': isin,
                'scheme_name': info.get('scheme_name', 'Unknown'),
                'nav': info.get('latest', 0),
                'date': info.get('date', datetime.now().strftime('%Y-%m-%d'))
            })
        return pd.DataFrame(data)


if __name__ == "__main__":
    # Test the mock provider
    print("Testing NavProvider...")
    
    # Create mock data
    mock_data = {
        "INF209K01UT8": {
            'scheme_name': 'Test Fund 1',
            'latest': 100.5,
            'date': '2024-01-15',
            'historical': {
                '2024-01-01': 100.0,
                '2024-01-15': 100.5
            }
        },
        "INF209K01UU6": {
            'scheme_name': 'Test Fund 2',
            'latest': 50.25,
            'date': '2024-01-15',
            'historical': {
                '2024-01-01': 50.0,
                '2024-01-15': 50.25
            }
        }
    }
    
    provider = MockNavProvider(mock_data)
    
    # Test get_nav
    nav = provider.get_nav("INF209K01UT8")
    print(f"Latest NAV for INF209K01UT8: {nav}")
    
    nav = provider.get_nav("INF209K01UT8", "2024-01-01")
    print(f"NAV for INF209K01UT8 on 2024-01-01: {nav}")
    
    # Test get_latest_navs
    df = provider.get_latest_navs()
    print(f"\nLatest NAVs:\n{df}")
    
    # Test get_historical_nav
    df = provider.get_historical_nav("INF209K01UT8", "2024-01-01", "2024-01-15")
    print(f"\nHistorical NAV:\n{df}")
    
    # Test ISIN validation
    print(f"\nISIN validation:")
    print(f"INF209K01UT8 valid: {provider.validate_isin('INF209K01UT8')}")
    print(f"US1234567890 valid: {provider.validate_isin('US1234567890')}")
    print(f"INF209K01U invalid: {provider.validate_isin('INF209K01U')}")
