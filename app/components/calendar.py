"""
Liquidity Calendar Component for Portfolio Analytics.
Shows upcoming events: FD maturities, ELSS lock-ins, SIP dates, PPF withdrawals.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class EventType(Enum):
    """Types of calendar events."""
    FD_MATURITY = "FD Maturity"
    ELSS_UNLOCK = "ELSS Unlock"
    SIP_DUE = "SIP Due"
    PPF_WITHDRAWAL = "PPF Withdrawal Eligible"
    NPS_WITHDRAWAL = "NPS Tier-2 Available"
    CASH_FLOW = "Cash Flow"


@dataclass
class CalendarEvent:
    """Calendar event data structure."""
    date: datetime
    event_type: EventType
    title: str
    description: str
    value: float
    asset_type: str
    days_until: int
    actionable: str
    data: Dict
    
    def to_dict(self) -> Dict:
        return {
            'date': self.date.strftime('%Y-%m-%d'),
            'event_type': self.event_type.value,
            'title': self.title,
            'description': self.description,
            'value': self.value,
            'asset_type': self.asset_type,
            'days_until': self.days_until,
            'actionable': self.actionable,
            'data': self.data
        }


class LiquidityCalendar:
    """Liquidity and events calendar for portfolio management."""
    
    def __init__(self):
        self.events: List[CalendarEvent] = []
        self.today = datetime.now()
    
    def add_fd_maturities(
        self, 
        fds_df: pd.DataFrame, 
        days_ahead: int = 90
    ) -> List[CalendarEvent]:
        """
        Add FD maturity events to calendar.
        
        Args:
            fds_df: DataFrame with FD data (institution, maturity_date, current_value)
            days_ahead: Look ahead window in days
        
        Returns:
            List of FD maturity events
        """
        if fds_df.empty or 'maturity_date' not in fds_df.columns:
            return []
        
        events = []
        cutoff = self.today + timedelta(days=days_ahead)
        
        fds_df = fds_df.copy()
        fds_df['maturity_date'] = pd.to_datetime(fds_df['maturity_date'])
        
        for idx, row in fds_df.iterrows():
            maturity_date = row['maturity_date']
            
            # Skip if already matured or beyond cutoff
            if maturity_date < self.today or maturity_date > cutoff:
                continue
            
            institution = str(row.get('institution', 'Unknown Bank'))
            account = str(row.get('account_number', ''))
            value = float(row.get('current_value', row.get('principal', 0)))
            days_until = (maturity_date - self.today).days
            
            # Determine priority based on proximity
            if days_until <= 7:
                priority = "High"
                actionable = f"URGENT: {institution} FD matures in {days_until} days. Plan reinvestment immediately."
            elif days_until <= 30:
                priority = "Medium"
                actionable = f"Plan reinvestment for {institution} FD maturing in {days_until} days"
            else:
                priority = "Low"
                actionable = f"Monitor {institution} FD maturity in {days_until} days for reinvestment opportunity"
            
            event = CalendarEvent(
                date=maturity_date,
                event_type=EventType.FD_MATURITY,
                title=f"FD Maturity: {institution}",
                description=f"FD {account} worth ₹{value:,.0f} matures",
                value=value,
                asset_type="FD",
                days_until=days_until,
                actionable=actionable,
                data={
                    'institution': institution,
                    'account_number': account,
                    'principal': float(row.get('principal', 0)),
                    'interest_rate': float(row.get('interest_rate', 0)),
                    'priority': priority
                }
            )
            events.append(event)
        
        self.events.extend(events)
        return events
    
    def add_elss_lockins(
        self, 
        transactions_df: pd.DataFrame,
        months_ahead: int = 12
    ) -> List[CalendarEvent]:
        """
        Add ELSS lock-in ending events.
        
        Args:
            transactions_df: DataFrame with transaction data
            months_ahead: Look ahead window in months
        
        Returns:
            List of ELSS unlock events
        """
        if transactions_df.empty:
            return []
        
        events = []
        cutoff = self.today + timedelta(days=30 * months_ahead)
        
        # Identify ELSS transactions
        elss_df = transactions_df.copy()
        
        if 'is_elss' in elss_df.columns:
            elss_df = elss_df[elss_df['is_elss'] == True]
        elif 'scheme_name' in elss_df.columns:
            # Infer from name
            elss_keywords = ['elss', 'tax', 'savings', '80c', 'taxsaver']
            mask = elss_df['scheme_name'].str.lower().str.contains('|'.join(elss_keywords), na=False)
            elss_df = elss_df[mask]
        else:
            return []
        
        if elss_df.empty:
            return []
        
        # Get lock-in dates
        if 'lock_in_end' in elss_df.columns:
            elss_df['lock_in_end'] = pd.to_datetime(elss_df['lock_in_end'], errors='coerce')
        else:
            # Estimate 3 years from purchase
            date_col = 'date' if 'date' in elss_df.columns else 'purchase_date'
            if date_col in elss_df.columns:
                elss_df[date_col] = pd.to_datetime(elss_df[date_col])
                elss_df['lock_in_end'] = elss_df[date_col] + timedelta(days=3*365)
            else:
                return []
        
        # Filter to upcoming unlocks
        upcoming = elss_df[
            (elss_df['lock_in_end'] >= self.today) & 
            (elss_df['lock_in_end'] <= cutoff)
        ].copy()
        
        for idx, row in upcoming.iterrows():
            unlock_date = row['lock_in_end']
            scheme = str(row.get('scheme_name', 'Unknown ELSS'))
            amount = float(row.get('amount', row.get('current_value', 0)))
            folio = str(row.get('folio_number', ''))
            days_until = (unlock_date - self.today).days
            
            event = CalendarEvent(
                date=unlock_date,
                event_type=EventType.ELSS_UNLOCK,
                title=f"ELSS Unlock: {scheme}",
                description=f"3-year lock-in ends for {scheme}",
                value=amount,
                asset_type="ELSS",
                days_until=days_until,
                actionable=f"₹{amount:,.0f} becomes available for redemption/rebalancing after {unlock_date.strftime('%b %Y')}",
                data={
                    'scheme': scheme,
                    'folio_number': folio,
                    'purchase_amount': amount,
                    'unlock_month': unlock_date.strftime('%B %Y')
                }
            )
            events.append(event)
        
        self.events.extend(events)
        return events
    
    def add_sip_dates(
        self, 
        transactions_df: pd.DataFrame,
        months_ahead: int = 3
    ) -> List[CalendarEvent]:
        """
        Detect SIP patterns and add upcoming SIP due dates.
        
        Args:
            transactions_df: DataFrame with transaction history
            months_ahead: Look ahead window in months
        
        Returns:
            List of SIP due events
        """
        if transactions_df.empty or 'date' not in transactions_df.columns:
            return []
        
        events = []
        cutoff = self.today + timedelta(days=30 * months_ahead)
        
        df = transactions_df.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        # Group by scheme to detect patterns
        for scheme, group in df.groupby('scheme_name'):
            if len(group) < 3:
                continue  # Need at least 3 transactions for pattern
            
            # Sort by date
            group = group.sort_values('date')
            
            # Calculate day differences
            dates = group['date'].tolist()
            diffs = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
            
            # Check if monthly pattern (25-35 days between transactions)
            is_monthly = all(25 <= d <= 35 for d in diffs[-3:]) if len(diffs) >= 3 else False
            
            if is_monthly:
                # Predict next SIP date
                last_date = dates[-1]
                sip_day = last_date.day
                
                # Generate upcoming dates
                current = last_date + timedelta(days=30)
                while current <= cutoff:
                    # Adjust for month end
                    month_days = (current.replace(day=28) + timedelta(days=4)).day - 28
                    adjusted_day = min(sip_day, month_days)
                    sip_date = current.replace(day=adjusted_day)
                    
                    if sip_date >= self.today:
                        avg_amount = group['amount'].mean()
                        days_until = (sip_date - self.today).days
                        
                        event = CalendarEvent(
                            date=sip_date,
                            event_type=EventType.SIP_DUE,
                            title=f"SIP Due: {scheme}",
                            description=f"Monthly SIP of ₹{avg_amount:,.0f}",
                            value=avg_amount,
                            asset_type="SIP",
                            days_until=days_until,
                            actionable=f"Ensure ₹{avg_amount:,.0f} available in linked account",
                            data={
                                'scheme': scheme,
                                'sip_amount': avg_amount,
                                'sip_day': sip_day,
                                'is_predicted': True
                            }
                        )
                        events.append(event)
                    
                    current = current + timedelta(days=30)
        
        self.events.extend(events)
        return events
    
    def add_ppf_withdrawals(
        self, 
        ppf_df: pd.DataFrame
    ) -> List[CalendarEvent]:
        """
        Add PPF partial withdrawal eligibility dates.
        
        PPF allows partial withdrawal after 7 years from account opening.
        
        Args:
            ppf_df: DataFrame with PPF data
        
        Returns:
            List of PPF withdrawal events
        """
        if ppf_df.empty:
            return []
        
        events = []
        
        # Get lock-in dates
        if 'lock_in_end_calculated' in ppf_df.columns:
            ppf_df['lock_in_end'] = pd.to_datetime(ppf_df['lock_in_end_calculated'])
        elif 'lock_in_end' in ppf_df.columns:
            ppf_df['lock_in_end'] = pd.to_datetime(ppf_df['lock_in_end'])
        else:
            # Calculate from first deposit
            if 'deposit_date' in ppf_df.columns:
                ppf_df['deposit_date'] = pd.to_datetime(ppf_df['deposit_date'])
                ppf_df['lock_in_end'] = ppf_df['deposit_date'] + timedelta(days=7*365)
            else:
                return []
        
        # Group by account to get earliest date per account
        accounts = ppf_df.groupby('account_number').agg({
            'lock_in_end': 'min',
            'calculated_balance': 'last',
            'current_balance': 'last'
        }).reset_index()
        
        for idx, row in accounts.iterrows():
            unlock_date = row['lock_in_end']
            account = str(row['account_number'])
            
            # Skip if not yet eligible
            if unlock_date > self.today + timedelta(days=365*5):  # Only show if within 5 years
                continue
            
            balance = float(row.get('calculated_balance', row.get('current_balance', 0)))
            
            # Max withdrawal is 50% of balance at end of 4th preceding year
            # Simplified: 50% of current balance
            max_withdrawal = balance * 0.5
            
            days_until = (unlock_date - self.today).days
            
            if days_until <= 0:
                # Already eligible
                event = CalendarEvent(
                    date=self.today,
                    event_type=EventType.PPF_WITHDRAWAL,
                    title=f"PPF Withdrawal Available: {account}",
                    description=f"Account eligible for partial withdrawal (max ₹{max_withdrawal:,.0f})",
                    value=max_withdrawal,
                    asset_type="PPF",
                    days_until=0,
                    actionable=f"Can withdraw up to 50% of balance (₹{max_withdrawal:,.0f}) for emergencies",
                    data={
                        'account': account,
                        'current_balance': balance,
                        'max_withdrawal': max_withdrawal,
                        'eligibility_date': unlock_date.strftime('%Y-%m-%d'),
                        'is_eligible': True
                    }
                )
            else:
                # Upcoming eligibility
                event = CalendarEvent(
                    date=unlock_date,
                    event_type=EventType.PPF_WITHDRAWAL,
                    title=f"PPF Eligibility: {account}",
                    description=f"Account becomes eligible for partial withdrawal in {days_until//365} years",
                    value=max_withdrawal,
                    asset_type="PPF",
                    days_until=days_until,
                    actionable=f"Continue contributions. Partial withdrawal available after {unlock_date.strftime('%b %Y')}",
                    data={
                        'account': account,
                        'current_balance': balance,
                        'eligibility_date': unlock_date.strftime('%Y-%m-%d'),
                        'is_eligible': False
                    }
                )
            
            events.append(event)
        
        self.events.extend(events)
        return events
    
    def add_nps_tier2_withdrawal(
        self, 
        nps_df: pd.DataFrame
    ) -> List[CalendarEvent]:
        """
        Add NPS Tier 2 withdrawal availability (no lock-in).
        
        Args:
            nps_df: DataFrame with NPS data
        
        Returns:
            List of NPS Tier 2 events
        """
        if nps_df.empty or 'tier' not in nps_df.columns:
            return []
        
        events = []
        tier2 = nps_df[nps_df['tier'] == 2]
        
        if tier2.empty:
            return []
        
        # Aggregate by PRAN
        tier2_summary = tier2.groupby('pran').agg({
            'current_value': 'sum',
            'returns_since_inception': 'mean'
        }).reset_index()
        
        for idx, row in tier2_summary.iterrows():
            pran = str(row['pran'])
            value = float(row['current_value'])
            returns = float(row.get('returns_since_inception', 0))
            
            event = CalendarEvent(
                date=self.today,
                event_type=EventType.NPS_WITHDRAWAL,
                title=f"NPS Tier-2 Available: {pran[:6]}...",
                description=f"Tier-2 balance of ₹{value:,.0f} available for withdrawal (no lock-in)",
                value=value,
                asset_type="NPS Tier-2",
                days_until=0,
                actionable="Tier-2 is liquid. Can withdraw for emergencies or rebalancing.",
                data={
                    'pran': pran,
                    'tier': 2,
                    'current_value': value,
                    'returns_pct': returns,
                    'is_liquid': True
                }
            )
            events.append(event)
        
        self.events.extend(events)
        return events
    
    def get_calendar_df(
        self, 
        filter_types: Optional[List[str]] = None,
        days_ahead: Optional[int] = None
    ) -> pd.DataFrame:
        """
        Get all events as a DataFrame, optionally filtered.
        
        Args:
            filter_types: List of event types to include (e.g., ['FD', 'ELSS'])
            days_ahead: Only show events within this many days
        
        Returns:
            DataFrame with calendar events
        """
        if not self.events:
            return pd.DataFrame(columns=[
                'date', 'event_type', 'title', 'description', 
                'value', 'asset_type', 'days_until', 'actionable'
            ])
        
        # Convert to DataFrame
        df = pd.DataFrame([e.to_dict() for e in self.events])
        
        # Filter by asset type if specified
        if filter_types:
            df = df[df['asset_type'].isin(filter_types)]
        
        # Filter by days ahead if specified
        if days_ahead is not None:
            df = df[df['days_until'] <= days_ahead]
        
        # Sort by date
        df = df.sort_values('date')
        
        return df
    
    def get_upcoming_liquidity_summary(self) -> Dict:
        """
        Get summary of upcoming liquidity events.
        
        Returns:
            Dictionary with liquidity breakdown
        """
        if not self.events:
            return {
                'total_upcoming_value': 0,
                'events_by_type': {},
                'next_30_days': 0,
                'next_90_days': 0,
                'next_12_months': 0
            }
        
        df = self.get_calendar_df()
        
        # Calculate totals by timeframe
        next_30 = df[df['days_until'] <= 30]['value'].sum()
        next_90 = df[df['days_until'] <= 90]['value'].sum()
        next_365 = df[df['days_until'] <= 365]['value'].sum()
        
        # Group by asset type
        by_type = df.groupby('asset_type')['value'].sum().to_dict()
        
        return {
            'total_upcoming_value': df['value'].sum(),
            'events_by_type': by_type,
            'next_30_days': next_30,
            'next_90_days': next_90,
            'next_12_months': next_365,
            'event_count': len(df),
            'events': df.to_dict('records')
        }
    
    def generate_full_calendar(
        self,
        fds_df: pd.DataFrame = None,
        transactions_df: pd.DataFrame = None,
        ppf_df: pd.DataFrame = None,
        nps_df: pd.DataFrame = None
    ) -> pd.DataFrame:
        """
        Generate complete liquidity calendar from all data sources.
        
        Returns:
            DataFrame with all calendar events
        """
        self.events = []  # Reset
        
        if fds_df is not None:
            self.add_fd_maturities(fds_df)
        
        if transactions_df is not None:
            self.add_elss_lockins(transactions_df)
            self.add_sip_dates(transactions_df)
        
        if ppf_df is not None:
            self.add_ppf_withdrawals(ppf_df)
        
        if nps_df is not None:
            self.add_nps_tier2_withdrawal(nps_df)
        
        return self.get_calendar_df()


def create_liquidity_calendar(
    fds_df: pd.DataFrame = None,
    transactions_df: pd.DataFrame = None,
    ppf_df: pd.DataFrame = None,
    nps_df: pd.DataFrame = None
) -> LiquidityCalendar:
    """
    Convenience function to create a fully populated calendar.
    
    Returns:
        LiquidityCalendar instance with all events loaded
    """
    calendar = LiquidityCalendar()
    calendar.generate_full_calendar(fds_df, transactions_df, ppf_df, nps_df)
    return calendar
