# Portfolio Analytics Tool

**Personal Investment Dashboard for Indian Investors**

Built for treasury professionals who want institutional-grade analysis of their personal portfolios.

---

## 🚀 Quick Start (5 Minutes)

```bash
# 1. Navigate to project
cd ~/workspace/portfolio-analytics

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initialize database
python3 setup.py

# 4. Launch dashboard
streamlit run app.py
```

Then open `http://localhost:8501` in your browser.

---

## 📊 What You Get

### Phase 1: Core Analytics ✅
- **CAS Statement Parser** - Auto-extract holdings from CAMS/Karvy PDFs
- **Real-time NAV** - Fetch latest prices from AMFI India
- **XIRR Calculation** - True annualized returns (not misleading CAGR)
- **Asset Allocation** - Equity/Debt/Liquid/ELSS breakdown

### Phase 2: Integration & Monitoring ✅
- **FD/PPF/NPS Tracking** - CSV upload with auto-calculated values
- **Liquidity Calendar** - Maturity dates, ELSS unlocks, SIP schedules
- **Concentration Alerts** - "Top 3 schemes = 60% of portfolio"
- **Cash Drag Warnings** - Uninvested money alerts

### Phase 3: Risk Intelligence ✅
- **Age-Based Glide Path** - Auto-adjusting allocation (35 → 60% equity, -1%/year)
- **Risk Score** - 0-100 score with component breakdown
- **Sharpe Ratio & Drawdown** - Risk-adjusted return analysis
- **Tax-Loss Harvesting** - Automated loss harvesting suggestions
- **Rebalancing Calculator** - Tax-optimized trade suggestions

---

## 📁 Project Structure

```
portfolio-analytics/
├── app.py                 ← Start here (unified entry point)
├── setup.py               ← One-time setup script
├── requirements.txt       ← Python dependencies
│
├── app/
│   ├── main.py            ← Streamlit dashboard
│   ├── dashboard.py       ← Alternative view
│   └── components/        ← Reusable UI components
│       ├── alerts.py
│       ├── calendar.py
│       ├── glide_path_view.py
│       ├── manual_uploader.py
│       ├── recommendations.py
│       └── risk_dashboard.py
│
├── api/
│   ├── nav_provider.py   ← Abstract NAV interface
│   └── amfi_provider.py   ← AMFI India integration
│
├── parsers/
│   ├── cas_parser.py      ← PDF/CSV CAS parsing
│   └── manual_assets.py   ← FD/PPF/NPS parsers
│
├── utils/
│   ├── xirr.py           ← XIRR calculation engine
│   ├── database.py       ← SQLite wrapper
│   ├── risk_metrics.py   ← Volatility, Sharpe, Drawdown
│   ├── glide_path.py     ← Age-based allocation logic
│   ├── rebalancer.py     ← Rebalancing calculator
│   └── tax_tracker.py    ← Tax optimization engine
│
├── config/
│   ├── categories.yaml    ← Scheme classification rules
│   ├── limits.yaml        ← Alert thresholds
│   └── glide_path.yaml    ← Age-based targets
│
├── templates/             ← CSV templates for manual upload
│   ├── fd_template.csv
│   ├── ppf_template.csv
│   └── nps_template.csv
│
├── data/                  ← SQLite databases (auto-created)
│   ├── portfolio.db
│   └── isin_master.db
│
├── docs/
│   └── USER_GUIDE.md      ← Complete documentation
│
└── tests/                 ← Unit tests
    ├── test_manual_assets.py
    ├── test_alerts.py
    ├── test_calendar.py
    └── test_phase3.py
```

---

## 🎯 Features by Tab

| Tab | Features |
|-----|----------|
| **Overview** | Total AUM, XIRR (1Y/3Y), Risk Score, Asset Allocation Pie |
| **Holdings** | Sortable table, Filters, XIRR by scheme, Top/Bottom performers |
| **Allocation** | Equity/Debt breakdown, Category drill-down, Benchmark comparison |
| **Calendar** | FD maturities, ELSS unlocks, SIP due dates, PPF eligibility |
| **Alerts** | Red/Yellow/Green priority alerts with actionable fixes |
| **Risk** | Risk score, Volatility, Sharpe ratio, Max drawdown, Rolling returns |
| **Glide Path** | Current vs target allocation, Drift indicators, Rebalancing calculator |
| **Recommendations** | Priority-ranked action list with quantified impact |

---

## 📈 Supported Asset Classes

| Asset | Input Method | Auto-Update | Analysis |
|-------|--------------|-------------|----------|
| **Mutual Funds** | CAS PDF/CSV | AMFI NAV daily | XIRR, Allocation, Risk |
| **Fixed Deposits** | CSV Upload | Manual refresh | Interest calc, Maturity tracking |
| **PPF** | CSV Upload | Manual refresh | Lock-in tracking, Withdrawal dates |
| **NPS** | CSV Upload | Manual refresh | Allocation analysis, Tier-1/2 split |
| **Cash** | Manual entry | Manual | Liquidity ratio, Drag analysis |

---

