"""
Tests for Alert Engine.
"""

import pytest
import pandas as pd
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.components.alerts import AlertEngine, Severity, Alert


class TestConcentrationAlerts:
    """Tests for concentration alert rules."""
    
    def test_single_holding_above_threshold(self):
        """Test alert when single holding exceeds threshold."""
        engine = AlertEngine()
        
        holdings = pd.DataFrame({
            'scheme_name': ['Fund A', 'Fund B', 'Fund C'],
            'current_value': [600000, 200000, 200000]  # Fund A is 60%
        })
        
        alerts = engine.check_concentration(holdings, threshold=0.15)
        
        # Should have at least one critical alert for Fund A
        critical_alerts = [a for a in alerts if a.severity == Severity.CRITICAL]
        assert len(critical_alerts) >= 1
        assert any('Fund A' in a.title for a in critical_alerts)
    
    def test_concentration_within_limits(self):
        """Test no alerts when all holdings within limits."""
        engine = AlertEngine()
        
        holdings = pd.DataFrame({
            'scheme_name': ['Fund A', 'Fund B', 'Fund C', 'Fund D', 'Fund E'],
            'current_value': [200000, 200000, 200000, 200000, 200000]  # Each 20%
        })
        
        alerts = engine.check_concentration(holdings, threshold=0.25)
        
        critical_alerts = [a for a in alerts if a.severity == Severity.CRITICAL]
        assert len(critical_alerts) == 0
    
    def test_top3_concentration_alert(self):
        """Test top3 concentration check."""
        engine = AlertEngine()
        
        holdings = pd.DataFrame({
            'scheme_name': ['Fund A', 'Fund B', 'Fund C', 'Fund D'],
            'current_value': [400000, 300000, 200000, 100000]  # Top 3 = 90%
        })
        
        alerts = engine.check_top3_concentration(holdings, threshold=0.50)
        
        # Should have critical alert
        critical_alerts = [a for a in alerts if a.severity == Severity.CRITICAL]
        assert len(critical_alerts) >= 1


class TestCashDragAlerts:
    """Tests for cash drag alerts."""
    
    def test_high_cash_percentage(self):
        """Test alert when cash is too high."""
        engine = AlertEngine()
        
        cash = 200000
        total = 1000000  # 20% cash
        
        alerts = engine.check_cash_drag(cash, total, threshold=0.10)
        
        critical_alerts = [a for a in alerts if a.severity == Severity.CRITICAL]
        assert len(critical_alerts) >= 1
        assert any('20' in a.message or '0.2' in a.message for a in alerts)
    
    def test_low_cash_buffer(self):
        """Test alert when cash is too low."""
        engine = AlertEngine()
        
        cash = 10000
        total = 1000000  # 1% cash
        
        alerts = engine.check_cash_drag(cash, total, threshold=0.10)
        
        # Should have warning about low cash
        warning_alerts = [a for a in alerts if a.severity == Severity.WARNING]
        assert len(warning_alerts) >= 1
    
    def test_optimal_cash_level(self):
        """Test OK status when cash is within range."""
        engine = AlertEngine()
        
        cash = 50000
        total = 1000000  # 5% cash
        
        alerts = engine.check_cash_drag(cash, total, threshold=0.10)
        
        ok_alerts = [a for a in alerts if a.severity == Severity.OK]
        assert len(ok_alerts) >= 1


class TestELSSAlerts:
    """Tests for ELSS lock-in alerts."""
    
    def test_elss_unlocking_soon(self):
        """Test alert for ELSS unlocking within warning window."""
        from datetime import datetime, timedelta
        
        engine = AlertEngine()
        
        today = datetime.now()
        
        transactions = pd.DataFrame({
            'scheme_name': ['Axis ELSS Tax Saver', 'Regular Fund'],
            'amount': [50000, 30000],
            'is_elss': [True, False],
            'lock_in_end': [
                (today + timedelta(days=60)).strftime('%Y-%m-%d'),  # Unlocking in 60 days
                None
            ]
        })
        
        alerts = engine.check_elss_lockin(transactions, months_before=3)
        
        # Should have info alert for ELSS
        info_alerts = [a for a in alerts if a.severity == Severity.INFO]
        assert len(info_alerts) >= 1


class TestAlertStructure:
    """Tests for alert data structure."""
    
    def test_alert_to_dict(self):
        """Test alert serialization."""
        alert = Alert(
            title="Test Alert",
            message="Test message",
            severity=Severity.WARNING,
            category="test",
            metric_value=0.20,
            threshold=0.15,
            actionable="Do something"
        )
        
        d = alert.to_dict()
        
        assert d['title'] == "Test Alert"
        assert d['severity'] == "yellow"
        assert d['metric_value'] == 0.20
        assert 'timestamp' in d


class TestFullReport:
    """Tests for full alerts report generation."""
    
    def test_generate_full_report(self):
        """Test complete alerts report."""
        engine = AlertEngine()
        
        holdings = pd.DataFrame({
            'scheme_name': ['Fund A', 'Fund B'],
            'current_value': [700000, 300000]  # 70% concentration
        })
        
        report = engine.generate_alerts_report(
            holdings_df=holdings,
            cash_value=150000,
            total_portfolio_value=1000000
        )
        
        assert 'summary' in report
        assert 'critical' in report
        assert 'warnings' in report
        assert report['summary']['total'] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
