# Portfolio Analytics Tool - Complete User Guide

**Version:** 1.0  
**Built for:** Ashish Prakash  
**Last Updated:** April 2026

---

## Table of Contents

1. [Quick Start (5 Minutes)](#quick-start)
2. [What This Tool Does](#what-this-tool-does)
3. [Installation & Setup](#installation--setup)
4. [Uploading Your Data](#uploading-your-data)
5. [Understanding the Dashboard](#understanding-the-dashboard)
6. [Interpreting Alerts & Recommendations](#interpreting-alerts)
7. [Advanced Features](#advanced-features)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## 1. Quick Start (5 Minutes) <a name="quick-start"></a>

### Step 1: Install Dependencies
```bash
cd ~/workspace/portfolio-analytics
pip install -r requirements.txt
```

### Step 2: Initialize Database
```bash
python3 -c "from database import PortfolioDatabase; db = PortfolioDatabase(); db.initialize_database()"
```

### Step 3: Run the App
```bash
streamlit run app/main.py
```

### Step 4: Upload Your CAS Statement
1. Open browser at `http://localhost:8501`
2. Click "Browse files" in the sidebar
3. Select your CAMS/Karvy CAS statement (PDF or CSV)
4. Click "Update NAV Data" to fetch latest prices
5. View your portfolio!

---

## 2. What This Tool Does <a name="what-this-tool-does"></a>

This is a **personal portfolio analytics dashboard** designed for treasury professionals who want institutional-grade analysis of their personal investments.

### Supported Asset Classes

| Asset Class | Data Source | What You Get |
|-------------|-------------|--------------|
| **Mutual Funds** | CAS Statement (CAMS/Karvy) | NAV, XIRR, Allocation, Sector Exposure |
| **Fixed Deposits** | Manual CSV Upload | Maturity tracking, Interest calculation |
| **PPF** | Manual CSV Upload | Lock-in tracking, Withdrawal eligibility |
| **NPS** | Manual CSV Upload | Tier-1/Tier-2 split, Allocation analysis |
| **Cash/ Liquid** | Manual Entry | Liquidity ratio, Drag analysis |

### Key Features

**Phase 1 - Core Analytics**
- Automatic CAS parsing (PDF/CSV)
- Real-time NAV fetch from AMFI
- XIRR calculation per scheme and portfolio
- Asset allocation breakdown

**Phase 2 - Integration & Monitoring**
- FD/PPF/NPS manual upload
- Liquidity calendar (maturities, lock-ins)
- Concentration alerts
- Cash drag warnings

**Phase 3 - Risk Intelligence**
- Age-based glide path (35 → 60% equity, reducing 1%/year)
- Risk score (0-100) with component breakdown
- Sharpe ratio, Max Drawdown, Rolling returns
- Tax-loss harvesting suggestions
- Rebalancing calculator with tax optimization

---

## 3. Installation & Setup <a name="installation--setup"></a>

### Prerequisites

- Python 3.10 or higher
- pip package manager
- 500 MB free disk space
- Internet connection (for NAV updates)

### Step-by-Step Installation

**1. Navigate to Project Directory**
```bash
cd ~/workspace/portfolio-analytics
```

**2. Create Virtual Environment (Recommended)**
```bash
python3 -m venv venv
source venv/bin/activate  # On Linux/Mac
# OR
venv\Scripts\activate  # On Windows
```

**3. Install Dependencies**
```bash
pip install -r requirements.txt
```

This installs:
- streamlit (web dashboard)
- pandas, numpy (data processing)
- plotly (visualizations)
- pdfplumber, PyPDF2 (CAS parsing)
- pyyaml (configuration)
- requests (API calls)

**4. Initialize Database**
```bash
python3 -c "from database import PortfolioDatabase; db = PortfolioDatabase(); db.initialize_database(); print('Database ready!')"
```

**5. Test Installation**
```bash
python3 -c "import app.main; print('All imports working!')"
```

### File Structure

```
portfolio-analytics/
├── app/
│   ├── main.py              ← Start here (Streamlit app)
│   ├── dashboard.py         ← Alternative dashboard
│   └── components/          ← UI components
├── parsers/                 ← CAS and CSV parsers
├── api/                     ← AMFI data provider
├── utils/                   ← XIRR, Risk metrics, Tax
├── config/                  ← YAML configuration files
├── templates/               ← CSV templates for manual upload
├── data/                    ← SQLite databases
├── docs/                    ← This documentation
└── tests/                   ← Unit tests
```

---

## 4. Uploading Your Data <a name="uploading-your-data"></a>

### 4.1 Mutual Funds - CAS Statement (Easiest)

**What is a CAS Statement?**
Consolidated Account Statement from CAMS or Karvy. Contains ALL your mutual fund holdings across fund houses.

**How to Get It:**
1. **CAMS:** https://www.camsonline.com → CAS Statement → Enter PAN, email
2. **Karvy:** https://www.karvykra.com → CAS Statement
3. **NSDL:** https://nsdlcas.nsdl.com → Consolidated Account Statement

**Supported Formats:**
- PDF (most common) - Tool extracts automatically
- CSV (if available) - Direct import

**Upload Process:**
1. Run app: `streamlit run app/main.py`
2. In sidebar, click "📁 Upload CAS Statement"
3. Select your PDF/CSV file
4. Wait for processing (10-30 seconds for PDF)
5. Click "🔄 Update NAV Data" to fetch current prices

**What Gets Extracted:**
- ISIN codes
- Scheme names
- Folio numbers
- Units held
- Current value (from statement)
- Category (Equity/Debt/Hybrid/ELSS - auto-detected)

**Sample CAS Data Extracted:**
```
Scheme: SBI Bluechip Fund - Growth
ISIN: INF200K01SQ9
Folio: 12345678
Units: 1,500.500
Current Value: ₹45,750.00
Category: Equity Large Cap
```

### 4.2 Fixed Deposits (FD) - CSV Upload

**Download Template:**
```bash
cp templates/fd_template.csv ~/Downloads/fd_data.csv
```

**Template Columns:**

| Column | Description | Example |
|--------|-------------|---------|
| institution | Bank/NBFC name | HDFC Bank |
| account_number | FD receipt number | FD123456789 |
| principal | Initial deposit | 100000 |
| interest_rate | Annual rate (%) | 7.5 |
| start_date | Opening date (YYYY-MM-DD) | 2024-01-15 |
| maturity_date | Maturity date (YYYY-MM-DD) | 2026-01-15 |
| interest_type | simple/compound | compound |
| compounding_frequency | yearly/quarterly/monthly | quarterly |
| current_value | Leave blank (calculated) | |
| notes | Optional remarks | Senior citizen rate |

**Example Row:**
```csv
institution,account_number,principal,interest_rate,start_date,maturity_date,interest_type,compounding_frequency,current_value,notes
HDFC Bank,FD123456789,100000,7.5,2024-01-15,2026-01-15,compound,quarterly,,Senior citizen rate
SBI,FD987654321,50000,7.0,2024-03-10,2025-03-10,simple,,,Renewable
```

**Upload Process:**
1. Go to "📊 Upload Manual Assets" tab
2. Select "Fixed Deposits"
3. Upload your CSV
4. Preview and validate
5. Save to database

**Automatic Calculations:**
- Current value using A = P(1 + r/n)^(nt)
- Days to maturity
- Interest accrued till date

### 4.3 PPF - CSV Upload

**Download Template:**
```bash
cp templates/ppf_template.csv ~/Downloads/ppf_data.csv
```

**Template Columns:**

| Column | Description | Example |
|--------|-------------|---------|
| account_number | PPF account number | PPF123456 |
| financial_year | FY of deposit | 2023-24 |
| deposit_date | Date (YYYY-MM-DD) | 2023-04-05 |
| amount | Deposit amount | 150000 |
| interest_rate | Govt declared rate | 7.1 |
| current_balance | Running balance | 500000 |
| maturity_date | 15-year maturity | 2038-03-31 |
| lock_in_end | Lock-in end date | 2033-03-31 |
| notes | Optional | Partial withdrawal eligible |

**PPF Rules Integrated:**
- 15-year lock-in from first deposit
- Partial withdrawal from 7th year
- Loan facility from 3rd to 6th year
- Interest compounded annually (govt rate)

**Important:**
- PPF interest rates change quarterly (tracked since 2016)
- Tool uses historical rates for accurate calculation
- Current rate (FY 2025-26): 7.1%

### 4.4 NPS - CSV Upload

**Download Template:**
```bash
cp templates/nps_template.csv ~/Downloads/nps_data.csv
```

**Template Columns:**

| Column | Description | Example |
|--------|-------------|---------|
| pran | Permanent Retirement Account Number | 123456789012 |
| tier | Tier 1 or 2 | 1 |
| allocation_type | equity/corporate_bond/govt_securities/alternate | equity |
| allocation_percentage | % allocated | 50 |
| current_value | Current value in this bucket | 250000 |
| contributions_ytd | Contributions this year | 50000 |
| returns_since_inception | Returns % | 12.5 |
| notes | Optional | Active choice |

**NPS Allocation Types:**
- **Equity (E):** Max 75% (age < 50), 50% (age 50-60)
- **Corporate Bonds (C):** Fixed income from corporate debt
- **Government Securities (G):** Central/State govt bonds
- **Alternate Assets (A):** Max 5%, includes REITs, InvITs

**Upload Tips:**
1. Get allocation split from NPS CRA (Karvy/NSDL)
2. Create separate rows for each bucket
3. Example: If Tier-1 is 50% E, 30% C, 20% G → 3 rows

### 4.5 Direct Equity (Optional)

While primarily designed for MF, you can add direct stocks:

**Method 1:** Add to FD template with custom notes
**Method 2:** Extend templates/equity_template.csv (create if needed)

**Recommended:** Use broker API (Zerodha Kite, Upstox) for automatic sync - requires additional setup.

---

## 5. Understanding the Dashboard <a name="understanding-the-dashboard"></a>

### Tab 1: Overview (Landing Page)

**Top Metrics Bar:**
```
┌─────────────────────────────────────────────────────────────────┐
│  TOTAL AUM          XIRR (1Y)        XIRR (3Y)      RISK SCORE  │
│  ₹ 25,45,678        18.5%            14.2%          42/100      │
│  Last updated: 08 Apr 2025, 18:30 IST                           │
└─────────────────────────────────────────────────────────────────┘
```

**Asset Allocation Pie Chart:**
- Hover to see values
- Click legend to filter
- Shows: Equity, Debt, Liquid, ELSS, Gold, Cash

**Quick Stats:**
- Number of schemes
- Top performer (by XIRR)
- Worst performer
- Cash drag %

### Tab 2: Holdings (Detailed View)

**Sortable Table Columns:**
| Column | What It Means |
|--------|---------------|
| Scheme Name | Fund name + Category badge |
| AMC | Fund house |
| Units | Current holding |
| Current NAV | Latest from AMFI |
| Current Value | Units × NAV |
| XIRR | True annualized return |
| % of Portfolio | Concentration indicator |
| Actions | Edit/Delete |

**Filters:**
- Asset class (Equity/Debt/Hybrid)
- AMC (SBI, HDFC, Axis, etc.)
- Category (Large Cap, ELSS, Liquid)
- Performance (Top 10 / Bottom 10)

**Color Coding:**
- 🟢 XIRR > 15%: Excellent
- 🟡 XIRR 8-15%: Good
- 🔴 XIRR < 8%: Review needed

### Tab 3: Allocation Analysis

**Drill-Down Charts:**

1. **Equity Breakdown**
   - Large Cap / Mid Cap / Small Cap / Flexi Cap
   - Value vs Growth (if detectable)

2. **Debt Breakdown**
   - Duration buckets (0-1Y, 1-3Y, 3-5Y, 5Y+)
   - Credit quality (AAA, AA, A)
   - Issuer type (G-Sec, PSU, Corporate)

3. **Tax Status**
   - ELSS (locked-in vs free)
   - Equity LTCG vs STCG
   - Debt taxation buckets

**Benchmark Comparison:**
- Your equity returns vs Nifty 50
- Your debt returns vs Crisil Composite Bond Index

### Tab 4: Calendar (Liquidity Events)

**Upcoming Events Table:**

| Date | Event Type | Asset | Details | Action Needed |
|------|------------|-------|---------|---------------|
| 15 Apr | FD Maturity | HDFC FD | ₹1,00,000 | Decide: Renew/Withdraw |
| 22 May | ELSS Unlock | Axis LT Equity | 500 units | Can sell if needed |
| 01 Jun | SIP Due | SBI Bluechip | ₹5,000 | Ensure balance |

**Filter by:**
- Next 30/60/90 days
- Asset type
- Event type (Maturity/Unlock/SIP)

### Tab 5: Alerts (Red/Yellow/Green)

**Alert Cards:**

🔴 **CRITICAL (Red)** - Immediate Action Required
- "HDFC Top 100 is 18% of portfolio (limit: 15%)"
- "Cash drag at 15% (limit: 10%) - ₹2.5L uninvested"
- "NPS equity at 35% vs target 50%"

🟡 **WARNING (Yellow)** - Monitor/Optimize
- "ELSS lock-in ends in 2 months - plan exit"
- "Debt duration 4.2Y vs target 3Y - rate risk"
- "No international equity exposure"

🟢 **INFO (Green)** - Good Practices
- "Diversified across 12 AMCs"
- "Tax-loss harvesting opportunity: ₹12,500 unrealized loss"

**Each Card Shows:**
- Current state
- Recommended action
- Expected impact
- One-click fix (where applicable)

### Tab 6: Risk Dashboard

**Risk Score Gauge:**
```
Risk Score: 42/100 (Moderate)
├─ Volatility: 35% contribution
├─ Concentration: 30% contribution
├─ Liquidity: 20% contribution
└─ Drawdown: 15% contribution
```

**Key Metrics:**
| Metric | Your Value | Benchmark | Interpretation |
|--------|------------|-----------|----------------|
| Portfolio Volatility | 12.5% | Market 15% | Lower is better |
| Sharpe Ratio | 1.2 | Nifty 0.9 | Risk-adjusted return |
| Max Drawdown | -18% | Nifty -24% | Resilience |
| 1Y Rolling Return | 18.5% | Nifty 22% | Underperforming |
| 3Y Rolling Return | 14.2% | Nifty 12% | Outperforming |

**Charts:**
1. **Drawdown Chart:** Peak-to-trough over time
2. **Rolling Returns:** 1Y/3Y/5Y rolling windows
3. **Benchmark Deviation:** Your alpha vs Nifty

### Tab 7: Glide Path

**Current vs Target Allocation:**

```
At Age 35:
┌──────────┬─────────┬─────────┬────────┐
│ Asset    │ Current │ Target  │ Drift  │
├──────────┼─────────┼─────────┼────────┤
│ Equity   │ 72%  🔴 │ 60%     │ +12%   │
│ Debt     │ 23%  🟢 │ 35%     │ -12%   │
│ Gold     │ 2%   🟡 │ 3%      │ -1%    │
│ Cash     │ 3%   🟢 │ 2%      │ +1%    │
└──────────┴─────────┴─────────┴────────┘
```

**Color Coding:**
- 🟢 Within ±5% of target
- 🟡 5-10% deviation
- 🔴 >10% deviation (rebalancing needed)

**Glide Path Projection:**
```
Age 35: Equity 60% → Debt 35% → Gold 3%
Age 40: Equity 55% → Debt 40% → Gold 3%
Age 45: Equity 50% → Debt 42% → Gold 5%
Age 50: Equity 45% → Debt 47% → Gold 5%
Age 55: Equity 40% → Debt 50% → Gold 7%
Age 60: Equity 35% → Debt 55% → Gold 7%
```

**Rebalancing Calculator:**
- Current portfolio value
- Target allocation
- Suggested trades (Sell X, Buy Y)
- Tax-optimized sequencing (sell LTCG before STCG)
- Transaction cost estimate

### Tab 8: Recommendations (Priority Queue)

**Ranked Action List:**

1. **🔴 REDUCE HDFC TOP 100**
   - Current: 18% (₹4.5L)
   - Target: 15% (₹3.75L)
   - Action: Sell ₹75,000 worth
   - Tax Impact: ₹0 (LTCG eligible)
   - Alternative: Switch to Nifty 50 Index (lower expense)

2. **🟡 DEPLOY CASH DRAG**
   - Current: 15% uninvested (₹2.5L)
   - Target: 5%
   - Action: Invest ₹2L in Liquid Bees / Arbitrage Fund
   - Expected Return: 6% vs 3% in savings
   - Annual Gain: ₹6,000

3. **🟢 TAX LOSS HARVESTING**
   - Unrealized Loss: ₹12,500 in Nippon India Small Cap
   - Action: Sell → Buy similar fund (SBI Small Cap)
   - Tax Savings: ₹2,500 (20% STCG offset)
   - Holding Period: Reset to 0 days

**Each Recommendation Shows:**
- Problem statement
- Current vs ideal state
- Step-by-step fix
- Quantified impact (₹ value)
- Risk/constraints

---

## 6. Interpreting Alerts & Recommendations <a name="interpreting-alerts"></a>

### Understanding Risk Score (0-100)

**Score Breakdown:**
- **0-25:** Conservative (Low risk, potentially lower returns)
- **26-50:** Moderate (Balanced, appropriate for 30s-40s)
- **51-75:** Aggressive (High growth potential, higher volatility)
- **76-100:** Speculative (Very high risk, need monitoring)

**Component Weights:**
- Volatility (35%): How much portfolio swings
- Concentration (30%): Single points of failure
- Liquidity (20%): Ability to access cash when needed
- Drawdown (15%): Worst-case historical loss

**How to Reduce Risk Score:**
1. Add more schemes (reduce concentration)
2. Include debt/liquid (reduce volatility)
3. Build emergency fund (improve liquidity)
4. Avoid sector/thematic funds (reduce drawdown risk)

### Understanding XIRR vs CAGR

**CAGR** (Compound Annual Growth Rate):
- Simple formula: (Ending Value / Beginning Value)^(1/n) - 1
- Assumes single investment at start
- **Misleading for SIPs**

**XIRR** (Extended Internal Rate of Return):
- Accounts for exact dates of every cash flow
- Handles SIPs, redemptions, dividends
- **True annualized return**

**Example:**
- SIP ₹10,000/month for 12 months
- Total invested: ₹1.2L
- Current value: ₹1.35L
- CAGR shows 12.5% (wrong - doesn't account for time-weighted investments)
- XIRR shows 23.4% (correct - each SIP had different duration)

**Always use XIRR for portfolio evaluation.**

### Understanding Glide Path

**Why It Matters:**
At 35, you can afford 60% equity because:
- 25+ years to retirement
- Time to recover from market crashes
- Income likely increasing

At 55, you need 40% equity because:
- 5-10 years to retirement
- Can't afford 2008-style 50% drawdown
- Need stability as you approach corpus target

**Automatic Adjustments:**
Tool reduces equity target by 1% per year after 40.
You can override in `config/glide_path.yaml` if your situation differs.

### Understanding Tax-Loss Harvesting

**Concept:**
Sell losing investments → Book capital loss → Offset gains → Rebuy similar asset

**Rules:**
- Equity: Can't buy same/substantially identical security within 30 days (wash sale concept not formal in India, but advised)
- Debt: No such restriction
- Must file ITR to claim loss carry-forward

**Example Workflow:**
1. Tool flags: "Nippon Small Cap has ₹12,500 unrealized loss"
2. You sell ₹50,000 worth of Nippon Small Cap
3. Buy ₹50,000 of SBI Small Cap (similar, not identical)
4. Book ₹12,500 loss in this FY
5. Offset against ₹20,000 STCG from other sale
6. Tax saved: ₹2,500 (20% of ₹12,500)

**Caution:**
- Reset holding period to 0
- STCG if sold within 1 year
- LTCG after 1 year

---

## 7. Advanced Features <a name="advanced-features"></a>

### Custom Configuration

**Edit `config/categories.yaml`:**
Add your own scheme classification rules:
```yaml
custom_category:
  name: "My Special Funds"
  patterns:
    - "SBI.*Special.*Situations"
    - "Axis.*Focused.*25"
  asset_class: "equity"
  risk_level: "high"
```

**Edit `config/limits.yaml`:**
Adjust alert thresholds:
```yaml
concentration_limit: 0.15  # Change to 0.20 for 20%
cash_limit: 0.10           # Change to 0.15 for 15%
top3_limit: 0.50           # Top 3 schemes max 50%
```

**Edit `config/glide_path.yaml`:**
Custom age-based allocation:
```yaml
glide_path:
  custom:
    age_35:
      equity: 70    # More aggressive than default
      debt: 25
      gold: 3
      cash: 2
```

### Database Queries (For Power Users)

```python
from database import PortfolioDatabase
db = PortfolioDatabase()

# Custom SQL
conn = db.get_connection()

# Top 5 holdings by value
top5 = conn.execute("""
    SELECT scheme_name, current_value 
    FROM holdings 
    WHERE asset_type='MF' 
    ORDER BY current_value DESC 
    LIMIT 5
""").fetchall()

# Average XIRR by category
avg_xirr = conn.execute("""
    SELECT category, AVG(xirr) as avg_return
    FROM holdings
    WHERE asset_type='MF'
    GROUP BY category
""").fetchall()

# Monthly investment pattern
monthly = conn.execute("""
    SELECT strftime('%Y-%m', date) as month, SUM(amount) as investment
    FROM transactions
    WHERE type='PURCHASE'
    GROUP BY month
    ORDER BY month DESC
""").fetchall()
```

### API Integration (Developers)

**Add New Data Source:**
```python
from api.nav_provider import NavProvider

class CustomProvider(NavProvider):
    def get_nav(self, isin, date=None):
        # Your API logic
        return nav_value
    
    def get_historical_nav(self, isin, from_date, to_date):
        # Your historical API logic
        return nav_dataframe
```

**Switch Provider:**
```python
from api.amfi_provider import AmfiProvider
from api.custom_provider import CustomProvider

# In app/main.py, change:
nav_provider = CustomProvider()  # Instead of AmfiProvider()
```

### Exporting Data

**Full Portfolio Backup:**
```bash
# SQLite backup
cp data/portfolio.db ~/backups/portfolio_$(date +%Y%m%d).db

# CSV export (available in UI)
# Holdings → Download CSV button
```

**Excel Integration:**
```python
# Export to Excel with multiple sheets
import pandas as pd

with pd.ExcelWriter('portfolio_report.xlsx') as writer:
    holdings_df.to_excel(writer, sheet_name='Holdings')
    transactions_df.to_excel(writer, sheet_name='Transactions')
    alerts_df.to_excel(writer, sheet_name='Alerts')
```

---

## 8. Troubleshooting <a name="troubleshooting"></a>

### Common Issues

**1. CAS Parser Not Working**

**Symptom:** "No holdings found in CAS file"

**Solutions:**
- Check if CAS is password-protected (remove password first)
- Verify file format (PDF should be text-based, not scanned image)
- Try CSV version of CAS if available
- Check PDF text extraction: `pdfplumber.open('cas.pdf').pages[0].extract_text()`

**2. NAV Not Updating**

**Symptom:** "NAV update failed" or old prices showing

**Solutions:**
- Check internet connection
- AMFI API is down (rare) - wait and retry
- Verify ISIN codes in database match AMFI records
- Manual override: Edit holdings table directly

**3. XIRR Calculation Shows Error**

**Symptom:** "XIRR calculation failed" or "No solution found"

**Causes:**
- All cashflows positive (no redemption/sale) - XIRR undefined
- All cashflows negative (no current value) - XIRR undefined
- Too few transactions

**Fix:**
- Add current value as negative cashflow (auto-handled by tool)
- Check transaction dates are in correct format

**4. Import Errors**

**Symptom:** `ModuleNotFoundError: No module named 'xyz'`

**Fix:**
```bash
pip install -r requirements.txt
# Or specific package:
pip install streamlit pandas numpy plotly pdfplumber PyPDF2 pyyaml requests
```

**5. Database Locked**

**Symptom:** "sqlite3.OperationalError: database is locked"

**Fix:**
- Close other apps using the database
- Restart Streamlit: Ctrl+C, then `streamlit run app/main.py`
- Delete `.db-journal` files if present

**6. ISIN Not Found**

**Symptom:** "Unknown scheme" or missing NAV

**Fix:**
- Add ISIN to `data/isin_master.db` manually
- Or use tool's "Add Manual Holding" feature
- Update ISIN master: Run `python3 data/populate_isin_master.py`

---

## 9. FAQ <a name="faq"></a>

**Q: Is my data secure?**
A: Yes. All data stored locally in SQLite database on your machine. No data sent to any server except NAV fetches from AMFI's public API.

**Q: Can I use this for my family members?**
A: Yes. Create separate database files:
```python
db = PortfolioDatabase('data/wife_portfolio.db')
```

**Q: How often should I update NAV?**
A: Once daily is sufficient. Mutual fund NAVs update once per day (evening).

**Q: Can I track international investments?**
A: Partial support. Add to manual CSV with USD values, but currency conversion not automatic.

**Q: What about real estate, gold jewelry?**
A: Add to FD template as "Physical Assets" with approximate values. Not integrated into risk calculations yet.

**Q: Can I import from Kuvera/ETMONEY/Groww?**
A: Export CSV from those apps, then map columns to our templates. Full API integration not available (requires paid partnerships).

**Q: How accurate is the XIRR?**
A: Uses Newton-Raphson method with fallback bisection. Accurate to 0.001%. Matches Excel's XIRR function.

**Q: Why is my XIRR negative even though absolute return is positive?**
A: XIRR accounts for time. If you invested recently and market dipped, time-weighted return can be negative even if absolute loss is small.

**Q: Can I automate this? Run daily reports?**
A: Yes. Create a cron job:
```bash
# Edit crontab
crontab -e
# Add line for daily at 6 PM:
0 18 * * * cd ~/workspace/portfolio-analytics && python3 -c "from app.main import generate_report; generate_report()"
```

**Q: Will this work on Windows?**
A: Yes, but paths need backslashes. Better to use WSL (Windows Subsystem for Linux) for full compatibility.

**Q: How do I backup my data?**
A: Copy `data/portfolio.db` file regularly. Or use tool's built-in export to CSV.

**Q: Can I contribute/modify the code?**
A: Absolutely! It's your personal project. Edit any file, restart Streamlit to see changes.

---

## Support & Feedback

For issues, check:
1. This documentation (Ctrl+F to search)
2. `tests/` folder for example usage
3. Code comments in source files

To add features:
1. Edit relevant files in `app/`, `utils/`, `parsers/`
2. Restart Streamlit
3. Test changes

---

**Built with ❤️ for treasury professionals who want institutional-grade personal finance tools.**

*Remember: This tool provides analysis, not investment advice. Always consult your financial advisor before making investment decisions.*