## 🔧 Configuration

All configs in `config/` directory:

**Alert Thresholds** (`config/limits.yaml`):
```yaml
concentration_limit: 0.15      # Max 15% in single scheme
top3_limit: 0.50               # Top 3 schemes max 50%
cash_limit: 0.10                 # Cash drag max 10%
equity_deviation: 0.05          # ±5% from target allocation
```

**Age-Based Allocation** (`config/glide_path.yaml`):
```yaml
glide_path:
  age_35:
    equity: 60    # 60% aggressive at age 35
    debt: 35
    gold: 3
    cash: 2
```

**Scheme Classification** (`config/categories.yaml`):
```yaml
categories:
  elss:
    patterns: ["ELSS", "Tax Saver", "Tax Saver Fund"]
    lock_in_years: 3
    asset_class: "equity"
    tax_status: "80c_eligible"
```

---

## 🧪 Running Tests

```bash
# Run all tests
python3 -m pytest tests/

# Run specific test
python3 tests/test_alerts.py

# Run with verbose output
python3 -m pytest tests/ -v
```

---

## 📚 Documentation

**Complete User Guide:** `docs/USER_GUIDE.md`

Covers:
- Installation & setup
- Uploading CAS statements
- CSV templates for FD/PPF/NPS
- Understanding each dashboard tab
- Interpreting risk scores and XIRR
- Tax-loss harvesting strategies
- Troubleshooting common issues
- Advanced configuration

---

## 🛠️ Development

### Adding New Features

**1. New Alert Type:**
Edit `app/components/alerts.py`:
```python
def check_custom_alert(holdings_df):
    # Your logic
    return Alert(...)
```

**2. New Data Source:**
Create `api/custom_provider.py`:
```python
from api.nav_provider import NavProvider

class CustomProvider(NavProvider):
    def get_nav(self, isin, date=None):
        # API logic
        pass
```

**3. New Visualization:**
Create `app/components/custom_view.py`:
```python
import streamlit as st
import plotly.express as px

def render():
    st.plotly_chart(fig)
```

### Database Schema

```sql
-- Core holdings table
CREATE TABLE holdings (
    id INTEGER PRIMARY KEY,
    isin TEXT,
    scheme_name TEXT,
    category TEXT,
    asset_type TEXT,  -- MF, FD, PPF, NPS
    units REAL,
    purchase_value REAL,
    purchase_date TEXT,
    folio TEXT,
    amc TEXT,
    current_nav REAL,
    current_value REAL,
    xirr REAL,
    last_updated TEXT
);

-- Transactions for XIRR calculation
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    isin TEXT,
    type TEXT,  -- PURCHASE, REDEMPTION, DIVIDEND
    date TEXT,
    amount REAL,
    units REAL,
    nav REAL
);

-- NAV history for risk metrics
CREATE TABLE nav_history (
    isin TEXT,
    date TEXT,
    nav REAL,
    PRIMARY KEY (isin, date)
);
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| CAS not parsing | Remove PDF password, check if text-based (not scanned) |
| NAV not updating | Check internet, AMFI API status, retry |
| XIRR error | Ensure both purchases and current value present |
| Import errors | `pip install -r requirements.txt` |
| Database locked | Close app, restart Streamlit |
| ISIN not found | Add manually or update `isin_master.db` |

See `docs/USER_GUIDE.md` Section 8 for detailed troubleshooting.

---

## 📊 Sample Output

**Dashboard Overview:**
```
┌──────────────────────────────────────────────────────────────┐
│  TOTAL AUM          XIRR (1Y)        XIRR (3Y)    RISK      │
│  ₹ 25,45,678        18.5%            14.2%          42/100   │
│                                                              │
│  ASSET ALLOCATION                                          │
│  Equity 58% ████████████████████░░░░░░░░░░░░░░░░  Target 60%│
│  Debt   32% ███████████░░░░░░░░░░░░░░░░░░░░░░░░░  Target 35%│
│  Gold    5% ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  Target 3% │
│  Cash    5% ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  Target 2% │
└──────────────────────────────────────────────────────────────┘
```

**Alert Example:**
```
🔴 CRITICAL: Concentration Risk
   HDFC Top 100 Fund: 18% of portfolio (Limit: 15%)
   Action: Reduce by ₹75,000 → Switch to Nifty 50 Index
   Tax Impact: ₹0 (LTCG eligible)
```

---

## 🤝 Contributing

This is a personal project - modify freely for your needs.

To extend:
1. Fork the logic
2. Edit files in `app/`, `utils/`, `parsers/`
3. Restart Streamlit to see changes
4. Test with your data

---

## 📝 License

Personal use only. Built for Ashish Prakash's portfolio management.

---

## 🙏 Acknowledgments

- **AMFI India** - Free NAV API
- **CAMS/Karvy** - CAS statement ecosystem
- **RBI** - Risk-free rate data
- **Streamlit** - Dashboard framework
- **Plotly** - Visualizations

---

**Built with ❤️ for treasury professionals who demand precision in personal finance.**

*Remember: This tool provides analysis, not investment advice.*
