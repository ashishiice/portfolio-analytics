"""
Tests for Liquidity Calendar.
"""

import pytest
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.components.calendar import LiquidityCalendar, EventType, CalendarEvent


class TestFDCalendar:
    """Tests for FD maturity calendar events."""
    
    def test_fd_maturity_detection(self):
        """Test detection of upcoming FD maturities."""
        calendar = LiquidityCalendar()
        
        today = datetime.now()
        
        fds = pd.DataFrame({
            'institution': ['HDFC Bank', 'SBI'],
            'account_number': ['FD123', 'SBIFD456'],
            'principal': [100000, 200000],
            'maturity_date': [
                (today + timedelta(days=30)).strftime('%Y-%m-%d'),  # Maturing soon
                (today + timedelta(days=200)).strftime('%Y-%m-%d')  # Not soon
            ],
            'current_value': [108000, 210000]
        })
        
        events = calendar.add_fd_maturities(fds, days_ahead=90)
        
        # Should find 1 event (HDFC, maturing in 30 days)
        assert len(events) == 1
        assert events[0].event_type == EventType.FD_MATURITY
        assert 'HDFC' in events[0].title
    
    def test_fd_maturity_priority(self):
        """Test priority levels for FD maturities."""
        calendar = LiquidityCalendar()
        
        today = datetime.now()
        
        fds = pd.DataFrame({
            'institution': ['Bank A', 'Bank B'],
            'account_number': ['FD1', 'FD2'],
            'principal': [100000, 100000],
            'maturity_date': [
                (today + timedelta(days=5)).strftime('%Y-%m-%d'),  # Urgent
                (today + timedelta(days=60)).strftime('%Y-%m-%d')    # Normal
            ],
            'current_value': [108000, 108000]
        })
        
        events = calendar.add_fd_maturities(fds, days_ahead=90)
        
        assert len(events) == 2
        
        # Check priorities
        urgent = [e for e in events if e.days_until <= 7]
        assert len(urgent) == 1
        assert urgent[0].data.get('priority') == 'High'


class TestELSSCalendar:
    """Tests for ELSS lock-in calendar events."""
    
    def test_elss_unlock_detection(self):
        """Test detection of ELSS funds unlocking."""
        calendar = LiquidityCalendar()
        
        today = datetime.now()
        
        transactions = pd.DataFrame({
            'scheme_name': ['Axis ELSS Tax Saver', 'HDFC ELSS'],
            'amount': [50000, 75000],
            'is_elss': [True, True],
            'lock_in_end': [
                (today + timedelta(days=45)).strftime('%Y-%m-%d'),   # Unlocking in 45 days
                (today + timedelta(days=400)).strftime('%Y-%m-%d')   # Too far
            ]
        })
        
        events = calendar.add_elss_lockins(transactions, months_ahead=3)
        
        # Should find 1 event (Axis ELSS, unlocking in 45 days < 3 months)
        assert len(events) == 1
        assert events[0].event_type == EventType.ELSS_UNLOCK


class TestPPFCalendar:
    """Tests for PPF withdrawal calendar."""
    
    def test_ppf_eligibility_detection(self):
        """Test detection of PPF withdrawal eligibility."""
        calendar = LiquidityCalendar()
        
        today = datetime.now()
        
        ppf = pd.DataFrame({
            'account_number': ['PPF123', 'PPF456'],
            'calculated_balance': [500000, 300000],
            'lock_in_end_calculated': [
                (today - timedelta(days=100)).strftime('%Y-%m-%d'),   # Eligible
                (today + timedelta(days=1000)).strftime('%Y-%m-%d')  # Not eligible
            ]
        })
        
        events = calendar.add_ppf_withdrawals(ppf)
        
        # Should find 1 eligible account
        assert len(events) >= 1
        eligible = [e for e in events if e.data.get('is_eligible')]
        assert len(eligible) == 1


class TestCalendarFiltering:
    """Tests for calendar filtering functionality."""
    
    def test_filter_by_asset_type(self):
        """Test filtering calendar by asset type."""
        calendar = LiquidityCalendar()
        
        # Add mixed events
        today = datetime.now()
        
        fds = pd.DataFrame({
            'institution': ['Bank A'],
            'account_number': ['FD1'],
            'principal': [100000],
            'maturity_date': [(today + timedelta(days=30)).strftime('%Y-%m-%d')],
            'current_value': [108000]
        })
        
        transactions = pd.DataFrame({
            'scheme_name': ['ELSS Fund'],
            'amount': [50000],
            'is_elss': [True],
            'lock_in_end': [(today + timedelta(days=60)).strftime('%Y-%m-%d')]
        })
        
        calendar.add_fd_maturities(fds)
        calendar.add_elss_lockins(transactions)
        
        # Filter to FD only
        fd_only = calendar.get_calendar_df(filter_types=['FD'])
        assert len(fd_only) == 1
        assert fd_only.iloc[0]['asset_type'] == 'FD'
        
        # Filter to ELSS only
        elss_only = calendar.get_calendar_df(filter_types=['ELSS'])
        assert len(elss_only) == 1
        assert elss_only.iloc[0]['asset_type'] == 'ELSS'
    
    def test_filter_by_days_ahead(self):
        """Test filtering by days ahead."""
        calendar = LiquidityCalendar()
        
        today = datetime.now()
        
        fds = pd.DataFrame({
            'institution': ['Bank A', 'Bank B'],
            'account_number': ['FD1', 'FD2'],
            'principal': [100000, 200000],
            'maturity_date': [
                (today + timedelta(days=30)).strftime('%Y-%m-%d'),   # Within 60 days
                (today + timedelta(days=90)).strftime('%Y-%m-%d')  # Outside 60 days
            ],
            'current_value': [108000, 216000]
        })
        
        calendar.add_fd_maturities(fds, days_ahead=120)
        
        # Filter to 60 days
        filtered = calendar.get_calendar_df(days_ahead=60)
        assert len(filtered) == 1
        assert filtered.iloc[0]['days_until'] == 30


class TestCalendarEventStructure:
    """Tests for calendar event data structure."""
    
    def test_event_to_dict(self):
        """Test event serialization."""
        today = datetime.now()
        
        event = CalendarEvent(
            date=today,
            event_type=EventType.FD_MATURITY,
            title="Test FD",
            description="Test description",
            value=100000,
            asset_type="FD",
            days_until=30,
            actionable="Do something",
            data={'test': 'data'}
        )
        
        d = event.to_dict()
        
        assert d['title'] == "Test FD"
        assert d['event_type'] == "FD Maturity"
        assert d['value'] == 100000
        assert d['days_until'] == 30


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
