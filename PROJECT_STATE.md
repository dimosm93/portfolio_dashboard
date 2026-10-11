# PROJECT_STATE.md — LLM Context & Memory Sheet

## Project Overview
**Personal Investment Dashboard** is a production-grade, Python-based web application built with Streamlit and deployed on Streamlit Community Cloud. It provides real-time portfolio management, historical performance analytics, fundamental stock screening, and automated Greek tax (E1 form) reporting for multi-broker, multi-asset portfolios (Stocks, ETFs, Crypto, Robo-Advisors).

---

## Technical Stack & Runtime Environment
- **Language & Runtime:** Python 3.11 
- **Frontend & App Framework:** Streamlit
- **Database:** Turso Cloud Database (Distributed SQLite-compatible database using `libsql-experimental`)
- **Data Processing & Analytics:** Pandas, NumPy
- **Financial Data Integration:** `yfinance` (with fallback mechanisms)
- **Visualizations:** Plotly (Express & Graph Objects)

---

## Repository & Deployment Architecture
- **Repository:** `dimosm93/portfolio_dashboard`
- **Active Branch:** `main` (Single source of truth. All feature branches `feature/cloud-deployment` and `feature/screener-integration` have been merged and deleted).
- **Deployment Platform:** Streamlit Community Cloud
- **Entry Point:** `dashboard.py`
- **Cloud Settings:** Advanced Settings configured specifically to **Python 3.11**.

---

## Security, Secrets & Environment Configuration
- **Local Development Secrets File:** `.streamlit/secrets.toml` (Strictly excluded via `.gitignore`).
- **Cloud Environment Secrets:** Managed via Streamlit Community Cloud Dashboard (`Settings > Secrets`).
- **Required Secret Keys:**
  - `TURSO_DATABASE_URL`: Connection string (`libsql://<db-name>.turso.io`)
  - `TURSO_AUTH_TOKEN`: Turso database JWT auth token
  - `PASSWORD` / `APP_PASSWORD`: Custom application authentication password

---

## Key Modules & Core Features

1. **Portfolio Analytics & Tracking:**
   - Multi-broker, multi-asset consolidation (Stocks, ETFs, Crypto, Robo-Advisors).
   - Realized vs. Unrealized Profit & Loss (PnL) engine.
   - Dividend and fee tracking across currencies.
   - Dynamic view modes (Live Market Data vs. Historical End-of-Year Snapshot).
   - Portfolio growth chart (Capital Invested vs. Total Portfolio Value over time).

2. **Stock Screener Module:**
   - Fundamental valuation analysis tool.
   - Sector-adjusted metrics evaluation (P/E, PEG, EV/EBITDA ratios).

3. **Greek Tax (E1) Reporting Helper:**
   - Automated aggregation of transaction history into specific Greek tax return codes:
     - **Code 743:** Asset Purchases
     - **Code 659/660:** Realized Capital Gains
     - **Code 295/296:** Gross Dividend Income
     - **Code 029/030:** Foreign Tax Withheld

---

## Developer & LLM Operational Guidelines
- **Branch Strategy:** Work directly on `main` or merge temporary feature branches immediately after testing. Keep the repo history clean.
- **Dependency Guardrail:** Do not upgrade Python version beyond 3.11 in cloud settings without verifying `libsql-experimental` compatibility.
- **Database Operations:** Always execute queries using parameter substitution (`?`) to prevent SQL injection and compatibility issues with the `libsql` driver.
- **Secrets Management:** Never print, log, or hardcode Turso credentials or application passwords.

Upcoming Tasks (Next Session)
Performance Optimization (Cloud Branch): Address the slow loading times caused by yfinance network calls and Turso HTTP requests by implementing Streamlit's @st.cache_data (TTL caching) for both live price fetching and raw transaction fetching.
Ensure cache is cleared appropriately upon any CRUD (Add/Edit/Delete) operation.