"""
CAS (Consolidated Account Statement) Parser
Supports both PDF (Karvy/CAMS) and CSV formats.
Extracts mutual fund holdings and transactions.
"""

import re
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import io
import csv

import pdfplumber
import pandas as pd
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ParsedHolding:
    """Represents a parsed holding from CAS."""
    isin: str
    scheme_name: str
    folio: str
    units: float
    current_nav: float
    current_value: float
    category: str = ""
    amc: str = ""
    purchase_value: float = 0.0
    purchase_date: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'isin': self.isin,
            'scheme_name': self.scheme_name,
            'folio': self.folio,
            'units': self.units,
            'current_nav': self.current_nav,
            'current_value': self.current_value,
            'category': self.category,
            'amc': self.amc,
            'purchase_value': self.purchase_value,
            'purchase_date': self.purchase_date
        }


@dataclass
class ParsedTransaction:
    """Represents a parsed transaction from CAS."""
    isin: str
    scheme_name: str
    folio: str
    date: str
    type: str  # PURCHASE, REDEMPTION, DIVIDEND, SIP, etc.
    units: float
    nav: float
    amount: float
    description: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'isin': self.isin,
            'scheme_name': self.scheme_name,
            'folio': self.folio,
            'date': self.date,
            'type': self.type,
            'units': self.units,
            'nav': self.nav,
            'amount': self.amount,
            'description': self.description
        }


