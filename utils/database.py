"""
Database module for Portfolio Analytics Tool.
Phase 1: Mutual Fund holdings
Phase 2: Extended with manual assets (FD, PPF, NPS)
"""

import sqlite3
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional, Union
from pathlib import Path


class PortfolioDatabase:
    """SQLite database for portfolio data with MF holdings and manual assets."""
    
    def __init__(self, db_path: str = "data/portfolio.db"):
        """Initialize database connection and create tables if not exist."""
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create all required tables."""
        cursor = self.conn.cursor()
        
        # Phase 1: Mutual Fund Holdings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mf_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheme_code TEXT NOT NULL,
                scheme_name TEXT,
                isin TEXT,
                units REAL,
                nav REAL,
                current_value REAL,
                folio_number TEXT,
                amc TEXT,
                category TEXT,
                sub_category TEXT,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Phase 1: Transactions
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scheme_code TEXT NOT NULL,
                scheme_name TEXT,
                transaction_type TEXT,
                date DATE,
                amount REAL,
                units REAL,
                nav REAL,
                folio_number TEXT,
                is_elss BOOLEAN DEFAULT 0,
                lock_in_end DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Phase 2: Manual Assets - Fixed Deposits
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fd_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                institution TEXT NOT NULL,
                account_number TEXT,
                principal REAL NOT NULL,
                interest_rate REAL NOT NULL,
                start_date DATE NOT NULL,
                maturity_date DATE NOT NULL,
                interest_type TEXT DEFAULT 'compound',
                compounding_frequency INTEGER DEFAULT 4,
                current_value REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Phase 2: Manual Assets - PPF
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ppf_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_number TEXT NOT NULL,
                financial_year INTEGER NOT NULL,
                deposit_date DATE NOT NULL,
                amount REAL NOT NULL,
                interest_rate REAL,
                current_balance REAL,
                maturity_date DATE,
                lock_in_end DATE,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Phase 2: Manual Assets - NPS
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nps_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pran TEXT NOT NULL,
                tier INTEGER NOT NULL CHECK(tier IN (1, 2)),
                allocation_type TEXT NOT NULL,
                allocation_percentage REAL NOT NULL,
                current_value REAL NOT NULL,
                contributions_ytd REAL DEFAULT 0,
                returns_since_inception REAL DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Phase 2: Cash Holdings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cash_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_name TEXT NOT NULL,
                account_type TEXT,
                balance REAL NOT NULL,
                currency TEXT DEFAULT 'INR',
                notes TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.conn.commit()
    
    # =========================================================================
    # Phase 1: Mutual Fund Methods
    # =========================================================================
    
    def add_mf_holding(self, holding_data: Dict) -> int:
        """Add or update a mutual fund holding."""
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO mf_holdings 
            (scheme_code, scheme_name, isin, units, nav, current_value, 
             folio_number, amc, category, sub_category)
            VALUES 
            (:scheme_code, :scheme_name, :isin, :units, :nav, :current_value,
             :folio_number, :amc, :category, :sub_category)
            ON CONFLICT DO UPDATE SET
                units = excluded.units,
                nav = excluded.nav,
                current_value = excluded.current_value,
                last_updated = CURRENT_TIMESTAMP
        """, holding_data)
        self.conn.commit()
        return cursor.lastrowid
    
    def get_mf_holdings(self) -> pd.DataFrame:
        """Get all mutual fund holdings as DataFrame."""
        return pd.read_sql_query(
            "SELECT * FROM mf_holdings ORDER BY current_value DESC", 
            self.conn
        )
    
    def get_mf_transactions(self, is_elss: Optional[bool] = None) -> pd.DataFrame:
        """Get transactions, optionally filtered by ELSS status."""
        query = "SELECT * FROM transactions"
        params = []
        if is_elss is not None:
            query += " WHERE is_elss = ?"
            params.append(1 if is_elss else 0)
        query += " ORDER BY date DESC"
        return pd.read_sql_query(query, self.conn, params=params)
    
    def get_total_mf_value(self) -> float:
        """Get total value of all mutual fund holdings."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COALESCE(SUM(current_value), 0) FROM mf_holdings")
        return cursor.fetchone()[0]
    
    # =========================================================================
    # Phase 2: Manual Asset Methods
    # =========================================================================
    
    def add_manual_asset(self, asset_type: str, data: Dict) -> int:
        """
        Add a manual asset to the database.
        
        Args:
            asset_type: 'fd', 'ppf', 'nps', or 'cash'
            data: Dictionary with asset details
        
        Returns:
            ID of inserted/updated record
        """
        asset_type = asset_type.lower()
        cursor = self.conn.cursor()
        
        if asset_type == 'fd':
            cursor.execute("""
                INSERT INTO fd_holdings 
                (institution, account_number, principal, interest_rate, start_date,
                 maturity_date, interest_type, compounding_frequency, current_value, notes)
                VALUES 
                (:institution, :account_number, :principal, :interest_rate, :start_date,
                 :maturity_date, :interest_type, :compounding_frequency, :current_value, :notes)
            """, data)
            
        elif asset_type == 'ppf':
            cursor.execute("""
                INSERT INTO ppf_holdings 
                (account_number, financial_year, deposit_date, amount, interest_rate,
                 current_balance, maturity_date, lock_in_end, notes)
                VALUES 
                (:account_number, :financial_year, :deposit_date, :amount, :interest_rate,
                 :current_balance, :maturity_date, :lock_in_end, :notes)
            """, data)
            
        elif asset_type == 'nps':
            cursor.execute("""
                INSERT INTO nps_holdings 
                (pran, tier, allocation_type, allocation_percentage, current_value,
                 contributions_ytd, returns_since_inception, notes)
                VALUES 
                (:pran, :tier, :allocation_type, :allocation_percentage, :current_value,
                 :contributions_ytd, :returns_since_inception, :notes)
            """, data)
            
        elif asset_type == 'cash':
            cursor.execute("""
                INSERT INTO cash_holdings 
                (account_name, account_type, balance, currency, notes)
                VALUES 
                (:account_name, :account_type, :balance, :currency, :notes)
            """, data)
        else:
            raise ValueError(f"Unknown asset_type: {asset_type}")
        
        self.conn.commit()
        return cursor.lastrowid
    
    def get_manual_assets(self, asset_type: Optional[str] = None) -> pd.DataFrame:
        """
        Get manual assets, optionally filtered by type.
        
        Args:
            asset_type: 'fd', 'ppf', 'nps', 'cash', or None for all
        
        Returns:
            DataFrame with asset data
        """
        if asset_type:
            asset_type = asset_type.lower()
            if asset_type == 'fd':
                return pd.read_sql_query(
                    "SELECT *, 'FD' as asset_type FROM fd_holdings", self.conn
                )
            elif asset_type == 'ppf':
                return pd.read_sql_query(
                    "SELECT *, 'PPF' as asset_type FROM ppf_holdings", self.conn
                )
            elif asset_type == 'nps':
                return pd.read_sql_query(
                    "SELECT *, 'NPS' as asset_type FROM nps_holdings", self.conn
                )
            elif asset_type == 'cash':
                return pd.read_sql_query(
                    "SELECT *, 'Cash' as asset_type FROM cash_holdings", self.conn
                )
            else:
                raise ValueError(f"Unknown asset_type: {asset_type}")
        else:
            # Get all manual assets combined
            dfs = []
            for atype in ['fd', 'ppf', 'nps', 'cash']:
                try:
                    df = self.get_manual_assets(atype)
                    if not df.empty:
                        dfs.append(df)
                except Exception:
                    pass
            if dfs:
                return pd.concat(dfs, ignore_index=True)
            return pd.DataFrame()
    
    def get_manual_assets_value(self, asset_type: Optional[str] = None) -> float:
        """Get total value of manual assets."""
        cursor = self.conn.cursor()
        
        if asset_type:
            asset_type = asset_type.lower()
            if asset_type == 'fd':
                cursor.execute("SELECT COALESCE(SUM(current_value), 0) FROM fd_holdings")
            elif asset_type == 'ppf':
                cursor.execute("SELECT COALESCE(SUM(current_balance), 0) FROM ppf_holdings")
            elif asset_type == 'nps':
                cursor.execute("SELECT COALESCE(SUM(current_value), 0) FROM nps_holdings")
            elif asset_type == 'cash':
                cursor.execute("SELECT COALESCE(SUM(balance), 0) FROM cash_holdings")
            else:
                return 0.0
        else:
            # Sum all manual assets
            cursor.execute("""
                SELECT COALESCE(
                    (SELECT SUM(current_value) FROM fd_holdings) +
                    (SELECT SUM(current_balance) FROM ppf_holdings) +
                    (SELECT SUM(current_value) FROM nps_holdings) +
                    (SELECT SUM(balance) FROM cash_holdings)
                , 0)
            """)
        
        result = cursor.fetchone()[0]
        return result if result else 0.0
    
    def get_total_portfolio_value(self) -> Dict[str, float]:
        """
        Get comprehensive portfolio value breakdown.
        
        Returns:
            Dictionary with MF, manual assets, and total values
        """
        mf_value = self.get_total_mf_value()
        fd_value = self.get_manual_assets_value('fd')
        ppf_value = self.get_manual_assets_value('ppf')
        nps_value = self.get_manual_assets_value('nps')
        cash_value = self.get_manual_assets_value('cash')
        
        manual_total = fd_value + ppf_value + nps_value + cash_value
        grand_total = mf_value + manual_total
        
        return {
            'mf_value': mf_value,
            'fd_value': fd_value,
            'ppf_value': ppf_value,
            'nps_value': nps_value,
            'cash_value': cash_value,
            'manual_total': manual_total,
            'total': grand_total,
            'last_updated': datetime.now().isoformat()
        }
    
    def delete_manual_asset(self, asset_type: str, asset_id: int) -> bool:
        """Delete a manual asset by ID."""
        asset_type = asset_type.lower()
        cursor = self.conn.cursor()
        
        table_map = {
            'fd': 'fd_holdings',
            'ppf': 'ppf_holdings',
            'nps': 'nps_holdings',
            'cash': 'cash_holdings'
        }
        
        if asset_type not in table_map:
            return False
        
        table = table_map[asset_type]
        cursor.execute(f"DELETE FROM {table} WHERE id = ?", (asset_id,))
        self.conn.commit()
        return cursor.rowcount > 0
    
    def update_fd_value(self, fd_id: int, current_value: float):
        """Update calculated FD current value."""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE fd_holdings 
            SET current_value = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id = ?
        """, (current_value, fd_id))
        self.conn.commit()
    
    def close(self):
        """Close database connection."""
        self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Singleton instance for app use
_db_instance = None

def get_db(db_path: str = "data/portfolio.db") -> PortfolioDatabase:
    """Get or create database singleton instance."""
    global _db_instance
    if _db_instance is None:
        _db_instance = PortfolioDatabase(db_path)
    return _db_instance


def reset_db():
    """Reset database singleton (for testing)."""
    global _db_instance
    _db_instance = None
