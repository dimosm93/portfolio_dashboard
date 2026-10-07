# Portfolio Dashboard - Project State

## Tech Stack
- Python 3.x
- Streamlit
- Database: 
  - Main Branch: SQLite (portfolio.db)
  - feature/cloud-deployment Branch: Turso Cloud DB (libsql-client)
- Plotly (Express & Graph Objects)
- Pandas & NumPy
- yfinance

## Active Branches
1. **main**: The stable, local-only version (SQLite).
2. **feature/cloud-deployment**: Cloud-ready version with Turso DB integration and st.secrets authentication. Deployed to Streamlit Community Cloud for testing.

## Security & Secrets
- `APP_PASSWORD`: Used for a custom login screen on the Cloud branch.
- `TURSO_URL` & `TURSO_AUTH_TOKEN`: Used for Cloud DB connection.
- All secrets are managed locally via `.streamlit/secrets.toml` and safely ignored by `.gitignore`.

## Upcoming Tasks (Next Session)
1. **Performance Optimization (Cloud Branch)**: Address the slow loading times caused by `yfinance` network calls and Turso HTTP requests by implementing Streamlit's `@st.cache_data` (TTL caching) for both live price fetching and raw transaction fetching.
2. Ensure cache is cleared appropriately upon any CRUD (Add/Edit/Delete) operation.
3. Evaluate the cloud testing period and decide whether to merge `feature/cloud-deployment` into `main`.