class CategoryClassifier:
    """Classifies mutual fund schemes into categories."""
    
    def __init__(self, config_path: str = None):
        """Initialize with category rules from YAML config."""
        if config_path is None:
            base_dir = Path(__file__).parent.parent
            config_path = base_dir / 'config' / 'categories.yaml'
        
        self.rules = self._load_rules(config_path)
        self.default_category = self.rules.get('default_category', 'Equity Flexi Cap')
        self.amc_mapping = self.rules.get('amc_mapping', {})
    
    def _load_rules(self, config_path: Path) -> Dict:
        """Load classification rules from YAML file."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Could not load category config: {e}. Using defaults.")
            return {
                'categories': {},
                'default_category': 'Equity Flexi Cap',
                'amc_mapping': {}
            }
    
    def classify(self, scheme_name: str, isin: str = "") -> Tuple[str, str]:
        """
        Classify scheme into category and asset type.
        
        Returns:
            Tuple of (category, asset_type)
        """
        scheme_lower = scheme_name.lower()
        
        categories = self.rules.get('categories', {})
        
        for cat_key, cat_rules in categories.items():
            patterns = cat_rules.get('patterns', [])
            for pattern in patterns:
                if pattern.lower() in scheme_lower:
                    return cat_rules.get('category', cat_key), cat_rules.get('asset_type', 'Equity')
        
        # Try to infer from keywords if no match
        if any(x in scheme_lower for x in ['equity', 'growth', 'dividend']):
            if 'tax' in scheme_lower or 'elss' in scheme_lower or '80c' in scheme_lower:
                return 'ELSS', 'Equity'
            if 'large' in scheme_lower:
                return 'Equity Large Cap', 'Equity'
            if 'mid' in scheme_lower:
                return 'Equity Mid Cap', 'Equity'
            if 'small' in scheme_lower:
                return 'Equity Small Cap', 'Equity'
            return 'Equity Flexi Cap', 'Equity'
        
        if any(x in scheme_lower for x in ['liquid', 'cash', 'insta']):
            return 'Liquid', 'Debt'
        
        if any(x in scheme_lower for x in ['debt', 'gilt', 'bond']):
            return 'Debt Medium/Long Term', 'Debt'
        
        if any(x in scheme_lower for x in ['balanced', 'hybrid', 'allocation']):
            return 'Hybrid Balanced Advantage', 'Hybrid'
        
        return self.default_category, 'Equity'
    
    def extract_amc(self, scheme_name: str) -> str:
        """Extract AMC name from scheme name."""
        scheme_upper = scheme_name.upper()
        
        for prefix, amc_name in self.amc_mapping.items():
            if prefix.upper() in scheme_upper:
                return amc_name
        
        # Try to extract from beginning of scheme name
        words = scheme_name.split()
        if words:
            return words[0]
        
        return "Unknown"


class CASParser:
    """Parser for Consolidated Account Statements from Karvy/CAMS."""
    
    def __init__(self, config_path: str = None):
        """Initialize parser."""
        self.classifier = CategoryClassifier(config_path)
    
    def parse(self, file_path: str) -> Dict[str, Any]:
        """
        Parse a CAS file (PDF or CSV).
        
        Args:
            file_path: Path to CAS file
        
        Returns:
            Dictionary with 'holdings' and 'transactions' lists
        """
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        ext = path.suffix.lower()
        
        if ext == '.pdf':
            return self.parse_pdf(file_path)
        elif ext == '.csv':
            return self.parse_csv(file_path)
        else:
            raise ValueError(f"Unsupported file format: {ext}")
    
    def parse_pdf(self, pdf_path: str) -> Dict[str, Any]:
        """
        Parse PDF CAS statement.
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Dictionary with 'holdings' and 'transactions' lists
        """
        holdings = []
        transactions = []
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                all_text = ""
                for page in pdf.pages:
                    all_text += page.extract_text() + "\n"
                
                # Parse the extracted text
                parsed = self._parse_cas_text(all_text)
                holdings = parsed['holdings']
                transactions = parsed['transactions']
                
                # Also try to extract tables directly
                table_data = self._extract_tables(pdf)
                if table_data:
                    holdings.extend(table_data['holdings'])
                    transactions.extend(table_data['transactions'])
        
        except Exception as e:
            logger.error(f"Error parsing PDF: {e}")
            raise
        
        return {
            'holdings': holdings,
            'transactions': transactions,
            'source': pdf_path,
            'format': 'PDF'
        }
    
    def _extract_tables(self, pdf) -> Dict[str, List]:
        """Extract data from tables in PDF."""
        holdings = []
        transactions = []
        
        for page in pdf.pages:
            tables = page.extract_tables()
            for table in tables:
                if not table or len(table) < 2:
                    continue
                
                # Check if this looks like a holdings table
                header = [str(cell or '').lower() for cell in table[0]]
                
                if any(x in ' '.join(header) for x in ['scheme', 'folio', 'units', 'nav', 'value']):
                    # Holdings table
                    for row in table[1:]:
                        if len(row) >= 5:
                            holding = self._parse_holding_row(row)
                            if holding:
                                holdings.append(holding.to_dict())
                
                elif any(x in ' '.join(header) for x in ['date', 'transaction', 'amount', 'units']):
                    # Transactions table
                    for row in table[1:]:
                        if len(row) >= 4:
                            tx = self._parse_transaction_row(row)
                            if tx:
                                transactions.append(tx.to_dict())
        
        return {'holdings': holdings, 'transactions': transactions}
    
    def _parse_holding_row(self, row: List) -> Optional[ParsedHolding]:
        """Parse a single holding row from table."""
        try:
            # Try to identify columns by content
            scheme_name = ""
            isin = ""
            folio = ""
            units = 0.0
            nav = 0.0
            value = 0.0
            
            for cell in row:
                if not cell:
                    continue
                cell_str = str(cell).strip()
                
                # ISIN pattern
                if re.match(r'^IN[A-Z0-9]{10}$', cell_str.replace('-', '').replace(' ', '')):
                    isin = cell_str.replace('-', '').replace(' ', '')
                # Units pattern (numeric with decimals)
                elif re.match(r'^\d+\.?\d*$', cell_str.replace(',', '')):
                    num_val = float(cell_str.replace(',', ''))
                    if num_val > 100:  # Likely value or NAV
                        if nav == 0:
                            nav = num_val
                        else:
                            value = num_val
                    else:
                        units = num_val
                # Scheme name (contains alphanumeric, spaces)
                elif len(cell_str) > 10 and not cell_str.replace('.', '').replace(',', '').isdigit():
                    scheme_name = cell_str
                # Folio pattern (numeric/alphanumeric, typically 10+ chars)
                elif re.match(r'^[A-Z0-9/\-]+$', cell_str) and len(cell_str) > 5:
                    if not folio:
                        folio = cell_str
            
            if isin and scheme_name:
                category, asset_type = self.classifier.classify(scheme_name)
                amc = self.classifier.extract_amc(scheme_name)
                
                # If value not parsed, calculate
                if value == 0 and units > 0 and nav > 0:
                    value = units * nav
                
                return ParsedHolding(
                    isin=isin,
                    scheme_name=scheme_name,
                    folio=folio or "",
                    units=units,
                    current_nav=nav,
                    current_value=value,
                    category=category,
                    amc=amc
                )
        
        except Exception as e:
            logger.debug(f"Error parsing holding row: {e}")
        
        return None
    
    def _parse_transaction_row(self, row: List) -> Optional[ParsedTransaction]:
        """Parse a single transaction row from table."""
        try:
            date_str = ""
            tx_type = ""
            amount = 0.0
            units = 0.0
            nav = 0.0
            description = ""
            
            for cell in row:
                if not cell:
                    continue
                cell_str = str(cell).strip()
                
                # Date pattern
                if re.match(r'^\d{2}[/-]\d{2}[/-]\d{4}$', cell_str):
                    date_str = cell_str
                # Amount/Units pattern
                elif re.match(r'^-?[\d,]+\.?\d*$', cell_str):
                    num_val = float(cell_str.replace(',', ''))
                    if abs(num_val) > 1000:
                        amount = abs(num_val)
                    else:
                        units = abs(num_val)
                # Transaction type
                elif any(x in cell_str.upper() for x in ['PURCHASE', 'REDEMPTION', 'SIP', 'SWITCH', 'DIVIDEND']):
                    tx_type = cell_str.upper()
                    if 'SIP' in tx_type:
                        tx_type = 'SIP'
                    elif 'PURCHASE' in tx_type or 'BUY' in tx_type:
                        tx_type = 'PURCHASE'
                    elif 'REDEMPTION' in tx_type or 'SELL' in tx_type:
                        tx_type = 'REDEMPTION'
                else:
                    description = cell_str
            
            if date_str and amount > 0:
                # Parse date to standard format
                try:
                    for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%d/%m/%y', '%d-%m-%y']:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            date_str = dt.strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            continue
                except:
                    pass
                
                return ParsedTransaction(
                    isin="",  # Will be filled from context
                    scheme_name="",
                    folio="",
                    date=date_str,
                    type=tx_type or 'PURCHASE',
                    units=units,
                    nav=nav,
                    amount=amount,
                    description=description
                )
        
        except Exception as e:
            logger.debug(f"Error parsing transaction row: {e}")
        
        return None
    
    def _parse_cas_text(self, text: str) -> Dict[str, List]:
        """Parse CAS from extracted text."""
        holdings = []
        transactions = []
        
        # Find ISIN and scheme information
        isin_pattern = r'IN[A-Z0-9]{10}'
        isins = re.findall(isin_pattern, text.replace('-', '').replace(' ', ''))
        
        # Extract scheme blocks
        # Typical format: Scheme Name followed by ISIN, Folio, Units, NAV, Value
        lines = text.split('\n')
        current_amc = ""
        
        for i, line in enumerate(lines):
            # Check for AMC header
            if 'Mutual Fund' in line and ' folio' not in line.lower():
                current_amc = line.strip()
                continue
            
            # Look for ISIN in line
            line_isins = re.findall(isin_pattern, line.replace('-', '').replace(' ', ''))
            
            if line_isins:
                isin = line_isins[0]
                
                # Look for scheme name (usually previous line)
                scheme_name = ""
                if i > 0:
                    prev_line = lines[i-1].strip()
                    if len(prev_line) > 5 and not re.match(r'^\d', prev_line):
                        scheme_name = prev_line
                
                # Look for folio and units in following lines
                folio = ""
                units = 0.0
                nav = 0.0
                value = 0.0
                
                for j in range(i+1, min(i+5, len(lines))):
                    look_line = lines[j]
                    # Look for folio
                    folio_match = re.search(r'Folio\s*:?\s*([A-Z0-9/\-]+)', look_line, re.IGNORECASE)
                    if folio_match:
                        folio = folio_match.group(1)
                    
                    # Look for numeric values
                    numbers = re.findall(r'[\d,]+\.\d+', look_line.replace(',', ''))
                    if numbers:
                        nums = [float(n.replace(',', '')) for n in numbers]
                        # Heuristic: largest is value, medium is NAV, smallest is units
                        nums.sort(reverse=True)
                        if len(nums) >= 1:
                            value = nums[0]
                        if len(nums) >= 2:
                            nav = nums[1]
                        if len(nums) >= 3:
                            units = nums[2]
                
                if scheme_name:
                    category, asset_type = self.classifier.classify(scheme_name)
                    amc = self.classifier.extract_amc(scheme_name)
                    
                    holdings.append(ParsedHolding(
                        isin=isin,
                        scheme_name=scheme_name,
                        folio=folio,
                        units=units,
                        current_nav=nav,
                        current_value=value if value > 0 else units * nav,
                        category=category,
                        amc=amc
                    ).to_dict())
        
        return {'holdings': holdings, 'transactions': transactions}
    
    def parse_csv(self, csv_path: str) -> Dict[str, Any]:
        """
        Parse CSV CAS statement.
        
        Args:
            csv_path: Path to CSV file
        
        Returns:
            Dictionary with 'holdings' and 'transactions' lists
        """
        holdings = []
        transactions = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                # Try to detect format
                sample = f.read(4096)
                f.seek(0)
                
                # Determine dialect
                sniffer = csv.Sniffer()
                try:
                    dialect = sniffer.sniff(sample)
                except:
                    dialect = None
                
                reader = csv.DictReader(f, dialect=dialect) if dialect else csv.DictReader(f)
                
                for row in reader:
                    # Check if this is a holdings row or transaction row
                    if 'ISIN' in row or 'isin' in row:
                        holding = self._parse_csv_holding_row(row)
                        if holding:
                            holdings.append(holding.to_dict())
                    elif 'Date' in row or 'date' in row:
                        tx = self._parse_csv_transaction_row(row)
                        if tx:
                            transactions.append(tx.to_dict())
        
        except Exception as e:
            logger.error(f"Error parsing CSV: {e}")
            raise
        
        return {
            'holdings': holdings,
            'transactions': transactions,
            'source': csv_path,
            'format': 'CSV'
        }
    
    def _parse_csv_holding_row(self, row: Dict[str, str]) -> Optional[ParsedHolding]:
        """Parse a holding row from CSV."""
        try:
            isin = row.get('ISIN', row.get('isin', '')).strip()
            scheme_name = row.get('Scheme Name', row.get('scheme_name', row.get('Scheme', ''))).strip()
            folio = row.get('Folio', row.get('folio', row.get('Folio Number', ''))).strip()
            
            units_str = row.get('Units', row.get('units', row.get('Balance', '0')))
            units = float(str(units_str).replace(',', '')) if units_str else 0.0
            
            nav_str = row.get('NAV', row.get('nav', row.get('Current NAV', '0')))
            nav = float(str(nav_str).replace(',', '')) if nav_str else 0.0
            
            value_str = row.get('Value', row.get('value', row.get('Current Value', '0')))
            value = float(str(value_str).replace(',', '')) if value_str else 0.0
            
            if not value and units and nav:
                value = units * nav
            
            if isin and scheme_name:
                category, asset_type = self.classifier.classify(scheme_name)
                amc = self.classifier.extract_amc(scheme_name)
                
                return ParsedHolding(
                    isin=isin,
                    scheme_name=scheme_name,
                    folio=folio,
                    units=units,
                    current_nav=nav,
                    current_value=value,
                    category=category,
                    amc=amc
                )
        
        except Exception as e:
            logger.debug(f"Error parsing CSV holding row: {e}")
        
        return None
    
    def _parse_csv_transaction_row(self, row: Dict[str, str]) -> Optional[ParsedTransaction]:
        """Parse a transaction row from CSV."""
        try:
            date_str = row.get('Date', row.get('date', '')).strip()
            scheme_name = row.get('Scheme', row.get('scheme_name', '')).strip()
            isin = row.get('ISIN', row.get('isin', '')).strip()
            folio = row.get('Folio', row.get('folio', '')).strip()
            
            tx_type = row.get('Transaction Type', row.get('type', 'PURCHASE')).strip().upper()
            if 'SIP' in tx_type:
                tx_type = 'SIP'
            
            amount_str = row.get('Amount', row.get('amount', '0'))
            amount = float(str(amount_str).replace(',', '')) if amount_str else 0.0
            
            units_str = row.get('Units', row.get('units', '0'))
            units = float(str(units_str).replace(',', '')) if units_str else 0.0
            
            nav_str = row.get('NAV', row.get('nav', '0'))
            nav = float(str(nav_str).replace(',', '')) if nav_str else 0.0
            
            if date_str and amount > 0:
                # Convert date format
                try:
                    for fmt in ['%d/%m/%Y', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%y']:
                        try:
                            dt = datetime.strptime(date_str, fmt)
                            date_str = dt.strftime('%Y-%m-%d')
                            break
                        except ValueError:
                            continue
                except:
                    pass
                
                return ParsedTransaction(
                    isin=isin,
                    scheme_name=scheme_name,
                    folio=folio,
                    date=date_str,
                    type=tx_type,
                    units=units,
                    nav=nav,
                    amount=amount
                )
        
        except Exception as e:
            logger.debug(f"Error parsing CSV transaction row: {e}")
        
        return None
    
    def parse_to_dataframe(self, file_path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Parse CAS and return as DataFrames.
        
        Returns:
            Tuple of (holdings_df, transactions_df)
        """
        result = self.parse(file_path)
        
        holdings_df = pd.DataFrame(result['holdings'])
        transactions_df = pd.DataFrame(result['transactions'])
        
        return holdings_df, transactions_df


def parse_cas(file_path: str, config_path: str = None) -> Dict[str, Any]:
    """
    Convenience function to parse CAS file.
    
    Args:
        file_path: Path to CAS file
        config_path: Optional path to category config
    
    Returns:
        Dictionary with parsed holdings and transactions
    """
    parser = CASParser(config_path)
    return parser.parse(file_path)


if __name__ == "__main__":
    # Test the parser with a sample
    print("Testing CAS Parser...")
    
    parser = CASParser()
    
    # Test classification
    test_schemes = [
        "SBI Blue Chip Fund - Growth",
        "HDFC TaxSaver Fund - Growth",
        "ICICI Prudential Liquid Fund",
        "Axis Long Term Equity Fund",
        "Kotak Small Cap Fund",
        "Nippon India Balanced Advantage Fund"
    ]
    
    print("\nScheme Classification Test:")
    for scheme in test_schemes:
        category, asset_type = parser.classifier.classify(scheme)
        amc = parser.classifier.extract_amc(scheme)
        print(f"  {scheme}")
        print(f"    -> Category: {category}, Asset: {asset_type}, AMC: {amc}")
