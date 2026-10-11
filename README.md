Markdown
# 📈 Personal Investment Dashboard

A comprehensive, Python-based web application to track and analyze your personal investments across multiple brokers and asset classes. Built with Streamlit, it offers live market data fetching, historical growth tracking, built-in tax reporting helpers, and a standalone stock screening tool.

**Cloud & Database:** The application is configured for deployment on Streamlit Community Cloud, using **Turso** as a secure, distributed cloud database.

## ✨ Key Features
- **Multi-Asset Tracking:** Manage Stocks, ETFs, Crypto, and Robo-Advisors in one unified platform.
- **Live Market Data:** Automatic live price fetching using `yfinance` with multi-tier fallback mechanisms.
- **Advanced Analytics:** 
  - Realised & Unrealised PnL calculations.
  - Dividend and Fee tracking.
  - Historical Portfolio Growth chart (Invested Capital vs. Portfolio Value).
  - Annual Performance Summary (Year-over-Year Return %).
- **📈 Stock Screener (NEW):** A built-in fundamental valuation engine evaluating stocks based on sector-adjusted metrics (P/E, PEG, EV/EBITDA).
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

## 🚀 Local Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone [https://github.com/dimosm93/portfolio_dashboard.git](https://github.com/dimosm93/portfolio_dashboard.git)
   cd portfolio_dashboard
Install the required dependencies:
Make sure you have Python installed, then run:

Bash
pip install -r requirements.txt
Database Configuration (Secrets):
Create a folder named .streamlit in the root directory and add a secrets.toml file with your Turso credentials:

Ini, TOML
TURSO_DATABASE_URL = "libsql://[your-database-name].turso.io"
TURSO_AUTH_TOKEN = "your-auth-token"
Run the application:
Launch the Streamlit server locally:

Bash
streamlit run dashboard.py
The dashboard will automatically open in your default web browser at http://localhost:8501.

⚠️ Disclaimer
This software is provided for educational and informational purposes only. It does not constitute financial, investment, or tax advice. Always consult with a certified accountant for your tax declarations.

