# 📈 Personal Investment Dashboard

A comprehensive, Python-based local web application to track and analyze your personal investments across multiple brokers and asset classes. Built with Streamlit, it offers live market data fetching, historical growth tracking, and built-in tax reporting helpers. 

**Privacy First:** This version runs entirely on your local machine. All financial data is stored locally in an SQLite database (`portfolio.db`) and never leaves your computer.

##  Key Features

* **Multi-Asset Tracking:** Manage Stocks, ETFs, Crypto, and Robo-Advisors in one unified platform.
* **Live Market Data:** Automatic live price fetching using `yfinance` with multi-tier fallback mechanisms.
* **Advanced Analytics:**
  * Realised & Unrealised PnL calculations.
  * Dividend and Fee tracking.
  * Historical Portfolio Growth chart (Invested Capital vs. Portfolio Value).
  * Annual Performance Summary (Year-over-Year Return %).
  * Dynamic Dashboard View Mode (Live vs. Historical End-of-Year Snapshot).
* **🇬🇷 Greek Tax (E1) Helper:** Automatically calculates amounts for Greek tax declaration codes based on your transaction history:
  * **Code 743:** Asset Purchases
  * **Code 659/660:** Realised Capital Gains
  * **Code 295/296:** Gross Dividends
  * **Code 029/030:** Foreign Tax Paid

## 🛠️ Tech Stack

* **Frontend & Backend:** [Streamlit](https://streamlit.io/) (Python)
* **Data Processing:** Pandas, NumPy
* **Market Data:** `yfinance`
* **Visualizations:** Plotly (Express & Graph Objects)
* **Database:** SQLite (Local `portfolio.db`)

## 🚀 Local Setup & Installation
1. **Clone the repository:**
   ```bash
   git clone [https://github.com/dimosm93/portfolio_dashboard.git](https://github.com/dimosm93/portfolio_dashboard.git)
   cd portfolio_dashboard

   
Install the required dependencies: 
Make sure you have Python installed, then run:

Bash
pip install -r requirements.txt
Run the application:
Launch the Streamlit server locally:

Bash
streamlit run dashboard.py
The dashboard will automatically open in your default web browser at http://localhost:8501.

🗄️ Database Management
The app will automatically create a local portfolio.db SQLite file in the root directory upon the first run. Make sure that portfolio.db is included in your .gitignore file to prevent accidentally uploading your personal financial data to GitHub.

⚠️ Disclaimer
This software is provided for educational and informational purposes only. It does not constitute financial, investment, or tax advice. Always consult with a certified accountant for your tax declarations.
