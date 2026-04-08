"""
XIRR (Extended Internal Rate of Return) Calculator
Handles irregular cashflows for mutual fund investments.
Uses Newton-Raphson method for solving.
"""

import logging
from datetime import datetime, date
from typing import List, Tuple, Optional
import math

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def days_between(date1: datetime, date2: datetime) -> int:
    """Calculate days between two dates."""
    delta = date2 - date1
    return delta.days


def xnpv(rate: float, cashflows: List[Tuple[datetime, float]], reference_date: Optional[datetime] = None) -> float:
    """
    Calculate Net Present Value for irregular cashflows.
    
    Args:
        rate: Discount rate (daily rate, not annual)
        cashflows: List of (date, amount) tuples
        reference_date: Base date for NPV calculation (default: earliest date)
    
    Returns:
        Net Present Value
    """
    if not cashflows:
        return 0.0
    
    if reference_date is None:
        reference_date = min(cf[0] for cf in cashflows)
    
    npv = 0.0
    for cf_date, amount in cashflows:
        days = days_between(reference_date, cf_date)
        # Convert annual rate to daily compounding
        npv += amount / ((1 + rate) ** (days / 365.0))
    
    return npv


def xirr_derivative(rate: float, cashflows: List[Tuple[datetime, float]], reference_date: datetime) -> float:
    """
    Calculate derivative of NPV for Newton-Raphson method.
    
    Args:
        rate: Current rate estimate
        cashflows: List of (date, amount) tuples
        reference_date: Base date for calculation
    
    Returns:
        Derivative of NPV with respect to rate
    """
    derivative = 0.0
    for cf_date, amount in cashflows:
        days = days_between(reference_date, cf_date)
        if days != 0:
            derivative -= (days / 365.0) * amount / ((1 + rate) ** ((days / 365.0) + 1))
    return derivative


def calculate_xirr(
    cashflows: List[Tuple[datetime, float]], 
    guess: float = 0.1,
    max_iterations: int = 1000,
    precision: float = 1e-10,
    min_rate: float = -0.999999,
    max_rate: float = 1e6
) -> Optional[float]:
    """
    Calculate XIRR using Newton-Raphson method.
    
    Args:
        cashflows: List of (date, amount) tuples. Negative for outflows (investments),
                   positive for inflows (redemptions, dividends)
        guess: Initial guess for the rate (default 10%)
        max_iterations: Maximum Newton-Raphson iterations
        precision: Convergence threshold
        min_rate: Minimum allowed rate to prevent overflow
        max_rate: Maximum allowed rate to prevent overflow
    
    Returns:
        Annualized XIRR as decimal (e.g., 0.15 for 15%), or None if calculation fails
    """
    if len(cashflows) < 2:
        logger.warning("Need at least 2 cashflows for XIRR calculation")
        return None
    
    # Filter out zero amounts
    cashflows = [(d, a) for d, a in cashflows if abs(a) > 0.0001]
    
    if len(cashflows) < 2:
        logger.warning("Need at least 2 non-zero cashflows for XIRR calculation")
        return None
    
    # Check if all cashflows have same sign (no solution possible)
    signs = [1 if a > 0 else -1 for d, a in cashflows]
    if all(s > 0 for s in signs) or all(s < 0 for s in signs):
        logger.warning("All cashflows have same sign - XIRR cannot be calculated")
        return None
    
    # Use earliest date as reference
    reference_date = min(cf[0] for cf in cashflows)
    
    # Initial guess rate (daily rate approximation)
    rate = (1 + guess) ** (1 / 365.0) - 1
    
    for iteration in range(max_iterations):
        try:
            # Calculate NPV at current rate
            npv = xnpv(rate, cashflows, reference_date)
            
            # Check if we've converged
            if abs(npv) < precision:
                # Convert daily rate to annual
                annual_rate = (1 + rate) ** 365 - 1
                return annual_rate
            
            # Calculate derivative
            deriv = xirr_derivative(rate, cashflows, reference_date)
            
            # Avoid division by zero or very small derivative
            if abs(deriv) < 1e-300:
                logger.warning("Derivative too small, switching to bisection")
                break
            
            # Newton-Raphson update
            new_rate = rate - npv / deriv
            
            # Clamp rate to prevent divergence
            new_rate = max(min_rate, min(max_rate, new_rate))
            
            # Check for convergence in rate
            if abs(new_rate - rate) < precision:
                annual_rate = (1 + new_rate) ** 365 - 1
                return annual_rate
            
            rate = new_rate
            
        except (OverflowError, ValueError) as e:
            logger.warning(f"Numerical error in Newton-Raphson: {e}")
            break
    
    # If Newton-Raphson failed, try bisection method
    return _xirr_bisection(cashflows, reference_date, min_rate, max_rate, precision)


def _xirr_bisection(
    cashflows: List[Tuple[datetime, float]], 
    reference_date: datetime,
    min_rate: float,
    max_rate: float,
    precision: float,
    max_iterations: int = 1000
) -> Optional[float]:
    """
    Fallback bisection method for XIRR calculation.
    More robust but slower than Newton-Raphson.
    """
    # Convert annual bounds to daily
    low = (1 + min_rate) ** (1 / 365.0) - 1 if min_rate > -1 else -0.999
    high = (1 + max_rate) ** (1 / 365.0) - 1
    
    # Ensure signs are different
    low_npv = xnpv(low, cashflows, reference_date)
    high_npv = xnpv(high, cashflows, reference_date)
    
    # If both have same sign, expand the range
    if low_npv * high_npv > 0:
        # Try wider range
        low = -0.999
        high = 1.0  # Very high daily rate
        low_npv = xnpv(low, cashflows, reference_date)
        high_npv = xnpv(high, cashflows, reference_date)
        
        if low_npv * high_npv > 0:
            logger.warning("Cannot find rate bracket with different signs")
            return None
    
    for _ in range(max_iterations):
        mid = (low + high) / 2.0
        mid_npv = xnpv(mid, cashflows, reference_date)
        
        if abs(mid_npv) < precision:
            annual_rate = (1 + mid) ** 365 - 1
            return annual_rate
        
        # Narrow the bracket
        if low_npv * mid_npv < 0:
            high = mid
            high_npv = mid_npv
        else:
            low = mid
            low_npv = mid_npv
        
        if abs(high - low) < precision:
            mid = (low + high) / 2.0
            annual_rate = (1 + mid) ** 365 - 1
            return annual_rate
    
    logger.warning("Bisection method did not converge")
    return None


