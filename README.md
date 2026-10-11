# 📈 Personal Investment Dashboard

A comprehensive, Python-based web application to track and analyze your personal investments across multiple brokers and asset classes. Built with Streamlit, it offers live market data fetching, historical growth tracking, built-in tax reporting helpers, and a standalone stock screening tool.

**Cloud & Database:** The application is fully configured for cloud deployment on Streamlit Community Cloud, utilizing **Turso** as a secure, distributed remote database.

## ✨ Key Features
- **Multi-Asset Tracking:** Manage Stocks, ETFs, Crypto, and Robo-Advisors in one unified platform.
- **Live Market Data:** Automatic live price fetching using `yfinance` with multi-tier fallback mechanisms.
- **Advanced Analytics:** 
  - Realised & Unrealised PnL calculations.
  - Dividend and Fee tracking.
  - Historical Portfolio Growth chart (Invested Capital vs. Portfolio Value).
  - Annual Performance Summary (Year-over-Year Return %).
- **📈 Stock Screener:** A built-in fundamental valuation engine evaluating stocks based on sector-adjusted metrics (P/E, PEG, EV/EBITDA).
- **🇬🇷 Greek Tax (E1) Helper:** Automatically calculates amounts for Greek tax declaration codes based on your transaction history:
  - Code 743: Asset Purchases
  - Code 659/660: Realised Capital Gains
  - Code 295/296: Gross Dividends
  - Code 029/030: Foreign Tax Paid

## 🛠️ Tech Stack
- **Frontend & Backend:** Streamlit (Python)
- **Data Processing:** Pandas, NumPy
- **Market Data:** yfinance
- **Visualizations:** Plotly (Express & Graph Objects)
- **Database:** Turso (libsql-experimental)

## ☁️ Cloud Deployment (Streamlit Community Cloud)

To deploy this dashboard on the web using Streamlit Cloud and Turso DB:

1. **GitHub Setup:** Push this repository to your GitHub account on the `main` branch.
2. **Streamlit Cloud:** Go to [share.streamlit.io](https://share.streamlit.io) and click **"New app"**.
3. **App Configuration:**
   - Select your repository (`portfolio_dashboard`) and set the branch to `main`.
   - Main file path: `dashboard.py`.
   - ⚠️ **Important:** Go to *Advanced Settings* and set the **Python version to 3.11** (required for `libsql-experimental` wheels to build correctly).
4. **Environment Secrets:** 
   In the Streamlit Cloud dashboard, go to your app's **Settings > Secrets** and paste your Turso Database credentials:
   ```toml
   TURSO_DATABASE_URL = "libsql://[your-database-name].turso.io"
   TURSO_AUTH_TOKEN = "your-auth-token"
   ```
5. Click **Deploy!**

## 🚀 Local Setup & Installation

If you prefer to run it locally for development:

1. **Clone the repository:**
   ```bash
   git clone https://github.com/dimosm93/portfolio_dashboard.git
   cd portfolio_dashboard
   ```

2. **Install dependencies:**
   Make sure you have Python 3.11 installed, then run:
   ```bash
   pip install -r requirements.txt
   ```

3. **Local Secrets:**
   Create a folder named `.streamlit` in the root directory and add a `secrets.toml` file with your Turso credentials:
   ```toml
   TURSO_DATABASE_URL = "libsql://[your-database-name].turso.io"
   TURSO_AUTH_TOKEN = "your-auth-token"
   ```

4. **Run the application:**
   ```bash
   streamlit run dashboard.py
   ```

## ⚠️ Disclaimer
This software is provided for educational and informational purposes only. It does not constitute financial, investment, or tax advice. Always consult with a certified accountant for your tax declarations.
