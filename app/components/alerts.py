"""
Alert Rule Engine for Portfolio Analytics.
Generates actionable alerts with severity levels (red/yellow/green).
"""

import pandas as pd
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    """Alert severity levels."""
    CRITICAL = "red"
    WARNING = "yellow"
    OK = "green"
    INFO = "blue"


@dataclass
class Alert:
    """Alert data structure."""
    title: str
    message: str
    severity: Severity
    category: str
    metric_value: float
    threshold: float
    actionable: str = ""
    data: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            'title': self.title,
            'message': self.message,
            'severity': self.severity.value,
            'category': self.category,
            'metric_value': self.metric_value,
            'threshold': self.threshold,
            'actionable': self.actionable,
            'timestamp': datetime.now().isoformat()
        }


class AlertEngine:
    """Portfolio alert rule engine."""
    
    def __init__(self, config_path: str = "config/limits.yaml"):
        """Initialize with threshold configuration."""
        self.config = self._load_config(config_path)
        self.alerts: List[Alert] = []
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML."""
        default_config = {
            'concentration_limit': 0.15,
            'top3_limit': 0.50,
            'cash_limit': 0.10,
            'equity_deviation': 0.05,
            'elss_warning_months': 3,
            'alert_severity': {
                'critical': {'concentration': 0.20, 'cash_drag': 0.15, 'top3_concentration': 0.60},
                'warning': {'concentration': 0.15, 'cash_drag': 0.10, 'top3_concentration': 0.50}
            }
        }
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
                if config:
                    return {**default_config, **config}
        except Exception as e:
            print(f"Warning: Could not load config from {config_path}: {e}")
        
        return default_config
    
    def check_concentration(
        self, 
        holdings_df: pd.DataFrame, 
        threshold: Optional[float] = None
    ) -> List[Alert]:
        """
        Check if any single holding exceeds concentration threshold.
        
        Args:
            holdings_df: DataFrame with columns: scheme_name, current_value
            threshold: Max % of portfolio for single holding (default 15%)
        
        Returns:
            List of concentration alerts
        """
        if holdings_df.empty or 'current_value' not in holdings_df.columns:
            return []
        
        alerts = []
        total_value = holdings_df['current_value'].sum()
        
        if total_value == 0:
            return []
        
        # Use configured thresholds
        warning_threshold = threshold or self.config.get('concentration_limit', 0.15)
        critical_threshold = self.config.get('alert_severity', {}).get('critical', {}).get('concentration', 0.20)
        
        for idx, row in holdings_df.iterrows():
            value = float(row['current_value'])
            scheme = str(row.get('scheme_name', f'Holding {idx}'))
            percentage = value / total_value
            
            if percentage > critical_threshold:
                # Calculate reduction needed
                excess_amount = value - (critical_threshold * total_value)
                
                alert = Alert(
                    title=f"Critical Concentration Risk: {scheme}",
                    message=f"{scheme} is {percentage:.1%} of portfolio (limit: {critical_threshold:.0%})",
                    severity=Severity.CRITICAL,
                    category="concentration",
                    metric_value=percentage,
                    threshold=critical_threshold,
                    actionable=f"Reduce {scheme} by ₹{excess_amount:,.0f} to reach {critical_threshold:.0%} limit",
                    data={'scheme': scheme, 'current_value': value, 'target_value': critical_threshold * total_value}
                )
                alerts.append(alert)
                
            elif percentage > warning_threshold:
                # Calculate buffer
                buffer_amount = (critical_threshold * total_value) - value
                
                alert = Alert(
                    title=f"High Concentration: {scheme}",
                    message=f"{scheme} is {percentage:.1%} of portfolio (warning at {warning_threshold:.0%})",
                    severity=Severity.WARNING,
                    category="concentration",
                    metric_value=percentage,
                    threshold=warning_threshold,
                    actionable=f"Monitor closely. ₹{buffer_amount:,.0f} buffer before critical limit",
                    data={'scheme': scheme, 'current_value': value}
                )
                alerts.append(alert)
        
        self.alerts.extend(alerts)
        return alerts
    
    def check_top3_concentration(
        self, 
        holdings_df: pd.DataFrame, 
        threshold: Optional[float] = None
    ) -> List[Alert]:
        """
        Check if top 3 holdings exceed combined threshold.
        
        Args:
            holdings_df: DataFrame with holdings data
            threshold: Max % for top 3 holdings combined (default 50%)
        
        Returns:
            List of top3 concentration alerts
        """
        if holdings_df.empty or 'current_value' not in holdings_df.columns:
            return []
        
        alerts = []
        total_value = holdings_df['current_value'].sum()
        
        if total_value == 0 or len(holdings_df) < 3:
            return []
        
        # Get top 3 by value
        top3 = holdings_df.nlargest(3, 'current_value')
        top3_value = top3['current_value'].sum()
        top3_percentage = top3_value / total_value
        
        # Get threshold
        warning_threshold = threshold or self.config.get('top3_limit', 0.50)
        critical_threshold = self.config.get('alert_severity', {}).get('critical', {}).get('top3_concentration', 0.60)
        
        scheme_names = top3['scheme_name'].tolist()
        schemes_text = ", ".join(scheme_names)
        
        if top3_percentage > critical_threshold:
            excess_value = top3_value - (critical_threshold * total_value)
            
            alert = Alert(
                title="Critical Top-3 Concentration",
                message=f"Top 3 holdings ({schemes_text}) are {top3_percentage:.1%} of portfolio",
                severity=Severity.CRITICAL,
                category="concentration",
                metric_value=top3_percentage,
                threshold=critical_threshold,
                actionable=f"Reduce top 3 holdings by ₹{excess_value:,.0f} to reach {critical_threshold:.0%} limit",
                data={'top3_schemes': scheme_names, 'top3_value': top3_value, 'total_value': total_value}
            )
            alerts.append(alert)
            
        elif top3_percentage > warning_threshold:
            alert = Alert(
                title="High Top-3 Concentration",
                message=f"Top 3 holdings ({schemes_text}) are {top3_percentage:.1%} of portfolio",
                severity=Severity.WARNING,
                category="concentration",
                metric_value=top3_percentage,
                threshold=warning_threshold,
                actionable="Consider diversifying into additional schemes",
                data={'top3_schemes': scheme_names, 'top3_value': top3_value}
            )
            alerts.append(alert)
        else:
            # Green status
            alert = Alert(
                title="Top-3 Concentration Healthy",
                message=f"Top 3 holdings are {top3_percentage:.1%} of portfolio (limit: {warning_threshold:.0%})",
                severity=Severity.OK,
                category="concentration",
                metric_value=top3_percentage,
                threshold=warning_threshold,
                actionable="No action needed",
                data={'top3_schemes': scheme_names}
            )
            alerts.append(alert)
        
        self.alerts.extend(alerts)
        return alerts
    
    def check_cash_drag(
        self, 
        cash_value: float, 
        total_portfolio_value: float,
        threshold: Optional[float] = None
    ) -> List[Alert]:
        """
        Check if cash percentage indicates cash drag.
        
        Args:
            cash_value: Current cash/savings value
            total_portfolio_value: Total portfolio including investments
            threshold: Max recommended cash % (default 10%)
        
        Returns:
            List of cash drag alerts
        """
        alerts = []
        
        if total_portfolio_value == 0:
            return []
        
        cash_percentage = cash_value / total_portfolio_value
        
        # Get thresholds
        warning_threshold = threshold or self.config.get('cash_limit', 0.10)
        critical_threshold = self.config.get('alert_severity', {}).get('critical', {}).get('cash_drag', 0.15)
        min_buffer = self.config.get('min_cash_buffer', 0.03)
        
        if cash_percentage > critical_threshold:
            excess_cash = cash_value - (warning_threshold * total_portfolio_value)
            
            alert = Alert(
                title="Critical Cash Drag",
                message=f"Cash is {cash_percentage:.1%} of portfolio (₹{cash_value:,.0f})",
                severity=Severity.CRITICAL,
                category="cash_management",
                metric_value=cash_percentage,
                threshold=critical_threshold,
                actionable=f"Deploy ₹{excess_cash:,.0f} to investments to optimize returns",
                data={'cash_value': cash_value, 'recommended_max': warning_threshold * total_portfolio_value}
            )
            alerts.append(alert)
            
        elif cash_percentage > warning_threshold:
            alert = Alert(
                title="High Cash Level",
                message=f"Cash is {cash_percentage:.1%} of portfolio (₹{cash_value:,.0f})",
                severity=Severity.WARNING,
                category="cash_management",
                metric_value=cash_percentage,
                threshold=warning_threshold,
                actionable="Consider investing excess cash or moving to liquid funds",
                data={'cash_value': cash_value}
            )
            alerts.append(alert)
            
        elif cash_percentage < min_buffer:
            recommended = min_buffer * total_portfolio_value
            
            alert = Alert(
                title="Low Cash Buffer",
                message=f"Cash is only {cash_percentage:.1%} of portfolio (₹{cash_value:,.0f})",
                severity=Severity.WARNING,
                category="cash_management",
                metric_value=cash_percentage,
                threshold=min_buffer,
                actionable=f"Maintain at least ₹{recommended:,.0f} ({min_buffer:.0%}) for emergencies",
                data={'cash_value': cash_value, 'recommended_min': recommended}
            )
            alerts.append(alert)
        else:
            alert = Alert(
                title="Cash Level Optimal",
                message=f"Cash is {cash_percentage:.1%} of portfolio (₹{cash_value:,.0f})",
                severity=Severity.OK,
                category="cash_management",
                metric_value=cash_percentage,
                threshold=warning_threshold,
                actionable="Cash allocation is within recommended range",
                data={'cash_value': cash_value}
            )
            alerts.append(alert)
        
        self.alerts.extend(alerts)
        return alerts
    
    def check_elss_lockin(
        self, 
        transactions_df: pd.DataFrame,
        months_before: int = 3
    ) -> List[Alert]:
        """
        Check for ELSS funds nearing lock-in end.
        
        Args:
            transactions_df: DataFrame with columns: scheme_name, date, amount, is_elss, lock_in_end
            months_before: Months before lock-in end to start warning
        
        Returns:
            List of ELSS lock-in alerts
        """
        if transactions_df.empty:
            return []
        
        alerts = []
        today = datetime.now()
        warning_window = today + timedelta(days=30 * months_before)
        unlock_window = today + timedelta(days=365)  # Next 12 months
        
        # Filter ELSS transactions
        if 'is_elss' in transactions_df.columns:
            elss_df = transactions_df[transactions_df['is_elss'] == True].copy()
        elif 'scheme_name' in transactions_df.columns:
            # Infer ELSS from scheme name
            elss_keywords = ['elss', 'tax', 'savings', '80c', 'taxsaver']
            mask = transactions_df['scheme_name'].str.lower().str.contains('|'.join(elss_keywords), na=False)
            elss_df = transactions_df[mask].copy()
        else:
            return []
        
        if elss_df.empty:
            return []
        
        # Check for lock_in_end column
        if 'lock_in_end' in elss_df.columns:
            elss_df['lock_in_end'] = pd.to_datetime(elss_df['lock_in_end'], errors='coerce')
        else:
            # Estimate 3 years from purchase date
            elss_df['date'] = pd.to_datetime(elss_df.get('date', elss_df.get('purchase_date', today)))
            elss_df['lock_in_end'] = elss_df['date'] + timedelta(days=3*365)
        
        # Find ELSS unlocking soon
        unlocking_soon = elss_df[
            (elss_df['lock_in_end'] >= today) & 
            (elss_df['lock_in_end'] <= warning_window)
        ].copy()
        
        for idx, row in unlocking_soon.iterrows():
            scheme = str(row.get('scheme_name', 'Unknown ELSS'))
            lock_end = row['lock_in_end']
            amount = float(row.get('amount', 0))
            days_remaining = (lock_end - today).days
            
            alert = Alert(
                title=f"ELSS Lock-in Ending Soon: {scheme}",
                message=f"{scheme} lock-in ends in {days_remaining} days ({lock_end.strftime('%Y-%m-%d')})",
                severity=Severity.INFO,
                category="liquidity",
                metric_value=days_remaining,
                threshold=months_before * 30,
                actionable=f"₹{amount:,.0f} will be available for redemption/rebalancing after {lock_end.strftime('%b %Y')}",
                data={'scheme': scheme, 'unlock_date': lock_end.isoformat(), 'amount': amount}
            )
            alerts.append(alert)
        
        # Find ELSS already unlocked in past 12 months
        recently_unlocked = elss_df[
            (elss_df['lock_in_end'] < today) & 
            (elss_df['lock_in_end'] >= today - timedelta(days=365))
        ].copy()
        
        for idx, row in recently_unlocked.iterrows():
            scheme = str(row.get('scheme_name', 'Unknown ELSS'))
            lock_end = row['lock_in_end']
            amount = float(row.get('amount', 0))
            days_since = (today - lock_end).days
            
            alert = Alert(
                title=f"ELSS Unlocked: {scheme}",
                message=f"{scheme} lock-in ended {days_since} days ago ({lock_end.strftime('%Y-%m-%d')})",
                severity=Severity.OK,
                category="liquidity",
                metric_value=days_since,
                threshold=365,
                actionable=f"₹{amount:,.0f} available for rebalancing if needed",
                data={'scheme': scheme, 'unlocked_date': lock_end.isoformat(), 'amount': amount}
            )
            alerts.append(alert)
        
        self.alerts.extend(alerts)
        return alerts
    
    def check_allocation_drift(
        self,
        current_allocation: Dict[str, float],
        target_allocation: Dict[str, float]
    ) -> List[Alert]:
        """
        Check if current allocation has drifted from target.
        
        Args:
            current_allocation: Dict of {asset_class: percentage}
            target_allocation: Dict of {asset_class: target_percentage}
        
        Returns:
            List of allocation drift alerts
        """
        alerts = []
        deviation_threshold = self.config.get('equity_deviation', 0.05)
        
        all_classes = set(current_allocation.keys()) | set(target_allocation.keys())
        
        for asset_class in all_classes:
            current = current_allocation.get(asset_class, 0)
            target = target_allocation.get(asset_class, 0)
            deviation = abs(current - target)
            
            if deviation > deviation_threshold:
                direction = "over" if current > target else "under"
                diff_amount = abs(current - target)
                
                alert = Alert(
                    title=f"Allocation Drift: {asset_class.title()}",
                    message=f"{asset_class.title()} is {current:.1%} (target: {target:.1%}, deviation: {deviation:.1%})",
                    severity=Severity.WARNING if deviation > 0.10 else Severity.INFO,
                    category="allocation",
                    metric_value=current,
                    threshold=target,
                    actionable=f"{asset_class.title()} is {direction} by {diff_amount:.1%} - consider rebalancing",
                    data={'asset_class': asset_class, 'current': current, 'target': target}
                )
                alerts.append(alert)
        
        self.alerts.extend(alerts)
        return alerts
    
    def check_fd_maturity_gap(
        self,
        fds_df: pd.DataFrame,
        min_liquidity_needed: float = 0
    ) -> List[Alert]:
        """
        Check for FD maturity gaps and liquidity concerns.
        
        Args:
            fds_df: DataFrame with FD data
            min_liquidity_needed: Minimum liquidity needed in near term
        
        Returns:
            List of FD maturity alerts
        """
        if fds_df.empty:
            return []
        
        alerts = []
        today = datetime.now()
        
        if 'maturity_date' in fds_df.columns:
            fds_df['maturity_date'] = pd.to_datetime(fds_df['maturity_date'])
            
            # Check for maturing in next 90 days (opportunity for reinvestment)
            maturing_soon = fds_df[
                fds_df['maturity_date'].between(today, today + timedelta(days=90))
            ]
            
            for idx, row in maturing_soon.iterrows():
                scheme = str(row.get('institution', 'FD'))
                value = float(row.get('current_value', row.get('principal', 0)))
                maturity = row['maturity_date']
                
                alert = Alert(
                    title=f"FD Maturing: {scheme}",
                    message=f"{scheme} FD of ₹{value:,.0f} matures on {maturity.strftime('%Y-%m-%d')}",
                    severity=Severity.INFO,
                    category="liquidity",
                    metric_value=value,
                    threshold=0,
                    actionable="Plan reinvestment or use for rebalancing",
                    data={'institution': scheme, 'maturity_date': maturity.isoformat(), 'value': value}
                )
                alerts.append(alert)
            
            # Check for gaps in maturity (ladder analysis)
            future_fds = fds_df[fds_df['maturity_date'] > today].copy()
            if not future_fds.empty:
                future_fds = future_fds.sort_values('maturity_date')
                
                # Check if any gap > 6 months
                for i in range(len(future_fds) - 1):
                    current_maturity = future_fds.iloc[i]['maturity_date']
                    next_maturity = future_fds.iloc[i + 1]['maturity_date']
                    gap_days = (next_maturity - current_maturity).days
                    
                    if gap_days > 180:
                        alert = Alert(
                            title="FD Maturity Gap Detected",
                            message=f"{gap_days//30} month gap between FD maturities",
                            severity=Severity.WARNING,
                            category="liquidity",
                            metric_value=gap_days,
                            threshold=180,
                            actionable="Consider staggering FDs for better liquidity management",
                            data={'gap_days': gap_days}
                        )
                        alerts.append(alert)
                        break  # Only report first gap
        
        self.alerts.extend(alerts)
        return alerts
    
    def generate_alerts_report(
        self,
        holdings_df: pd.DataFrame = None,
        transactions_df: pd.DataFrame = None,
        cash_value: float = 0,
        total_portfolio_value: float = 0,
        fds_df: pd.DataFrame = None,
        target_allocation: Dict[str, float] = None,
        current_allocation: Dict[str, float] = None
    ) -> Dict:
        """
        Generate comprehensive alerts report.
        
        Returns:
            Dictionary with all alerts categorized by severity
        """
        self.alerts = []  # Reset alerts
        
        # Run all checks
        if holdings_df is not None and not holdings_df.empty:
            self.check_concentration(holdings_df)
            self.check_top3_concentration(holdings_df)
        
        if total_portfolio_value > 0:
            self.check_cash_drag(cash_value, total_portfolio_value)
        
        if transactions_df is not None and not transactions_df.empty:
            self.check_elss_lockin(transactions_df)
        
        if fds_df is not None and not fds_df.empty:
            self.check_fd_maturity_gap(fds_df)
        
        if current_allocation and target_allocation:
            self.check_allocation_drift(current_allocation, target_allocation)
        
        # Categorize by severity
        critical = [a for a in self.alerts if a.severity == Severity.CRITICAL]
        warnings = [a for a in self.alerts if a.severity == Severity.WARNING]
        info = [a for a in self.alerts if a.severity == Severity.INFO]
        ok = [a for a in self.alerts if a.severity == Severity.OK]
        
        return {
            'summary': {
                'critical_count': len(critical),
                'warning_count': len(warnings),
                'info_count': len(info),
                'ok_count': len(ok),
                'total': len(self.alerts),
                'generated_at': datetime.now().isoformat()
            },
            'critical': [a.to_dict() for a in critical],
            'warnings': [a.to_dict() for a in warnings],
            'info': [a.to_dict() for a in info],
            'ok': [a.to_dict() for a in ok],
            'all_alerts': [a.to_dict() for a in self.alerts]
        }
    
    def get_alerts_df(self) -> pd.DataFrame:
        """Get all alerts as a DataFrame for display."""
        if not self.alerts:
            return pd.DataFrame(columns=['title', 'message', 'severity', 'category', 'actionable'])
        
        return pd.DataFrame([a.to_dict() for a in self.alerts])


def generate_alerts_report(**kwargs) -> Dict:
    """
    Standalone function to generate alerts report.
    
    Usage:
        report = generate_alerts_report(
            holdings_df=holdings,
            cash_value=50000,
            total_portfolio_value=500000
        )
    """
    engine = AlertEngine()
    return engine.generate_alerts_report(**kwargs)
