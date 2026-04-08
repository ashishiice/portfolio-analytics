"""
Test script for Phase 3 - Risk Intelligence & Glide Path
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def test_glide_path():
    """Test glide path functions."""
    from utils.glide_path import get_target_allocation, calculate_drift, get_glide_path_projection
    
    # Test age 35
    target = get_target_allocation(35)
    assert target['equity'] == 60, f"Expected equity 60, got {target['equity']}"
    assert target['debt'] == 35, f"Expected debt 35, got {target['debt']}"
    
    # Test drift calculation
    current = {'equity': 68, 'debt': 25, 'gold': 4, 'cash': 3}
    drift = calculate_drift(current, target)
    assert drift['equity'] == 8, f"Expected equity drift 8, got {drift['equity']}"
    
    # Test projection
    projection = get_glide_path_projection(35, 60)
    assert len(projection) == 26, f"Expected 26 years, got {len(projection)}"
    assert projection.iloc[0]['equity'] == 60
    
    print("✅ Glide path tests passed")


def test_risk_metrics():
    """Test risk metrics calculations."""
    from utils.risk_metrics import portfolio_volatility, sharpe_ratio, max_drawdown
    
    # Create sample NAV history
    dates = pd.date_range(end=datetime.now(), periods=252, freq='D')
    np.random.seed(42)
    returns = np.random.normal(0.0003, 0.01, 252)
    nav = 100 * np.exp(np.cumsum(returns))
    
    nav_df = pd.DataFrame({'date': dates, 'nav': nav})
    
    # Test volatility
    vol = portfolio_volatility(nav_df)
    assert vol > 0, "Volatility should be positive"
    
    # Test Sharpe ratio
    returns_series = pd.Series(returns, index=dates)
    sharpe = sharpe_ratio(returns_series)
    assert isinstance(sharpe, (int, float, np.floating)), "Sharpe ratio should be numeric"
    
    # Test max drawdown
    dd = max_drawdown(nav_df)
    assert 'max_drawdown_pct' in dd
    assert dd['max_drawdown_pct'] <= 0, "Max drawdown should be <= 0"
    
    print("✅ Risk metrics tests passed")


def test_tax_tracker():
    """Test tax tracking functions."""
    from utils.tax_tracker import classify_gains, calculate_tax_liability_if_sold
    
    # Create sample holdings
    holdings = pd.DataFrame([
        {'scheme': 'Test Equity', 'scheme_type': 'Equity', 'purchase_date': '2023-01-01', 
         'current_value': 150000, 'cost_basis': 100000},
        {'scheme': 'Test ELSS', 'scheme_type': 'ELSS', 'purchase_date': '2024-02-01', 
         'current_value': 100000, 'cost_basis': 100000},
        {'scheme': 'Test Debt', 'scheme_type': 'Debt', 'purchase_date': '2020-01-01', 
         'current_value': 110000, 'cost_basis': 100000},
    ])
    
    # Test gain classification
    classified = classify_gains(holdings)
    assert 'gain_type' in classified.columns
    assert 'unrealized_gain' in classified.columns
    
    # Test tax calculation
    tax = calculate_tax_liability_if_sold(classified)
    assert 'total_tax' in tax
    assert 'equity_ltcg_tax' in tax
    
    print("✅ Tax tracker tests passed")


def test_rebalancer():
    """Test rebalancer functions."""
    from utils.rebalancer import calculate_rebalancing_trades, calculate_drift_matrix
    
    # Create sample holdings
    holdings = pd.DataFrame([
        {'scheme': 'Large Cap', 'scheme_type': 'Equity', 'scheme_category': 'Large Cap', 'current_value': 600000},
        {'scheme': 'Mid Cap', 'scheme_type': 'Equity', 'scheme_category': 'Mid Cap', 'current_value': 400000},
        {'scheme': 'Corporate Bond', 'scheme_type': 'Debt', 'scheme_category': 'Corporate Bond', 'current_value': 350000},
    ])
    
    target = {'equity': 60, 'debt': 35, 'gold': 3, 'cash': 2}
    
    # Test rebalancing trades
    trades = calculate_rebalancing_trades(holdings, target, total_aum=1350000)
    assert isinstance(trades, pd.DataFrame)
    if not trades.empty:
        assert 'action' in trades.columns
        assert 'amount' in trades.columns
    
    # Test drift matrix
    current = {'equity': 74, 'debt': 26, 'gold': 0, 'cash': 0}
    drift_df = calculate_drift_matrix(current, target)
    assert isinstance(drift_df, pd.DataFrame)
    assert 'asset_class' in drift_df.columns
    
    print("✅ Rebalancer tests passed")


def test_config():
    """Test configuration loading."""
    from utils.glide_path import load_glide_path_config
    
    config = load_glide_path_config()
    assert 'age_targets' in config
    assert 'age_35' in config['age_targets']
    assert config['age_targets']['age_35']['equity'] == 60
    
    print("✅ Config tests passed")


if __name__ == "__main__":
    print("\n🧪 Running Phase 3 Tests\n")
    
    try:
        test_config()
        test_glide_path()
        test_risk_metrics()
        test_tax_tracker()
        test_rebalancer()
        
        print("\n✅ All Phase 3 tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
