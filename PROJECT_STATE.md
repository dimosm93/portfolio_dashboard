# Portfolio Dashboard - Project State

## Tech Stack
- Python 3.x
- Streamlit
- SQLite (portfolio.db)
- Plotly (Express & Graph Objects)
- yfinance

## Operational Guidelines & Rules
- OS Environment: Windows (NO emojis in UI text to avoid UTF-8 console/editor encoding issues).
- Layout: Clean UI using tabs (st.tabs) and expandable sections (st.expander).
- Database Security: Local storage using portfolio.db (ignored in .gitignore).

## Database Schema (transactions table)
- id (INTEGER PRIMARY KEY AUTOINCREMENT)
- date (TEXT YYYY-MM-DD)
- ticker (TEXT)
- category (Stock, Crypto, ETF, Robo-Advisor)
- exchange (TEXT)
- action (BUY, SELL, DIVIDEND, FEE, SYNC_VALUE)
- quantity (REAL)
- price (REAL)
- fee (REAL)

## Completed Features
1. Multi-asset & Multi-broker portfolio tracking.
2. Realised PnL, Dividends, and Fees calculation.
3. Live market data fetching via yfinance with multi-tier fallback logic.
4. Interactive Portfolio Allocation Pie Chart.
5. Historical Portfolio Growth Line Chart (Invested Capital vs Portfolio Value).
6. Full Transaction CRUD (Add, Edit, Delete).
7. Collapsible UI sections using st.expander.
