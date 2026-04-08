# Portfolio Analytics Tool - Quick Start Guide

**Get up and running in 5 minutes**

---

## ⚡ 30-Second Setup

```bash
cd ~/workspace/portfolio-analytics
python3 setup.py
```

Done! Now launch:
```bash
streamlit run app.py
```

---

## 📊 Your First Portfolio View

### Option A: Use Sample Data (1 minute)

```bash
python3 app.py sample
streamlit run app.py
```

You'll see a ₹25+ Lakh sample portfolio with 6 MFs, 2 FDs, 1 PPF, 3 NPS allocations.

### Option B: Upload Your Real CAS (5 minutes)

**Step 1:** Get your CAS statement
- Go to https://www.camsonline.com
- Click "CAS Statement"
- Enter PAN, email, choose period (last 3 years)
- Download PDF

**Step 2:** Upload in dashboard
- Launch: `streamlit run app.py`
- Sidebar → "📁 Upload CAS Statement"
- Select your PDF
- Click "🔄 Update NAV Data"

**Step 3:** View your portfolio
- Total AUM, XIRR, Risk Score
- Asset allocation pie chart
- Holdings table with XIRR per scheme

---

## 🎯 Understanding Your Dashboard

### 8 Tabs Explained

| Tab | What It Shows | Action Item |
|-----|---------------|-------------|
| **Overview** | Total AUM, XIRR (1Y/3Y), Risk Score | Check if Risk Score < 50 |
| **Holdings** | All schemes with XIRR, NAV, Value | Sort by XIRR, check losers |
| **Allocation** | Equity/Debt/Gold/Cash split | Compare to targets |
| **Calendar** | Upcoming maturities, unlocks | Plan liquidity |
| **Alerts** | Red/Yellow/Green flags | Read top 3 alerts |
| **Risk** | Volatility, Sharpe, Drawdown | Check if Sharpe > 1.0 |
| **Glide Path** | Current vs Target allocation | Rebalance if drift > 5% |
| **Recommendations** | Priority action list | Execute top 3 |

### Key Metrics Explained

**XIRR (Extended Internal Rate of Return)**
- True annualized return accounting for SIP dates
- Better than CAGR (which ignores timing)
- >15% = Excellent, 8-15% = Good, <8% = Review

**Risk Score (0-100)**
- 0-25: Conservative
- 26-50: Moderate (✓ Good for age 35)
- 51-75: Aggressive
- 76-100: Speculative

**Glide Path**
- At 35: Target 60% Equity, 35% Debt, 3% Gold, 2% Cash
- Auto-reduces 1% equity per year after 40
- Protects from market crashes near retirement

---

## 🚨 First Actions to Take

### Immediate (Today)

1. **Check Concentration Risk**
   - Go to Alerts tab
   - If any scheme >15% → Consider diversifying
   - If top 3 >50% → Must rebalance

2. **Check Cash Drag**
   - In Overview, see "Cash %"
   - If >10% → Deploy to Liquid Bees/Arbitrage fund

3. **Review ELSS Lock-ins**
   - Calendar tab → ELSS unlocks
   - Plan exit strategy for maturing ELSS

### This Week

4. **Upload FD/PPF/NPS**
   - Download templates from `templates/` folder
   - Fill your data
   - Upload via "Upload Manual Assets" tab

5. **Review Risk Dashboard**
   - Check Sharpe Ratio (target >1.0)
   - Review Max Drawdown (should be <20%)

### This Month

6. **Tax Loss Harvesting**
   - Recommendations tab → "Tax Loss Opportunities"
   - Sell losers, offset gains, save tax

7. **Rebalancing**
   - Glide Path tab → Rebalancing Calculator
   - Execute trades to match target allocation

---

## 📁 File Structure Quick Reference

```
portfolio-analytics/
├── app.py              ← START HERE (streamlit run app.py)
├── setup.py            ← Run once to setup
├── docs/
│   └── USER_GUIDE.md   ← Full documentation (30 pages)
├── templates/
│   ├── fd_template.csv ← For bank FDs
│   ├── ppf_template.csv ← For PPF account
│   └── nps_template.csv ← For NPS allocations
├── config/
│   ├── limits.yaml     ← Alert thresholds (edit me)
│   └── glide_path.yaml ← Age allocation (edit me)
└── data/
    └── portfolio.db    ← Your data (auto-created)
```

---

## 🛠️ Customization

### Change Alert Thresholds

Edit `config/limits.yaml`:
```yaml
concentration_limit: 0.20  # Allow up to 20% per scheme (default 15%)
cash_limit: 0.15             # Allow up to 15% cash (default 10%)
```

### Change Age-Based Targets

Edit `config/glide_path.yaml`:
```yaml
glide_path:
  age_35:
    equity: 65    # More aggressive than default 60%
    debt: 30
```

### Add Custom Scheme Categories

Edit `config/categories.yaml`:
```yaml
my_custom_category:
  patterns: ["Special", "Opportunity"]
  asset_class: "equity"
  risk_level: "high"
```

---

## ❓ Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| CAS PDF not parsing | Remove password, ensure not scanned image |
| "streamlit: command not found" | `pip install streamlit` |
| Old NAV showing | Click "🔄 Update NAV Data" in sidebar |
| Missing ISIN | Add to data/isin_master.db manually |
| Database locked | Restart Streamlit: Ctrl+C, then `streamlit run app.py` |

---

## 📞 Getting Help

1. **This Quickstart** (you're reading it)
2. **Full User Guide**: `docs/USER_GUIDE.md` (30 pages, detailed)
3. **Code Comments**: Every file has inline documentation
4. **Sample Data**: `python3 app.py sample` generates test data

---

## ✅ Checklist: First Week

- [ ] Run `python3 setup.py`
- [ ] Launch with `streamlit run app.py`
- [ ] Upload CAS statement OR generate sample data
- [ ] Check all 8 dashboard tabs
- [ ] Read top 3 alerts
- [ ] Review Risk Score
- [ ] Download FD/PPF/NPS templates
- [ ] Fill and upload manual assets
- [ ] Check Glide Path vs Current allocation
- [ ] Note 1 action to take this week

---

**You're all set! Happy investing! 📈**

*Built for treasury professionals who demand precision.*
