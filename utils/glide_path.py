"""
Glide Path Module
Manages age-based asset allocation targets and calculates drift from targets.
"""

import pandas as pd
import numpy as np
import yaml
from typing import Dict, Tuple, Optional
from pathlib import Path


def load_glide_path_config(config_path: Optional[str] = None) -> Dict:
    """
    Load glide path configuration from YAML file.
    
    Args:
        config_path: Path to YAML file (default: config/glide_path.yaml)
        
    Returns:
        Dictionary with configuration
    """
    if config_path is None:
        base_path = Path(__file__).parent.parent
        config_path = base_path / "config" / "glide_path.yaml"
    
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    return config


def get_target_allocation(current_age: int, config: Optional[Dict] = None) -> Dict[str, float]:
    """
    Get target asset allocation for given age.
    
    Args:
        current_age: Current age of investor
        config: Glide path configuration (loaded if not provided)
        
    Returns:
        Dictionary with target percentages for each asset class
    """
    if config is None:
        config = load_glide_path_config()
    
    age_targets = config.get('age_targets', {})
    
    # Round to nearest 5-year bucket
    age_bucket = round(current_age / 5) * 5
    age_bucket = max(35, min(60, age_bucket))  # Clamp between 35 and 60
    
    age_key = f"age_{age_bucket}"
    
    if age_key in age_targets:
        return age_targets[age_key]
    
    # Calculate dynamically using formula if exact age not found
    formula = config.get('formula', {})
    min_equity = formula.get('minimum_equity', 30)
    
    equity = max(100 - current_age, min_equity)
    
    # Default gold and cash allocation based on age
    if current_age < 45:
        gold = 3
        cash = 2
    elif current_age < 55:
        gold = 5
        cash = 3
    else:
        gold = 7
        cash = 3
    
    debt = 100 - equity - gold - cash
    
    return {
        'equity': equity,
        'debt': max(debt, 0),
        'gold': gold,
        'cash': cash
    }


def calculate_drift(current_allocation: Dict[str, float],
                   target_allocation: Dict[str, float]) -> Dict[str, float]:
    """
    Calculate drift between current and target allocation.
    
    Args:
        current_allocation: Current percentage allocation by asset class
        target_allocation: Target percentage allocation by asset class
        
    Returns:
        Dictionary with drift values (current - target)
    """
    drift = {}
    
    all_keys = set(current_allocation.keys()) | set(target_allocation.keys())
    
    for key in all_keys:
        current = current_allocation.get(key, 0)
        target = target_allocation.get(key, 0)
        drift[key] = current - target
    
    return drift


def get_glide_path_projection(current_age: int, 
                             final_age: int = 60,
                             config: Optional[Dict] = None) -> pd.DataFrame:
    """
    Get year-by-year glide path projection.
    
    Args:
        current_age: Current age of investor
        final_age: Target retirement age
        config: Glide path configuration
        
    Returns:
        DataFrame with columns [age, equity, debt, gold, cash]
    """
    if config is None:
        config = load_glide_path_config()
    
    formula = config.get('formula', {})
    min_equity = formula.get('minimum_equity', 30)
    
    years = []
    
    for age in range(current_age, final_age + 1):
        target = get_target_allocation(age, config)
        row = {
            'age': age,
            'equity': target['equity'],
            'debt': target['debt'],
            'gold': target['gold'],
            'cash': target['cash']
        }
        years.append(row)
    
    return pd.DataFrame(years)


def check_rebalancing_needed(current_allocation: Dict[str, float],
                            target_allocation: Dict[str, float],
                            tolerance: float = 0.05) -> bool:
    """
    Check if portfolio rebalancing is needed based on drift tolerance.
    
    Args:
        current_allocation: Current percentage allocation
        target_allocation: Target percentage allocation
        tolerance: Maximum acceptable drift (default 5%)
        
    Returns:
        True if rebalancing needed, False otherwise
    """
    drift = calculate_drift(current_allocation, target_allocation)
    
    # Check if any asset class has drift exceeding tolerance
    for asset, drift_value in drift.items():
        if abs(drift_value) > tolerance * 100:  # Convert to percentage points
            return True
    
    return False


