"""
Portfolio Analytics Database Module
SQLite database handler for mutual fund portfolio data.
"""

import sqlite3
import os
from datetime import datetime, date
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from contextlib import contextmanager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class Holding:
    """Represents a mutual fund holding."""
    id: Optional[int]
    isin: str
    scheme_name: str
    category: str
    units: float
    purchase_value: float
    purchase_date: str
    folio: str
    amc: str
    current_nav: Optional[float] = None
    last_updated: Optional[str] = None
    current_value: Optional[float] = None  # Computed field


@dataclass
class Transaction:
    """Represents a mutual fund transaction."""
    id: Optional[int]
    isin: str
    type: str  # 'PURCHASE', 'REDEMPTION', 'DIVIDEND', 'SIP'
    date: str
    amount: float
    units: float
    nav: float
    folio: Optional[str] = None
    scheme_name: Optional[str] = None


@dataclass
class NavHistory:
    """Represents historical NAV data point."""
    isin: str
    date: str
    nav: float


@dataclass
class IsinMaster:
    """Represents ISIN master data."""
    isin: str
    scheme_name: str
    category: str
    amc: str
    benchmark: Optional[str] = None
    asset_type: Optional[str] = None


class PortfolioDatabase:
    """
    SQLite database manager for portfolio analytics.
    Handles holdings, transactions, NAV history, and ISIN master data.
    """
    
    def __init__(self, db_path: str = None):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file. Defaults to data/portfolio.db
        """
        if db_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, 'data', 'portfolio.db')
        
        self.db_path = db_path
        self._ensure_dir()
        self._init_db()
    
    def _ensure_dir(self):
        """Ensure the database directory exists."""
        dir_path = os.path.dirname(self.db_path)
        if dir_path and not os.path.exists(dir_path):
            os.makedirs(dir_path)
    
    def get_connection(self):
        """Get a database connection. Caller must close it."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _init_db(self):
        """Initialize database tables."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Holdings table - current portfolio positions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS holdings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isin TEXT NOT NULL,
                    scheme_name TEXT NOT NULL,
                    category TEXT,
                    asset_type TEXT,
                    units REAL NOT NULL,
                    purchase_value REAL,
                    purchase_date TEXT,
                    folio TEXT,
                    amc TEXT,
                    current_nav REAL,
                    last_updated TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(isin, folio)
                )
            """)
            
            # Transactions table - all buy/sell transactions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isin TEXT NOT NULL,
                    scheme_name TEXT,
                    type TEXT NOT NULL,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    units REAL NOT NULL,
                    nav REAL,
                    folio TEXT,
                    amc TEXT,
                    category TEXT,
                    description TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # NAV History table - historical NAV data
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS nav_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isin TEXT NOT NULL,
                    date TEXT NOT NULL,
                    nav REAL NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(isin, date)
                )
            """)
            
            # ISIN Master table - scheme information
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS isin_master (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    isin TEXT UNIQUE NOT NULL,
                    scheme_name TEXT NOT NULL,
                    category TEXT,
                    asset_type TEXT,
                    amc TEXT,
                    benchmark TEXT,
                    fund_type TEXT,
                    expense_ratio REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Index for faster queries
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_holdings_isin ON holdings(isin)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_isin ON transactions(isin)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_transactions_date ON transactions(date)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_nav_history_isin ON nav_history(isin)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_nav_history_date ON nav_history(date)
            """)
            
            conn.commit()
            logger.info("Database initialized successfully at %s", self.db_path)
    
    # Holdings Operations
    def add_holding(self, holding: Holding) -> int:
        """Add or update a holding."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute("""
                INSERT INTO holdings 
                (isin, scheme_name, category, units, purchase_value, purchase_date, folio, amc, current_nav, last_updated, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(isin, folio) DO UPDATE SET
                scheme_name=excluded.scheme_name,
                category=excluded.category,
                units=excluded.units,
                purchase_value=excluded.purchase_value,
                current_nav=excluded.current_nav,
                last_updated=excluded.last_updated,
                updated_at=excluded.updated_at
            """, (
                holding.isin, holding.scheme_name, holding.category, 
                holding.units, holding.purchase_value, holding.purchase_date,
                holding.folio, holding.amc, holding.current_nav, 
                holding.last_updated, now
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_holding(self, isin: str, folio: str) -> Optional[Holding]:
        """Get a specific holding by ISIN and folio."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM holdings WHERE isin = ? AND folio = ?
            """, (isin, folio))
            row = cursor.fetchone()
            if row:
                return Holding(**dict(row))
            return None
    
    def get_all_holdings(self) -> List[Holding]:
        """Get all current holdings."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM holdings ORDER BY scheme_name")
            return [Holding(**dict(row)) for row in cursor.fetchall()]
    
    def update_nav(self, isin: str, folio: str, nav: float):
        """Update current NAV for a holding."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                UPDATE holdings SET current_nav = ?, last_updated = ?
                WHERE isin = ? AND folio = ?
            """, (nav, now, isin, folio))
            conn.commit()
    
    def delete_holding(self, holding_id: int):
        """Delete a holding by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM holdings WHERE id = ?", (holding_id,))
            conn.commit()
    
    # Transaction Operations
    def add_transaction(self, transaction: Transaction) -> int:
        """Add a transaction."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO transactions 
                (isin, scheme_name, type, date, amount, units, nav, folio, amc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                transaction.isin, transaction.scheme_name, transaction.type,
                transaction.date, transaction.amount, transaction.units,
                transaction.nav, transaction.folio, transaction.amc
            ))
            conn.commit()
            return cursor.lastrowid
    
    def add_transactions_bulk(self, transactions: List[Transaction]) -> int:
        """Add multiple transactions in bulk."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            data = [(
                t.isin, t.scheme_name, t.type, t.date, t.amount, 
                t.units, t.nav, t.folio, t.amc
            ) for t in transactions]
            cursor.executemany("""
                INSERT INTO transactions 
                (isin, scheme_name, type, date, amount, units, nav, folio, amc)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, data)
            conn.commit()
            return cursor.rowcount
    
    def get_transactions(self, isin: Optional[str] = None) -> List[Transaction]:
        """Get transactions, optionally filtered by ISIN."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if isin:
                cursor.execute("""
                    SELECT * FROM transactions WHERE isin = ? ORDER BY date
                """, (isin,))
            else:
                cursor.execute("SELECT * FROM transactions ORDER BY date DESC")
            return [Transaction(**dict(row)) for row in cursor.fetchall()]
    
    def get_cashflows_for_xirr(self, isin: str) -> List[Tuple[datetime, float]]:
        """Get cashflows for XIRR calculation."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, amount, units, type FROM transactions WHERE isin = ? ORDER BY date
            """, (isin,))
            
            cashflows = []
            for row in cursor.fetchall():
                date_str = row['date']
                amount = row['amount']
                units = row['units']
                tx_type = row['type'].upper()
                
                # Parse date
                try:
                    dt = datetime.strptime(date_str, '%Y-%m-%d')
                except ValueError:
                    try:
                        dt = datetime.strptime(date_str, '%d-%m-%Y')
                    except ValueError:
                        continue
                
                # Determine cashflow direction (negative for investment, positive for redemption)
                if tx_type in ['PURCHASE', 'SIP']:
                    cashflows.append((dt, -abs(amount)))
                elif tx_type == 'REDEMPTION':
                    cashflows.append((dt, abs(amount)))
                elif tx_type == 'DIVIDEND':
                    cashflows.append((dt, abs(amount)))
            
            return cashflows
    
    # NAV History Operations
    def add_nav(self, nav_data: NavHistory) -> int:
        """Add NAV history entry."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    INSERT INTO nav_history (isin, date, nav)
                    VALUES (?, ?, ?)
                    ON CONFLICT(isin, date) DO UPDATE SET nav=excluded.nav
                """, (nav_data.isin, nav_data.date, nav_data.nav))
                conn.commit()
                return cursor.lastrowid
            except sqlite3.Error as e:
                logger.error("Error adding NAV: %s", e)
                raise
    
    def add_nav_bulk(self, nav_data_list: List[NavHistory]) -> int:
        """Add multiple NAV entries in bulk."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            data = [(n.isin, n.date, n.nav) for n in nav_data_list]
            cursor.executemany("""
                INSERT INTO nav_history (isin, date, nav)
                VALUES (?, ?, ?)
                ON CONFLICT(isin, date) DO UPDATE SET nav=excluded.nav
            """, data)
            conn.commit()
            return cursor.rowcount
    
    def get_nav(self, isin: str, date_str: str) -> Optional[float]:
        """Get NAV for a specific ISIN and date."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT nav FROM nav_history WHERE isin = ? AND date = ?
            """, (isin, date_str))
            row = cursor.fetchone()
            return row['nav'] if row else None
    
    def get_latest_nav(self, isin: str) -> Optional[Tuple[str, float]]:
        """Get the most recent NAV for an ISIN."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT date, nav FROM nav_history 
                WHERE isin = ? ORDER BY date DESC LIMIT 1
            """, (isin,))
            row = cursor.fetchone()
            return (row['date'], row['nav']) if row else None
    
    def get_nav_history(self, isin: str, from_date: str, to_date: str) -> List[NavHistory]:
        """Get NAV history for a date range."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM nav_history 
                WHERE isin = ? AND date >= ? AND date <= ?
                ORDER BY date
            """, (isin, from_date, to_date))
            return [NavHistory(**dict(row)) for row in cursor.fetchall()]
    
    # ISIN Master Operations
    def add_isin_master(self, isin_data: IsinMaster) -> int:
        """Add or update ISIN master record."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO isin_master 
                (isin, scheme_name, category, asset_type, amc, benchmark, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(isin) DO UPDATE SET
                scheme_name=excluded.scheme_name,
                category=excluded.category,
                asset_type=excluded.asset_type,
                amc=excluded.amc,
                benchmark=excluded.benchmark,
                updated_at=excluded.updated_at
            """, (
                isin_data.isin, isin_data.scheme_name, isin_data.category,
                isin_data.asset_type, isin_data.amc, isin_data.benchmark, now
            ))
            conn.commit()
            return cursor.lastrowid
    
    def add_isin_master_bulk(self, isin_list: List[IsinMaster]) -> int:
        """Add multiple ISIN master records in bulk."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            data = [(
                i.isin, i.scheme_name, i.category, i.asset_type,
                i.amc, i.benchmark, now
            ) for i in isin_list]
            cursor.executemany("""
                INSERT INTO isin_master 
                (isin, scheme_name, category, asset_type, amc, benchmark, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(isin) DO UPDATE SET
                scheme_name=excluded.scheme_name,
                category=excluded.category,
                asset_type=excluded.asset_type,
                amc=excluded.amc,
                benchmark=excluded.benchmark,
                updated_at=excluded.updated_at
            """, data)
            conn.commit()
            return cursor.rowcount
    
    def get_isin_master(self, isin: str) -> Optional[IsinMaster]:
        """Get ISIN master data for a specific ISIN."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM isin_master WHERE isin = ?", (isin,))
            row = cursor.fetchone()
            if row:
                return IsinMaster(
                    isin=row['isin'],
                    scheme_name=row['scheme_name'],
                    category=row['category'],
                    amc=row['amc'],
                    benchmark=row['benchmark'],
                    asset_type=row['asset_type']
                )
            return None
    
    def get_all_isin_master(self) -> List[IsinMaster]:
        """Get all ISIN master records."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM isin_master ORDER BY scheme_name")
            return [IsinMaster(
                isin=row['isin'],
                scheme_name=row['scheme_name'],
                category=row['category'],
                amc=row['amc'],
                benchmark=row['benchmark'],
                asset_type=row['asset_type']
            ) for row in cursor.fetchall()]
    
    def search_isin_master(self, keyword: str) -> List[IsinMaster]:
        """Search ISIN master by keyword."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            search = f"%{keyword}%"
            cursor.execute("""
                SELECT * FROM isin_master 
                WHERE scheme_name LIKE ? OR amc LIKE ? OR isin LIKE ?
                ORDER BY scheme_name
            """, (search, search, search))
            return [IsinMaster(
                isin=row['isin'],
                scheme_name=row['scheme_name'],
                category=row['category'],
                amc=row['amc'],
                benchmark=row['benchmark'],
                asset_type=row['asset_type']
            ) for row in cursor.fetchall()]
    
    # Analytics Operations
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """Get portfolio summary statistics."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Total AUM
            cursor.execute("SELECT SUM(units * current_nav) as aum FROM holdings WHERE current_nav IS NOT NULL")
            total_aum = cursor.fetchone()['aum'] or 0
            
            # Total purchase value
            cursor.execute("SELECT SUM(purchase_value) as cost FROM holdings")
            total_cost = cursor.fetchone()['cost'] or 0
            
            # Unrealized gains
            cursor.execute("""
                SELECT SUM(units * current_nav - purchase_value) as gains 
                FROM holdings WHERE current_nav IS NOT NULL
            """)
            unrealized_gains = cursor.fetchone()['gains'] or 0
            
            # Category-wise allocation
            cursor.execute("""
                SELECT category, SUM(units * current_nav) as value, COUNT(*) as count
                FROM holdings WHERE current_nav IS NOT NULL
                GROUP BY category
            """)
            category_breakdown = [dict(row) for row in cursor.fetchall()]
            
            return {
                'total_aum': total_aum,
                'total_cost': total_cost,
                'unrealized_gains': unrealized_gains,
                'return_pct': (unrealized_gains / total_cost * 100) if total_cost > 0 else 0,
                'category_breakdown': category_breakdown,
                'num_holdings': len(self.get_all_holdings())
            }
    
    def clear_all_data(self):
        """Clear all portfolio data (holdings and transactions)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM holdings")
            cursor.execute("DELETE FROM transactions")
            conn.commit()
            logger.info("All portfolio data cleared")


def get_default_db() -> PortfolioDatabase:
    """Get default database instance."""
    return PortfolioDatabase()


if __name__ == "__main__":
    # Test the database
    db = get_default_db()
    print(f"Database initialized at: {db.db_path}")
    
    # Add a test holding
    test_holding = Holding(
        id=None,
        isin="INF209K01UT8",
        scheme_name="Test Fund",
        category="Equity Large Cap",
        units=100.5,
        purchase_value=10000.0,
        purchase_date="2024-01-01",
        folio="12345678",
        amc="Test AMC",
        current_nav=120.0,
        last_updated=datetime.now().isoformat()
    )
    db.add_holding(test_holding)
    print("Test holding added successfully")
    
    # Retrieve holdings
    holdings = db.get_all_holdings()
    print(f"Number of holdings: {len(holdings)}")
    
    # Get summary
    summary = db.get_portfolio_summary()
    print(f"Portfolio Summary: {summary}")
