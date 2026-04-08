"""
Risk Metrics Module
Calculates portfolio risk metrics including volatility, Sharpe ratio, max drawdown,
rolling returns, and benchmark deviation.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import warnings


def portfolio_volatility(nav_history_df: pd.DataFrame, 
                         frequency: str = 'daily',
                         annualize: bool = True) -> Union[float, pd.Series]:
    """
    Calculate portfolio volatility (standard deviation of returns).
    
    Args:
        nav_history_df: DataFrame with columns ['date', 'nav'] or MultiIndex with schemes
        frequency: 'daily', 'weekly', 'monthly'
        annualize: Whether to annualize the volatility
        
    Returns:
        float or pd.Series of volatility values
    """
    if nav_history_df is None or nav_history_df.empty:
        return np.nan
    
    # Ensure date column exists
    if 'date' not in nav_history_df.columns and not isinstance(nav_history_df.index, pd.DatetimeIndex):
        raise ValueError("DataFrame must have 'date' column or DatetimeIndex")
    
    df = nav_history_df.copy()
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
    
    # Calculate returns
    if 'nav' in df.columns:
        returns = df['nav'].pct_change().dropna()
    else:
        # Assume all columns are NAV series
        returns = df.pct_change().dropna()
    
    if returns.empty:
        return np.nan
    
    # Calculate volatility
    if isinstance(returns, pd.Series):
        volatility = returns.std()
    else:
        volatility = returns.std()
    
    # Annualize
    if annualize:
        if frequency == 'daily':
            volatility = volatility * np.sqrt(252)
        elif frequency == 'weekly':
            volatility = volatility * np.sqrt(52)
        elif frequency == 'monthly':
            volatility = volatility * np.sqrt(12)
    
    return volatility


def sharpe_ratio(returns: Union[pd.Series, np.ndarray, List[float]],
                 risk_free_rate: float = 0.06,
                 frequency: str = 'daily') -> float:
    """
    Calculate Sharpe Ratio: (Portfolio Return - Risk Free Rate) / Portfolio Volatility
    
    Args:
        returns: Portfolio returns series
        risk_free_rate: Annual risk-free rate (default 6% for India 10Y GSec)
        frequency: Frequency of returns data
        
    Returns:
        Sharpe ratio value
    """
    if returns is None or len(returns) == 0:
        return np.nan
    
    returns = pd.Series(returns).dropna()
    
    if returns.empty:
        return np.nan
    
    # Convert annual risk-free rate to period rate
    if frequency == 'daily':
        period_rf = (1 + risk_free_rate) ** (1/252) - 1
        periods_per_year = 252
    elif frequency == 'weekly':
        period_rf = (1 + risk_free_rate) ** (1/52) - 1
        periods_per_year = 52
    elif frequency == 'monthly':
        period_rf = (1 + risk_free_rate) ** (1/12) - 1
        periods_per_year = 12
    else:
        period_rf = risk_free_rate
        periods_per_year = 1
    
    # Calculate annualized return
    mean_return = returns.mean()
    annualized_return = mean_return * periods_per_year
    
    # Calculate annualized volatility
    volatility = returns.std() * np.sqrt(periods_per_year)
    
    if volatility == 0:
        return 0.0
    
    sharpe = (annualized_return - risk_free_rate) / volatility
    
    return sharpe


def max_drawdown(nav_history_df: pd.DataFrame) -> Dict[str, Union[float, datetime]]:
    """
    Calculate maximum drawdown from peak to trough.
    
    Args:
        nav_history_df: DataFrame with columns ['date', 'nav']
        
    Returns:
        Dictionary with max_drawdown_pct, peak_date, trough_date, recovery_date
    """
    if nav_history_df is None or nav_history_df.empty:
        return {
            'max_drawdown_pct': 0.0,
            'peak_date': None,
            'trough_date': None,
            'recovery_date': None
        }
    
    df = nav_history_df.copy()
    
    # Ensure proper indexing
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
    
    if 'nav' in df.columns:
        nav_series = df['nav']
    else:
        nav_series = df.iloc[:, 0]  # Assume first column is NAV
    
    # Calculate running maximum
    running_max = nav_series.cummax()
    
    # Calculate drawdown
    drawdown = (nav_series - running_max) / running_max
    
    # Find maximum drawdown
    max_dd_idx = drawdown.idxmin()
    max_drawdown = drawdown.min()
    
    # Find peak before max drawdown
    peak_before_dd = running_max.loc[:max_dd_idx].idxmax()
    
    # Find recovery date (if any)
    recovery_date = None
    if max_dd_idx < nav_series.index[-1]:
        post_dd = nav_series.loc[max_dd_idx:]
        peak_value = running_max.loc[max_dd_idx]
        recovery_points = post_dd[post_dd >= peak_value]
        if not recovery_points.empty:
            recovery_date = recovery_points.index[0]
    
    return {
        'max_drawdown_pct': max_drawdown * 100,
        'peak_date': peak_before_dd,
        'trough_date': max_dd_idx,
        'recovery_date': recovery_date
    }


def rolling_returns(nav_history_df: pd.DataFrame,
                   windows: List[int] = [1, 3, 5],
                   window_unit: str = 'Y') -> pd.DataFrame:
    """
    Calculate rolling CAGR returns for specified windows.
    
    Args:
        nav_history_df: DataFrame with columns ['date', 'nav']
        windows: List of window periods (default [1, 3, 5] years)
        window_unit: 'Y' for years, 'M' for months
        
    Returns:
        DataFrame with rolling returns for each window
    """
    if nav_history_df is None or nav_history_df.empty:
        return pd.DataFrame()
    
    df = nav_history_df.copy()
    
    # Ensure proper indexing
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
    
    if 'nav' in df.columns:
        nav_series = df['nav']
    else:
        nav_series = df.iloc[:, 0]
    
    results = {}
    
    for window in windows:
        if window_unit == 'Y':
            days = window * 365
        else:
            days = window * 30
        
        # Calculate rolling returns
        rolling_rets = []
        dates = []
        
        for i in range(len(nav_series)):
            if i < days:
                rolling_rets.append(np.nan)
                dates.append(nav_series.index[i])
                continue
            
            start_nav = nav_series.iloc[i - days] if (i - days) >= 0 else nav_series.iloc[0]
            end_nav = nav_series.iloc[i]
            
            # CAGR calculation
            if start_nav > 0:
                years = days / 365
                cagr = ((end_nav / start_nav) ** (1/years)) - 1
                rolling_rets.append(cagr * 100)
            else:
                rolling_rets.append(np.nan)
            
            dates.append(nav_series.index[i])
        
        col_name = f"{window}{window_unit}"
        results[col_name] = rolling_rets
    
    result_df = pd.DataFrame(results, index=nav_series.index)
    return result_df


def benchmark_deviation(portfolio_returns: pd.Series,
                       benchmark_returns: pd.Series,
                       risk_free_rate: float = 0.06) -> Dict[str, float]:
    """
    Calculate alpha and other benchmark deviation metrics.
    
    Args:
        portfolio_returns: Portfolio daily/monthly returns
        benchmark_returns: Benchmark (e.g., Nifty 50) returns
        risk_free_rate: Annual risk-free rate
        
    Returns:
        Dictionary with alpha, beta, tracking_error, information_ratio, r_squared
    """
    if portfolio_returns is None or benchmark_returns is None:
        return {
            'alpha': np.nan,
            'beta': np.nan,
            'tracking_error': np.nan,
            'information_ratio': np.nan,
            'r_squared': np.nan
        }
    
    # Align series
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    
    if aligned.empty or len(aligned) < 2:
        return {
            'alpha': np.nan,
            'beta': np.nan,
            'tracking_error': np.nan,
            'information_ratio': np.nan,
            'r_squared': np.nan
        }
    
    port_rets = aligned.iloc[:, 0]
    bench_rets = aligned.iloc[:, 1]
    
    # Calculate beta (covariance / variance)
    covariance = port_rets.cov(bench_rets)
    benchmark_variance = bench_rets.var()
    
    if benchmark_variance == 0:
        beta = np.nan
    else:
        beta = covariance / benchmark_variance
    
    # Calculate alpha (excess return not explained by beta)
    port_mean = port_rets.mean() * 252  # Annualize
    bench_mean = bench_rets.mean() * 252
    period_rf = risk_free_rate / 252
    
    if np.isnan(beta):
        alpha = np.nan
    else:
        alpha = (port_mean - risk_free_rate) - beta * (bench_mean - risk_free_rate)
    
    # Tracking error (standard deviation of excess returns)
    excess_returns = port_rets - bench_rets
    tracking_error = excess_returns.std() * np.sqrt(252)
    
    # Information ratio (alpha / tracking error)
    if tracking_error == 0 or np.isnan(tracking_error):
        information_ratio = np.nan
    else:
        information_ratio = alpha / tracking_error
    
    # R-squared (correlation squared)
    correlation = port_rets.corr(bench_rets)
    r_squared = correlation ** 2 if not np.isnan(correlation) else np.nan
    
    return {
        'alpha': alpha,
        'beta': beta,
        'tracking_error': tracking_error,
        'information_ratio': information_ratio,
        'r_squared': r_squared
    }


def calculate_risk_score(nav_history_df: pd.DataFrame,
                        concentration_data: Optional[Dict] = None,
                        liquidity_data: Optional[Dict] = None) -> Dict[str, Union[int, str]]:
    """
    Calculate overall risk score (0-100) based on multiple factors.
    
    Args:
        nav_history_df: Historical NAV data
        concentration_data: Dictionary with concentration metrics
        liquidity_data: Dictionary with liquidity metrics
        
    Returns:
        Dictionary with risk_score, risk_level, components
    """
    scores = {}
    
    # Volatility risk (0-35 points)
    volatility = portfolio_volatility(nav_history_df)
    if np.isnan(volatility):
        scores['volatility'] = 15  # Default moderate
    elif volatility < 0.10:
        scores['volatility'] = 5
    elif volatility < 0.15:
        scores['volatility'] = 15
    elif volatility < 0.25:
        scores['volatility'] = 25
    else:
        scores['volatility'] = 35
    
    # Concentration risk (0-30 points)
    if concentration_data:
        max_concentration = concentration_data.get('max_scheme_concentration', 0.1)
        if max_concentration > 0.25:
            scores['concentration'] = 30
        elif max_concentration > 0.20:
            scores['concentration'] = 20
        elif max_concentration > 0.15:
            scores['concentration'] = 15
        else:
            scores['concentration'] = 5
    else:
        scores['concentration'] = 15
    
    # Liquidity risk (0-20 points)
    if liquidity_data:
        illiquid_pct = liquidity_data.get('illiquid_allocation', 0.1)
        if illiquid_pct > 0.30:
            scores['liquidity'] = 20
        elif illiquid_pct > 0.20:
            scores['liquidity'] = 15
        elif illiquid_pct > 0.10:
            scores['liquidity'] = 10
        else:
            scores['liquidity'] = 5
    else:
        scores['liquidity'] = 10
    
    # Drawdown risk (0-15 points)
    dd_info = max_drawdown(nav_history_df)
    max_dd = abs(dd_info['max_drawdown_pct'])
    if max_dd > 40:
        scores['drawdown'] = 15
    elif max_dd > 25:
        scores['drawdown'] = 10
    elif max_dd > 15:
        scores['drawdown'] = 7
    else:
        scores['drawdown'] = 3
    
    total_score = sum(scores.values())
    
    # Determine risk level
    if total_score >= 70:
        risk_level = "High"
    elif total_score >= 45:
        risk_level = "Moderate-High"
    elif total_score >= 25:
        risk_level = "Moderate"
    else:
        risk_level = "Low"
    
    return {
        'risk_score': total_score,
        'risk_level': risk_level,
        'components': scores,
        'max_possible': 100
    }


def calculate_var(returns: pd.Series, 
                  confidence: float = 0.95,
                  method: str = 'historical') -> float:
    """
    Calculate Value at Risk (VaR).
    
    Args:
        returns: Return series
        confidence: Confidence level (default 95%)
        method: 'historical' or 'parametric'
        
    Returns:
        VaR value (positive number represents loss)
    """
    if returns is None or returns.empty:
        return np.nan
    
    returns = returns.dropna()
    
    if method == 'historical':
        var = np.percentile(returns, (1 - confidence) * 100)
    else:
        mean = returns.mean()
        std = returns.std()
        z_score = np.percentile(np.random.standard_normal(10000), (1 - confidence) * 100)
        var = mean + z_score * std
    
    return abs(var)


def get_drawdown_series(nav_history_df: pd.DataFrame) -> pd.DataFrame:
    """
    Get drawdown series for plotting.
    
    Args:
        nav_history_df: DataFrame with NAV history
        
    Returns:
        DataFrame with drawdown percentages over time
    """
    if nav_history_df is None or nav_history_df.empty:
        return pd.DataFrame()
    
    df = nav_history_df.copy()
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
    
    if 'nav' in df.columns:
        nav_series = df['nav']
    else:
        nav_series = df.iloc[:, 0]
    
    running_max = nav_series.cummax()
    drawdown = ((nav_series - running_max) / running_max) * 100
    
    result = pd.DataFrame({
        'drawdown_pct': drawdown,
        'nav': nav_series,
        'running_max': running_max
    })
    
    return result
