#!/usr/bin/env python3
"""
Portfolio Analytics Tool - Unified Entry Point
===============================================

Personal investment dashboard for Indian investors.
Supports: Mutual Funds (CAS), Fixed Deposits, PPF, NPS

Usage:
    streamlit run app.py          # Launch web dashboard
    python3 app.py init           # Initialize database
    python3 app.py sample         # Generate sample data
    python3 app.py validate       # Run validation tests
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def init_database():
    """Initialize SQLite database with all tables"""
    print("🔧 Initializing Portfolio Analytics database...")
    
    try:
        from database import PortfolioDatabase
        db = PortfolioDatabase()
        db.initialize_database()
        
        print("✅ Database initialized successfully!")
        print(f"📁 Location: {db.db_path}")
        print("\nTables created:")
        print("  - holdings (mutual funds + manual assets)")
        print("  - transactions (for XIRR calculation)")
        print("  - nav_history (historical prices)")
        print("  - isin_master (scheme metadata)")
        print("  - manual_assets (FD, PPF, NPS)")
        print("  - alerts (generated alerts)")
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        sys.exit(1)

def generate_sample_data():
    """Generate sample portfolio for testing"""
    print("📊 Generating sample portfolio data...")
    
    try:
        from database import PortfolioDatabase
        from utils.xirr import calculate_xirr
        import pandas as pd
        from datetime import datetime, timedelta
        import random
        
        db = PortfolioDatabase()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        # Sample mutual fund holdings
        sample_mfs = [
            {
                'isin': 'INF200K01SQ9',
                'scheme_name': 'SBI Bluechip Fund - Direct Plan - Growth',
                'category': 'Equity Large Cap',
                'amc': 'SBI Mutual Fund',
                'units': 1500.500,
                'purchase_value': 125000.00,
                'purchase_date': '2022-01-15',
                'current_nav': 85.75,
                'asset_type': 'MF'
            },
            {
                'isin': 'INF846K01EW8',
                'scheme_name': 'Axis Long Term Equity Fund - Direct Growth',
                'category': 'ELSS',
                'amc': 'Axis Mutual Fund',
                'units': 800.250,
                'purchase_value': 50000.00,
                'purchase_date': '2023-03-10',
                'current_nav': 72.45,
                'asset_type': 'MF'
            },
            {
                'isin': 'INF179K01ZY5',
                'scheme_name': 'HDFC Top 100 Fund - Direct Plan - Growth',
                'category': 'Equity Large Cap',
                'amc': 'HDFC Mutual Fund',
                'units': 2200.000,
                'purchase_value': 180000.00,
                'purchase_date': '2021-06-20',
                'current_nav': 95.20,
                'asset_type': 'MF'
            },
            {
                'isin': 'INF194K01X88',
                'scheme_name': 'Nippon India Small Cap Fund - Direct Growth',
                'category': 'Equity Small Cap',
                'amc': 'Nippon India Mutual Fund',
                'units': 2500.750,
                'purchase_value': 75000.00,
                'purchase_date': '2023-08-05',
                'current_nav': 118.50,
                'asset_type': 'MF'
            },
            {
                'isin': 'INF204K01XK3',
                'scheme_name': 'ICICI Prudential Liquid Fund - Direct Plan',
                'category': 'Liquid',
                'amc': 'ICICI Prudential Mutual Fund',
                'units': 5000.000,
                'purchase_value': 150000.00,
                'purchase_date': '2024-01-10',
                'current_nav': 100.45,
                'asset_type': 'MF'
            },
            {
                'isin': 'INF760K01EY6',
                'scheme_name': 'Kotak Corporate Bond Fund - Direct Growth',
                'category': 'Debt Corporate Bond',
                'amc': 'Kotak Mutual Fund',
                'units': 3000.000,
                'purchase_value': 60000.00,
                'purchase_date': '2023-11-15',
                'current_nav': 22.15,
                'asset_type': 'MF'
            }
        ]
        
        # Calculate current values and XIRR
        total_aum = 0
        for mf in sample_mfs:
            current_value = mf['units'] * mf['current_nav']
            mf['current_value'] = current_value
            total_aum += current_value
            
            # Simple XIRR calculation (for demo)
            cashflows = [
                (datetime.strptime(mf['purchase_date'], '%Y-%m-%d'), -mf['purchase_value']),
                (datetime.now(), current_value)
            ]
            try:
                mf['xirr'] = calculate_xirr(cashflows) * 100
            except:
                mf['xirr'] = 12.5  # Default for demo
            
            # Insert into database
            cursor.execute('''
                INSERT OR REPLACE INTO holdings 
                (isin, scheme_name, category, asset_type, units, purchase_value, 
                 purchase_date, folio, amc, current_nav, current_value, xirr, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                mf['isin'], mf['scheme_name'], mf['category'], mf['asset_type'],
                mf['units'], mf['purchase_value'], mf['purchase_date'],
                'SAMPLE001', mf['amc'], mf['current_nav'], mf['current_value'],
                mf['xirr'], datetime.now().isoformat()
            ))
            
            # Insert transactions for XIRR
            cursor.execute('''
                INSERT INTO transactions (isin, type, date, amount, units, nav)
                VALUES (?, 'PURCHASE', ?, ?, ?, ?)
            ''', (mf['isin'], mf['purchase_date'], mf['purchase_value'], 
                  mf['units'], mf['purchase_value']/mf['units']))
        
        # Sample FDs
        sample_fds = [
            {
                'institution': 'HDFC Bank',
                'account_number': 'FD123456789',
                'principal': 100000,
                'interest_rate': 7.5,
                'start_date': '2024-01-15',
                'maturity_date': '2026-01-15',
                'interest_type': 'compound',
                'compounding_frequency': 'quarterly'
            },
            {
                'institution': 'SBI',
                'account_number': 'FD987654321',
                'principal': 50000,
                'interest_rate': 7.0,
                'start_date': '2024-03-10',
                'maturity_date': '2025-03-10',
                'interest_type': 'simple',
                'compounding_frequency': None
            }
        ]
        
        for fd in sample_fds:
            # Calculate current value
            if fd['interest_type'] == 'compound':
                n = 4 if fd['compounding_frequency'] == 'quarterly' else 1
                start = datetime.strptime(fd['start_date'], '%Y-%m-%d')
                years = (datetime.now() - start).days / 365.25
                current_value = fd['principal'] * (1 + fd['interest_rate']/100/n)**(n*years)
            else:
                start = datetime.strptime(fd['start_date'], '%Y-%m-%d')
                days = (datetime.now() - start).days
                interest = fd['principal'] * fd['interest_rate'] / 100 * days / 365
                current_value = fd['principal'] + interest
            
            cursor.execute('''
                INSERT INTO manual_assets 
                (asset_type, institution, account_number, principal, interest_rate,
                 start_date, maturity_date, interest_type, compounding_frequency, 
                 current_value, last_updated)
                VALUES ('FD', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (fd['institution'], fd['account_number'], fd['principal'],
                  fd['interest_rate'], fd['start_date'], fd['maturity_date'],
                  fd['interest_type'], fd['compounding_frequency'], current_value,
                  datetime.now().isoformat()))
            
            total_aum += current_value
        
        # Sample PPF
        cursor.execute('''
            INSERT INTO manual_assets 
            (asset_type, account_number, principal, interest_rate, start_date,
             maturity_date, current_value, last_updated)
            VALUES ('PPF', 'PPF123456', 500000, 7.1, '2018-04-01', '2033-03-31',
                    750000, ?)
        ''', (datetime.now().isoformat(),))
        total_aum += 750000
        
        # Sample NPS
        nps_allocations = [
            ('Tier-1 Equity', 'equity', 250000, 50),
            ('Tier-1 Corporate Bond', 'corporate_bond', 150000, 30),
            ('Tier-1 Govt Securities', 'govt_securities', 100000, 20)
        ]
        
        for name, alloc_type, value, pct in nps_allocations:
            cursor.execute('''
                INSERT INTO manual_assets 
                (asset_type, account_number, principal, interest_rate, current_value, last_updated)
                VALUES ('NPS', ?, ?, ?, ?, ?)
            ''', (f'{name} ({pct}%)', alloc_type, value, pct, datetime.now().isoformat()))
            total_aum += value
        
        conn.commit()
        conn.close()
        
        print(f"✅ Sample data generated!")
        print(f"📊 Total Portfolio Value: ₹{total_aum:,.2f}")
        print(f"\nAssets created:")
        print(f"  - {len(sample_mfs)} Mutual Funds")
        print(f"  - {len(sample_fds)} Fixed Deposits")
        print(f"  - 1 PPF Account")
        print(f"  - 3 NPS Allocations")
        print(f"\nNow run: streamlit run app.py")
        
    except Exception as e:
        print(f"❌ Error generating sample data: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def validate_setup():
    """Run validation tests"""
    print("🧪 Running validation tests...")
    
    try:
        # Test imports
        print("\n1. Testing imports...")
        from database import PortfolioDatabase
        from api.amfi_provider import AmfiProvider
        from parsers.cas_parser import CASParser
        from utils.xirr import calculate_xirr
        from utils.risk_metrics import calculate_volatility
        from utils.glide_path import get_target_allocation
        print("   ✅ All imports successful")
        
        # Test database
        print("\n2. Testing database...")
        db = PortfolioDatabase()
        conn = db.get_connection()
        cursor = conn.cursor()
        
        tables = ['holdings', 'transactions', 'nav_history', 'isin_master', 
                  'manual_assets', 'alerts']
        for table in tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                print(f"   ✅ Table '{table}' exists")
            else:
                print(f"   ❌ Table '{table}' missing")
        conn.close()
        
        # Test XIRR
        print("\n3. Testing XIRR calculation...")
        from datetime import datetime
        cashflows = [
            (datetime(2023, 1, 1), -100000),
            (datetime(2023, 6, 1), -50000),
            (datetime(2024, 1, 1), 165000)
        ]
        xirr = calculate_xirr(cashflows)
        print(f"   ✅ XIRR calculation: {xirr*100:.2f}%")
        
        # Test glide path
        print("\n4. Testing glide path...")
        target = get_target_allocation(35)
        print(f"   ✅ Age 35 target: {target}")
        
        # Test config files
        print("\n5. Testing configuration files...")
        import yaml
        configs = ['config/categories.yaml', 'config/limits.yaml', 'config/glide_path.yaml']
        for cfg in configs:
            with open(cfg, 'r') as f:
                data = yaml.safe_load(f)
                print(f"   ✅ {cfg} loaded")
        
        print("\n✅ All validation tests passed!")
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

def launch_dashboard():
    """Launch Streamlit dashboard"""
    import subprocess
    
    print("🚀 Launching Portfolio Analytics Dashboard...")
    print("\nThe dashboard will open in your browser.")
    print("If it doesn't open automatically, visit: http://localhost:8501")
    print("\nPress Ctrl+C to stop the server.\n")
    
    try:
        subprocess.run(['streamlit', 'run', 'app/main.py'], check=True)
    except FileNotFoundError:
        print("❌ Streamlit not found. Install with: pip install streamlit")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped.")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'init':
            init_database()
        elif command == 'sample':
            generate_sample_data()
        elif command == 'validate':
            validate_setup()
        elif command == 'help':
            print(__doc__)
        else:
            print(f"Unknown command: {command}")
            print("\nAvailable commands:")
            print("  init      - Initialize database")
            print("  sample    - Generate sample data")
            print("  validate  - Run validation tests")
            print("  help      - Show this help")
            print("\nOr run without arguments to launch dashboard.")
    else:
        # Default: launch dashboard
        launch_dashboard()