def calculate_xirr_safe(
    cashflows: List[Tuple[datetime, float]],
    default_return: Optional[float] = None
) -> Optional[float]:
    """
    Calculate XIRR with error handling.
    
    Args:
        cashflows: List of (date, amount) tuples
        default_return: Value to return if calculation fails
    
    Returns:
        Annualized XIRR or default_return if calculation fails
    """
    try:
        result = calculate_xirr(cashflows)
        return result if result is not None else default_return
    except Exception as e:
        logger.error(f"XIRR calculation failed: {e}")
        return default_return


def format_xirr(xirr_value: Optional[float]) -> str:
    """
    Format XIRR value for display.
    
    Args:
        xirr_value: XIRR as decimal
    
    Returns:
        Formatted string (e.g., "15.23%" or "N/A")
    """
    if xirr_value is None:
        return "N/A"
    
    if math.isnan(xirr_value) or math.isinf(xirr_value):
        return "N/A"
    
    # Handle extreme values
    if abs(xirr_value) > 100:
        return "N/A"
    
    return f"{xirr_value * 100:.2f}%"


def calculate_xirr_from_transactions(
    transactions: List[dict],
    current_value: Optional[float] = None,
    current_date: Optional[datetime] = None
) -> Optional[float]:
    """
    Calculate XIRR from transaction history.
    
    Args:
        transactions: List of transaction dicts with 'date' (str or datetime) and 'amount' and 'type' keys
        current_value: Current market value of holdings (positive cashflow)
        current_date: Date for current value (default: today)
    
    Returns:
        Annualized XIRR
    """
    cashflows = []
    
    for tx in transactions:
        # Parse date
        tx_date = tx.get('date')
        if isinstance(tx_date, str):
            try:
                tx_date = datetime.strptime(tx_date, '%Y-%m-%d')
            except ValueError:
                try:
                    tx_date = datetime.strptime(tx_date, '%d-%m-%Y')
                except ValueError:
                    continue
        
        if not isinstance(tx_date, datetime):
            continue
        
        amount = float(tx.get('amount', 0))
        tx_type = tx.get('type', 'PURCHASE').upper()
        
        # Adjust sign based on transaction type
        if tx_type in ['PURCHASE', 'SIP', 'BUY']:
            cashflows.append((tx_date, -abs(amount)))
        elif tx_type in ['REDEMPTION', 'SELL', 'SWITCH_OUT']:
            cashflows.append((tx_date, abs(amount)))
        elif tx_type == 'DIVIDEND':
            cashflows.append((tx_date, abs(amount)))
    
    # Add current value as final positive cashflow
    if current_value and current_value > 0:
        if current_date is None:
            current_date = datetime.now()
        cashflows.append((current_date, current_value))
    
    return calculate_xirr_safe(cashflows)


# Example usage and testing
if __name__ == "__main__":
    # Test with a simple SIP example
    print("Testing XIRR calculation...")
    
    # Example: SIP of 1000 for 12 months, current value 13000
    sip_cashflows = [
        (datetime(2023, 1, 1), -1000),
        (datetime(2023, 2, 1), -1000),
        (datetime(2023, 3, 1), -1000),
        (datetime(2023, 4, 1), -1000),
        (datetime(2023, 5, 1), -1000),
        (datetime(2023, 6, 1), -1000),
        (datetime(2023, 7, 1), -1000),
        (datetime(2023, 8, 1), -1000),
        (datetime(2023, 9, 1), -1000),
        (datetime(2023, 10, 1), -1000),
        (datetime(2023, 11, 1), -1000),
        (datetime(2023, 12, 1), -1000),
        (datetime(2023, 12, 31), 13000),  # Current value
    ]
    
    xirr_result = calculate_xirr(sip_cashflows)
    print(f"SIP XIRR: {format_xirr(xirr_result)}")
    
    # Test with redemption
    redemption_cashflows = [
        (datetime(2023, 1, 1), -10000),  # Lump sum investment
        (datetime(2023, 7, 1), 5000),    # Partial redemption
        (datetime(2023, 12, 31), 6000),  # Current value
    ]
    
    xirr_result2 = calculate_xirr(redemption_cashflows)
    print(f"Redemption XIRR: {format_xirr(xirr_result2)}")
    
    # Test edge cases
    print("\nTesting edge cases...")
    
    # All same sign (should fail)
    same_sign = [
        (datetime(2023, 1, 1), 1000),
        (datetime(2023, 2, 1), 2000),
    ]
    print(f"Same sign: {format_xirr(calculate_xirr(same_sign))}")
    
    # Single cashflow (should fail)
    single = [(datetime(2023, 1, 1), -1000)]
    print(f"Single: {format_xirr(calculate_xirr(single))}")
    
    # Empty (should fail)
    print(f"Empty: {format_xirr(calculate_xirr([]))}")
