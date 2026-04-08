"""
AMFI India NAV Provider Implementation
Fetches NAV data from AMFI India website.
"""

import requests
import pandas as pd
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any
from io import StringIO
import re
import logging

from api.nav_provider import NavProvider, IsinNotFoundError, DateNotFoundError, ProviderUnavailableError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AmfiProvider(NavProvider):
    """
    AMFI India NAV Provider.
    
    Fetches NAV data from https://www.amfiindia.com/spages/NAVAll.txt
    Uses the pipe-delimited format provided by AMFI.
    """
    
    AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
    
    def __init__(self, cache_enabled: bool = True, cache_duration: int = 300):
        """
        Initialize AMFI provider.
        
        Args:
            cache_enabled: Whether to cache NAV data
            cache_duration: Cache duration in seconds (default: 5 minutes)
        """
        super().__init__("AMFI India", self.AMFI_NAV_URL)
        self.cache_enabled = cache_enabled
        self.cache_duration = cache_duration
        self._cache: Optional[pd.DataFrame] = None
        self._cache_timestamp: Optional[datetime] = None
    
    def _fetch_nav_data(self) -> pd.DataFrame:
        """
        Fetch NAV data from AMFI website.
        
        Returns:
            DataFrame with columns: [amc, scheme_code, scheme_name, isin, nav, date, ...]
        """
        try:
            logger.info(f"Fetching NAV data from {self.AMFI_NAV_URL}")
            response = requests.get(self.AMFI_NAV_URL, timeout=30)
            response.raise_for_status()
            
            # Parse the pipe-delimited format
            nav_data = self._parse_nav_txt(response.text)
            
            self.logger.info(f"Fetched {len(nav_data)} NAV records")
            return nav_data
            
        except requests.RequestException as e:
            logger.error(f"Failed to fetch NAV data: {e}")
            raise ProviderUnavailableError(f"Failed to fetch NAV data: {e}")
    
    def _parse_nav_txt(self, text: str) -> pd.DataFrame:
        """
        Parse AMFI NAV text format.
        
        The format is pipe-delimited with the following structure:
        Scheme Code;Scheme Name;ISIN Div Payout/ISIN Growth;ISIN Div Reinvestment;Net Asset Value;Repurchase Price;Sale Price;Date
        
        Args:
            text: Raw text from AMFI website
        
        Returns:
            DataFrame with parsed NAV data
        """
        records = []
        lines = text.strip().split('\n')
        
        current_amc = ""
        current_date = ""
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Check if line contains AMC name (no pipes)
            if ';' not in line and not line.startswith('Scheme'):
                current_amc = line.strip()
                continue
            
            # Skip header lines
            if line.startswith('Scheme') or line.startswith('ISIN'):
                continue
            
            # Parse NAV record
            parts = line.split(';')
            if len(parts) >= 5:
                try:
                    scheme_code = parts[0].strip()
                    scheme_name = parts[1].strip()
                    isin_payout = parts[2].strip()
                    isin_reinvest = parts[3].strip()
                    nav_str = parts[4].strip()
                    date_str = parts[7].strip() if len(parts) > 7 else ""
                    
                    # Use the payout ISIN if available, else reinvestment ISIN
                    isin = isin_payout if isin_payout else isin_reinvest
                    
                    if isin and nav_str and nav_str != 'N.A.':
                        try:
                            nav = float(nav_str)
                            
                            # Parse date
                            if date_str:
                                try:
                                    nav_date = datetime.strptime(date_str, '%d-%b-%Y').strftime('%Y-%m-%d')
                                except ValueError:
                                    nav_date = date_str
                            else:
                                nav_date = datetime.now().strftime('%Y-%m-%d')
                            
                            records.append({
                                'amc': current_amc,
                                'scheme_code': scheme_code,
                                'scheme_name': scheme_name,
                                'isin': isin,
                                'isin_payout': isin_payout,
                                'isin_reinvest': isin_reinvest,
                                'nav': nav,
                                'date': nav_date,
                                'nav_date': nav_date
                            })
                        except ValueError:
                            continue
                except Exception as e:
                    logger.debug(f"Error parsing line: {line}, error: {e}")
                    continue
        
        return pd.DataFrame(records)
    
    def _get_cached_or_fetch(self) -> pd.DataFrame:
        """Get cached data or fetch fresh."""
        if not self.cache_enabled:
            return self._fetch_nav_data()
        
        now = datetime.now()
        if (self._cache is None or self._cache_timestamp is None or
            (now - self._cache_timestamp).seconds > self.cache_duration):
            self._cache = self._fetch_nav_data()
            self._cache_timestamp = now
            logger.info(f"NAV cache refreshed at {now}")
        
        return self._cache
    
    def get_nav(self, isin: str, nav_date: Optional[str] = None) -> Optional[float]:
        """
        Get NAV for a specific ISIN and date.
        
        Args:
            isin: ISIN code of the mutual fund
            nav_date: Date in 'YYYY-MM-DD' format. If None, returns latest NAV.
        
        Returns:
            NAV value as float, or None if not available
        """
        if not self.validate_isin(isin):
            logger.warning(f"Invalid ISIN format: {isin}")
            return None
        
        try:
            df = self._get_cached_or_fetch()
            
            # Filter by ISIN
            isin_data = df[df['isin'] == isin]
            
            if isin_data.empty:
                logger.warning(f"ISIN not found: {isin}")
                return None
            
            if nav_date:
                # Return NAV for specific date
                date_data = isin_data[isin_data['date'] == nav_date]
                if not date_data.empty:
                    return float(date_data.iloc[0]['nav'])
                
                # Try alternative date formats
                alt_formats = [
                    nav_date,  # YYYY-MM-DD
                    datetime.strptime(nav_date, '%Y-%m-%d').strftime('%d-%b-%Y').upper(),
                    datetime.strptime(nav_date, '%Y-%m-%d').strftime('%d-%b-%y').upper()
                ]
                for alt_date in alt_formats:
                    date_data = isin_data[isin_data['date'] == alt_date]
                    if not date_data.empty:
                        return float(date_data.iloc[0]['nav'])
                
                logger.warning(f"NAV not found for ISIN {isin} on date {nav_date}")
                return None
            else:
                # Return latest NAV (first record after sorting by date desc)
                latest = isin_data.sort_values('date', ascending=False).iloc[0]
                return float(latest['nav'])
                
        except Exception as e:
            logger.error(f"Error getting NAV: {e}")
            return None
    
    def get_historical_nav(
        self, 
        isin: str, 
        from_date: str, 
        to_date: str
    ) -> pd.DataFrame:
        """
        Get historical NAV data for a date range.
        
        Note: AMFI only provides latest NAV data. For historical data,
        you would need to use a different provider or maintain your own history.
        
        Args:
            isin: ISIN code of the mutual fund
            from_date: Start date in 'YYYY-MM-DD' format
            to_date: End date in 'YYYY-MM-DD' format
        
        Returns:
            DataFrame with columns: ['date', 'nav']
        """
        logger.warning("AMFI provider does not provide historical NAV data")
        
        # Return latest NAV only
        latest_nav = self.get_nav(isin)
        if latest_nav:
            today = datetime.now().strftime('%Y-%m-%d')
            return pd.DataFrame([{
                'date': today,
                'nav': latest_nav
            }])
        
        return pd.DataFrame(columns=['date', 'nav'])
    
    def get_latest_navs(self) -> pd.DataFrame:
        """
        Get latest NAV for all available schemes.
        
        Returns:
            DataFrame with columns: ['isin', 'scheme_name', 'amc', 'nav', 'date']
        """
        df = self._get_cached_or_fetch()
        
        # Get latest entry for each ISIN
        latest = df.sort_values('date', ascending=False).groupby('isin').first().reset_index()
        
        return latest[['isin', 'scheme_name', 'amc', 'nav', 'date']].copy()
    
    def get_scheme_info(self, isin: str) -> Optional[Dict[str, Any]]:
        """
        Get scheme information for an ISIN.
        
        Args:
            isin: ISIN code of the mutual fund
        
        Returns:
            Dictionary with scheme details, or None if not found
        """
        df = self._get_cached_or_fetch()
        isin_data = df[df['isin'] == isin]
        
        if isin_data.empty:
            return None
        
        latest = isin_data.sort_values('date', ascending=False).iloc[0]
        
        return {
            'isin': latest['isin'],
            'scheme_name': latest['scheme_name'],
            'amc': latest['amc'],
            'scheme_code': latest['scheme_code'],
            'latest_nav': float(latest['nav']),
            'nav_date': latest['date'],
            'isin_payout': latest.get('isin_payout', ''),
            'isin_reinvest': latest.get('isin_reinvest', '')
        }
    
    def search_schemes(self, keyword: str) -> pd.DataFrame:
        """
        Search for schemes by keyword.
        
        Args:
            keyword: Search term (scheme name, ISIN, or AMC)
        
        Returns:
            DataFrame with matching schemes
        """
        df = self._get_cached_or_fetch()
        
        keyword_lower = keyword.lower()
        
        # Search in scheme name, ISIN, and AMC
        mask = (
            df['scheme_name'].str.lower().str.contains(keyword_lower, na=False) |
            df['isin'].str.contains(keyword, na=False) |
            df['amc'].str.lower().str.contains(keyword_lower, na=False)
        )
        
        results = df[mask].sort_values('date', ascending=False).groupby('isin').first().reset_index()
        
        return results[['isin', 'scheme_name', 'amc', 'nav', 'date']].copy()
    
    def get_all_amcs(self) -> List[str]:
        """Get list of all AMCs in the data."""
        df = self._get_cached_or_fetch()
        return sorted(df['amc'].unique().tolist())
    
    def clear_cache(self):
        """Clear the NAV cache."""
        self._cache = None
        self._cache_timestamp = None
        logger.info("NAV cache cleared")


def get_amfi_provider() -> AmfiProvider:
    """Factory function to get AMFI provider instance."""
    return AmfiProvider()


if __name__ == "__main__":
    # Test the AMFI provider
    print("Testing AMFI Provider...")
    
    provider = AmfiProvider()
    
    # Test availability
    print(f"Provider available: {provider.is_available()}")
    
    # Get latest NAVs
    latest = provider.get_latest_navs()
    print(f"\nTotal schemes: {len(latest)}")
    print(f"\nSample NAVs:\n{latest.head(10)}")
    
    # Test get_nav for a known fund (example ISIN - may not exist)
    test_isin = "INF109K01Z48"  # SBI Blue Chip Fund - Growth
    nav = provider.get_nav(test_isin)
    print(f"\nNAV for {test_isin}: {nav}")
    
    # Search for schemes
    results = provider.search_schemes("SBI")
    print(f"\nSearch results for 'SBI': {len(results)} schemes")
    print(results.head())
    
    # Get AMC list
    amcs = provider.get_all_amcs()
    print(f"\nTotal AMCs: {len(amcs)}")
    print(f"Sample AMCs: {amcs[:5]}")