def get_rebalancing_urgency(current_allocation: Dict[str, float],
                           target_allocation: Dict[str, float],
                           config: Optional[Dict] = None) -> Dict:
    """
    Get detailed rebalancing urgency assessment.
    
    Args:
        current_allocation: Current allocation
        target_allocation: Target allocation
        config: Configuration for thresholds
        
    Returns:
        Dictionary with urgency level and details
    """
    if config is None:
        config = load_glide_path_config()
    
    rebalance_config = config.get('rebalancing', {})
    drift_tolerance = rebalance_config.get('drift_tolerance', 0.05) * 100
    max_drift = rebalance_config.get('max_drift_before_action', 0.10) * 100
    
    drift = calculate_drift(current_allocation, target_allocation)
    
    max_deviation = max(abs(d) for d in drift.values())
    
    # Count assets with significant drift
    assets_needing_rebalance = [
        asset for asset, d in drift.items() 
        if abs(d) > drift_tolerance
    ]
    
    # Determine urgency level
    if max_deviation > max_drift:
        urgency = "High"
        action = "Immediate"
    elif max_deviation > drift_tolerance:
        urgency = "Medium"
        action = "Planned"
    else:
        urgency = "Low"
        action = "None"
    
    return {
        'urgency': urgency,
        'action_required': action,
        'max_deviation': max_deviation,
        'assets_needing_rebalance': assets_needing_rebalance,
        'drift_details': drift,
        'drift_tolerance': drift_tolerance
    }


def map_scheme_to_asset_class(scheme_type: str, scheme_category: str, 
                              config: Optional[Dict] = None) -> str:
    """
    Map a scheme type to its asset class.
    
    Args:
        scheme_type: Type of scheme
        scheme_category: Category of scheme
        config: Configuration with asset class mappings
        
    Returns:
        Asset class string (equity, debt, gold, cash)
    """
    if config is None:
        config = load_glide_path_config()
    
    asset_classes = config.get('asset_classes', {})
    
    scheme_upper = f"{scheme_type} {scheme_category}".upper()
    
    for asset_class, keywords in asset_classes.items():
        for keyword in keywords:
            if keyword.upper() in scheme_upper:
                return asset_class
    
    # Default to equity for unknown types
    return 'equity'


def aggregate_allocation_by_asset_class(holdings_df: pd.DataFrame,
                                       config: Optional[Dict] = None) -> Dict[str, float]:
    """
    Aggregate holdings by asset class.
    
    Args:
        holdings_df: DataFrame with holdings including scheme_type and value
        config: Glide path configuration
        
    Returns:
        Dictionary with percentage allocation by asset class
    """
    if holdings_df is None or holdings_df.empty:
        return {'equity': 0, 'debt': 0, 'gold': 0, 'cash': 0}
    
    if config is None:
        config = load_glide_path_config()
    
    # Map each holding to asset class
    asset_class_values = {}
    total_value = 0
    
    for _, row in holdings_df.iterrows():
        scheme_type = row.get('scheme_type', '')
        scheme_category = row.get('scheme_category', '')
        value = row.get('current_value', 0)
        
        asset_class = map_scheme_to_asset_class(scheme_type, scheme_category, config)
        
        asset_class_values[asset_class] = asset_class_values.get(asset_class, 0) + value
        total_value += value
    
    if total_value == 0:
        return {'equity': 0, 'debt': 0, 'gold': 0, 'cash': 0}
    
    # Convert to percentages
    allocation = {}
    for asset_class in ['equity', 'debt', 'gold', 'cash']:
        allocation[asset_class] = (asset_class_values.get(asset_class, 0) / total_value) * 100
    
    return allocation


def get_lifecycle_fund_suggestion(current_age: int, 
                                  risk_tolerance: str = 'moderate') -> Dict:
    """
    Get lifecycle fund suggestion based on age and risk tolerance.
    
    Args:
        current_age: Current age
        risk_tolerance: 'conservative', 'moderate', 'aggressive'
        
    Returns:
        Dictionary with fund allocation suggestion
    """
    target = get_target_allocation(current_age)
    
    # Adjust based on risk tolerance
    if risk_tolerance == 'aggressive':
        target['equity'] = min(target['equity'] + 10, 80)
        target['debt'] = max(target['debt'] - 10, 10)
    elif risk_tolerance == 'conservative':
        target['equity'] = max(target['equity'] - 10, 20)
        target['debt'] = min(target['debt'] + 10, 70)
    
    # Recalculate to ensure sum is 100
    total = target['equity'] + target['debt'] + target['gold'] + target['cash']
    if total != 100:
        target['debt'] += (100 - total)  # Adjust debt to make up difference
    
    return target
