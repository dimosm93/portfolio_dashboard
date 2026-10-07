import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import date, datetime, timedelta
import libsql_client

# 1. Page Configuration
st.set_page_config(page_title="Personal Investment Dashboard", layout="wide")

# 2. Security / Authentication
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("Personal Investment Dashboard")
        st.subheader("Authentication Required")
        
        with st.form("login_form"):
            pwd = st.text_input("Enter Dashboard Password", type="password")
            submit = st.form_submit_button("Login")
            
            if submit:
                target_pwd = st.secrets.get("APP_PASSWORD", "1234")
                if pwd == target_pwd:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password.")
        st.stop()

check_password()

st.title("Personal Investment Dashboard")

# Database Helper Functions using Turso
def get_turso_client():
    url = st.secrets["TURSO_URL"]
    token = st.secrets["TURSO_AUTH_TOKEN"]
    if url.startswith("libsql://"):
        url = url.replace("libsql://", "https://")
    return libsql_client.create_client_sync(url=url, auth_token=token)

def run_stmt(sql, params=None):
    client = get_turso_client()
    if params:
        client.execute(sql, list(params))
    else:
        client.execute(sql)
    client.close()

# Helper function to fetch live price with multiple fallbacks
def fetch_live_price(ticker):
    ticker = str(ticker).replace(" ", "").upper()
    if not ticker:
        return np.nan
    
    try:
        tk = yf.Ticker(ticker)
        if hasattr(tk, 'fast_info'):
            fi = tk.fast_info
            for attr in ['last_price', 'previous_close', 'regular_market_price']:
                val = getattr(fi, attr, None)
                if val is not None and not np.isnan(val) and val > 0:
                    return float(val)
                try:
                    val_dict = fi[attr]
                    if val_dict is not None and not np.isnan(val_dict) and val_dict > 0:
                        return float(val_dict)
                except Exception:
                    pass
    except Exception:
        pass

    try:
        tk = yf.Ticker(ticker)
        hist = tk.history(period="1mo")
        if not hist.empty and 'Close' in hist.columns:
            valid_closes = hist['Close'].dropna()
            if not valid_closes.empty:
                return float(valid_closes.iloc[-1])
    except Exception:
        pass

    try:
        df = yf.download(ticker, period="5d", progress=False)
        if not df.empty and 'Close' in df.columns:
            if isinstance(df['Close'], pd.DataFrame):
                closes = df['Close'].iloc[:, 0].dropna()
            else:
                closes = df['Close'].dropna()
            if not closes.empty:
                return float(closes.iloc[-1])
    except Exception:
        pass

    return np.nan

# 3. Function to Load & Calculate Portfolio Data
def get_portfolio_data():
    client = get_turso_client()
    
    client.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            ticker TEXT,
            category TEXT,
            exchange TEXT,
            action TEXT,
            quantity REAL,
            price REAL,
            fee REAL DEFAULT 0.0,
            foreign_tax REAL DEFAULT 0.0
        )
    ''')
    
    rs = client.execute("SELECT * FROM transactions")
    df = pd.DataFrame(rs.rows, columns=rs.columns)
    client.close()
    
    if df.empty:
        return df, pd.DataFrame(), 0.0, 0.0, 0.0

    portfolio = {}
    realised_pnl_total = 0.0
    total_dividends_overall = 0.0
    total_fees_overall = 0.0
    
    for index, row in df.iterrows():
        ticker = str(row['ticker']).replace(" ", "").upper() if row['ticker'] else ''
        exchange = str(row['exchange']).strip() if row['exchange'] else 'Main'
        action = row['action']
        qty = float(row['quantity']) if row['quantity'] else 0.0
        price = float(row['price']) if row['price'] else 0.0
        trade_fee = float(row['fee']) if ('fee' in row and pd.notnull(row['fee'])) else 0.0
        
        key = (ticker, exchange)
        
        if key not in portfolio:
            portfolio[key] = {
                'Ticker': ticker,
                'Exchange': exchange,
                'Category': row['category'],
                'Qty': 0.0,
                'Avg Price': 0.0,
                'Realised PnL': 0.0,
                'Dividends': 0.0,
                'Fees': 0.0,
                'Manual_Value': None
            }
            
        p = portfolio[key]
        
        if action == 'BUY':
            total_cost = (p['Qty'] * p['Avg Price']) + (qty * price) + trade_fee
            p['Qty'] += qty
            p['Avg Price'] = total_cost / p['Qty'] if p['Qty'] > 0 else 0.0
            p['Fees'] += trade_fee
            total_fees_overall += trade_fee
            if p['Manual_Value'] is not None:
                p['Manual_Value'] += (qty * price)
            
        elif action == 'SELL':
            net_proceeds = (qty * price) - trade_fee
            profit = net_proceeds - (qty * p['Avg Price'])
            p['Realised PnL'] += profit
            realised_pnl_total += profit
            p['Qty'] -= qty
            p['Fees'] += trade_fee
            total_fees_overall += trade_fee
            if p['Manual_Value'] is not None:
                p['Manual_Value'] -= (qty * price)
            
        elif action == 'DIVIDEND':
            div_amount = price if price > 0 else (qty * price)
            p['Dividends'] += div_amount
            total_dividends_overall += div_amount
            
        elif action == 'FEE':
            fee_amount = price if price > 0 else trade_fee
            p['Fees'] += fee_amount
            total_fees_overall += fee_amount
            if p['Manual_Value'] is not None:
                p['Manual_Value'] -= fee_amount
                
        elif action == 'SYNC_VALUE':
            p['Manual_Value'] = price

    port_df = pd.DataFrame(list(portfolio.values()))
    if port_df.empty:
        return df, pd.DataFrame(), 0.0, 0.0, 0.0
        
    port_df = port_df[port_df['Qty'] > 0].copy()

    if not port_df.empty:
        yf_tickers = port_df[port_df['Category'] != 'Robo-Advisor']['Ticker'].unique()
        live_prices = {}
        
        if len(yf_tickers) > 0:
            for ticker in yf_tickers:
                live_prices[ticker] = fetch_live_price(ticker)
                
        port_df['Live Price'] = port_df['Ticker'].map(live_prices)
        port_df['Invested Value'] = port_df['Qty'] * port_df['Avg Price']
        
        robo_mask = port_df['Category'] == 'Robo-Advisor'
        
        port_df.loc[~robo_mask, 'Current Value'] = port_df.loc[~robo_mask, 'Qty'] * port_df.loc[~robo_mask, 'Live Price']
        port_df.loc[robo_mask, 'Current Value'] = port_df.loc[robo_mask, 'Manual_Value'].fillna(port_df.loc[robo_mask, 'Invested Value'])
        port_df.loc[robo_mask, 'Live Price'] = np.where(port_df.loc[robo_mask, 'Qty'] > 0, port_df.loc[robo_mask, 'Current Value'] / port_df.loc[robo_mask, 'Qty'], 0.0)
        
        port_df['Unrealised PnL (EUR)'] = port_df['Current Value'] - port_df['Invested Value']
        port_df['Unrealised PnL (%)'] = np.where(port_df['Invested Value'] > 0, (port_df['Unrealised PnL (EUR)'] / port_df['Invested Value']) * 100, 0.0)
        
        port_df = port_df.round(2)
        
    return df, port_df, realised_pnl_total, total_dividends_overall, total_fees_overall

# 4. Function to Calculate Historical Portfolio Growth
@st.cache_data(ttl=3600)
def get_portfolio_growth_df(raw_df):
    if raw_df.empty:
        return pd.DataFrame()
        
    df = raw_df.copy()
    df['date_dt'] = pd.to_datetime(df['date'])
    df = df.sort_values('date_dt')
    
    start_date = df['date_dt'].min().date()
    end_date = date.today()
    
    if start_date > end_date:
        start_date = end_date
        
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    standard_txs = df[df['category'] != 'Robo-Advisor']
    unique_tickers = [str(t).replace(" ", "").upper() for t in standard_txs['ticker'].unique() if t]
    
    hist_prices = {}
    for ticker in unique_tickers:
        try:
            tk = yf.Ticker(ticker)
            h = tk.history(start=start_date.strftime("%Y-%m-%d"), end=(end_date + timedelta(days=1)).strftime("%Y-%m-%d"))
            if not h.empty and 'Close' in h.columns:
                h.index = pd.to_datetime(h.index).tz_localize(None)
                s = h['Close'].reindex(date_range)
                s = s.ffill().bfill()
                hist_prices[ticker] = s
        except Exception:
            pass

    growth_data = []
    
    for current_dt in date_range:
        sub_df = df[df['date_dt'] <= current_dt]
        if sub_df.empty:
            continue
            
        invested_tot = 0.0
        current_val_tot = 0.0
        holdings = {}
        robo_vals = {}
        
        for _, row in sub_df.iterrows():
            ticker = str(row['ticker']).replace(" ", "").upper() if row['ticker'] else ''
            exchange = str(row['exchange']).strip() if row['exchange'] else 'Main'
            action = row['action']
            qty = float(row['quantity']) if row['quantity'] else 0.0
            price = float(row['price']) if row['price'] else 0.0
            trade_fee = float(row['fee']) if ('fee' in row and pd.notnull(row['fee'])) else 0.0
            cat = row['category']
            
            key = (ticker, exchange)
            if key not in holdings:
                holdings[key] = {'qty': 0.0, 'cost': 0.0, 'cat': cat}
                
            if action == 'BUY':
                holdings[key]['qty'] += qty
                holdings[key]['cost'] += (qty * price) + trade_fee
                invested_tot += (qty * price) + trade_fee
                if cat == 'Robo-Advisor':
                    robo_vals[key] = robo_vals.get(key, 0.0) + (qty * price)
            elif action == 'SELL':
                holdings[key]['qty'] -= qty
                net_proceeds = (qty * price) - trade_fee
                invested_tot -= net_proceeds
                if cat == 'Robo-Advisor':
                    robo_vals[key] = max(0.0, robo_vals.get(key, 0.0) - (qty * price))
            elif action == 'FEE':
                fee_amt = price if price > 0 else trade_fee
                invested_tot += fee_amt
            elif action == 'SYNC_VALUE':
                if cat == 'Robo-Advisor':
                    robo_vals[key] = price

        for (ticker, exchange), item in holdings.items():
            qty = item['qty']
            if qty <= 0:
                continue
            cat = item['cat']
            
            if cat == 'Robo-Advisor':
                current_val_tot += robo_vals.get((ticker, exchange), item['cost'])
            else:
                p_series = hist_prices.get(ticker)
                if p_series is not None and current_dt in p_series.index and pd.notnull(p_series.loc[current_dt]):
                    current_val_tot += qty * float(p_series.loc[current_dt])
                else:
                    current_val_tot += item['cost']
                    
        growth_data.append({
            'Date': current_dt,
            'Invested Capital': round(invested_tot, 2),
            'Portfolio Value': round(current_val_tot, 2),
            'Unrealised PnL': round(current_val_tot - invested_tot, 2)
        })

    return pd.DataFrame(growth_data)

# 5. Function to Calculate Annual Performance Summary
def get_annual_performance_df(growth_df):
    if growth_df.empty:
        return pd.DataFrame()
        
    df = growth_df.copy()
    df['Year'] = pd.to_datetime(df['Date']).dt.year
    current_year = date.today().year
    
    annual_rows = []
    prev_unrealised = 0.0
    prev_val = 0.0
    prev_inv = 0.0
    
    for y, group in df.groupby('Year'):
        last_row = group.iloc[-1]
        curr_val = float(last_row['Portfolio Value'])
        curr_inv = float(last_row['Invested Capital'])
        curr_unrealised = float(last_row['Unrealised PnL'])
        
        yoy_unrealised_change = curr_unrealised - prev_unrealised
        net_injected = curr_inv - prev_inv
        start_base = prev_val + net_injected
        yoy_return_pct = ((curr_val - start_base) / start_base * 100) if start_base > 0 else 0.0
        
        year_label = str(y) if y < current_year else f"{y} (YTD)"
        
        annual_rows.append({
            'Year': year_label,
            'Portfolio Value (EUR)': round(curr_val, 2),
            'Invested Capital (EUR)': round(curr_inv, 2),
            'End-of-Year Unrealised PnL (EUR)': round(curr_unrealised, 2),
            'YoY Unrealised Change (EUR)': round(yoy_unrealised_change, 2),
            'YoY Return (%)': round(yoy_return_pct, 2)
        })
        
        prev_unrealised = curr_unrealised
        prev_val = curr_val
        prev_inv = curr_inv
        
    return pd.DataFrame(annual_rows)

# Helper function to get cumulative totals up to a specific year
def get_snapshot_totals(raw_df, snapshot_year):
    if raw_df.empty:
        return 0.0, 0.0, 0.0
    
    df = raw_df.copy()
    df['date_dt'] = pd.to_datetime(df['date'])
    df = df[df['date_dt'].dt.year <= snapshot_year].sort_values('date_dt')
    
    portfolio = {}
    realised_pnl = 0.0
    dividends = 0.0
    fees = 0.0
    
    for _, row in df.iterrows():
        ticker = str(row['ticker']).replace(" ", "").upper() if row['ticker'] else ''
        exchange = str(row['exchange']).strip() if row['exchange'] else 'Main'
        action = row['action']
        qty = float(row['quantity']) if row['quantity'] else 0.0
        price = float(row['price']) if row['price'] else 0.0
        trade_fee = float(row['fee']) if ('fee' in row and pd.notnull(row['fee'])) else 0.0
        
        key = (ticker, exchange)
        if key not in portfolio:
            portfolio[key] = {'qty': 0.0, 'avg_price': 0.0}
        p = portfolio[key]
        
        if action == 'BUY':
            total_cost = (p['qty'] * p['avg_price']) + (qty * price) + trade_fee
            p['qty'] += qty
            p['avg_price'] = total_cost / p['qty'] if p['qty'] > 0 else 0.0
            fees += trade_fee
        elif action == 'SELL':
            net_proceeds = (qty * price) - trade_fee
            profit = net_proceeds - (qty * p['avg_price'])
            realised_pnl += profit
            p['qty'] -= qty
            fees += trade_fee
        elif action == 'DIVIDEND':
            div_amount = price if price > 0 else (qty * price)
            dividends += div_amount
        elif action == 'FEE':
            fee_amount = price if price > 0 else trade_fee
            fees += fee_amount
            
    return realised_pnl, dividends, fees

# 6. Function to Calculate Tax / E1 Declaration Values
def get_tax_e1_data(raw_df, selected_year):
    if raw_df.empty:
        return 0.0, 0.0, 0.0, 0.0, pd.DataFrame()

    df = raw_df.copy()
    df['date_dt'] = pd.to_datetime(df['date'])
    df = df.sort_values('date_dt')

    portfolio_state = {}
    code_743_purchases = 0.0
    code_659_realised_gains = 0.0
    code_659_dividends_gross = 0.0
    foreign_tax_total = 0.0
    
    year_records = []

    for index, row in df.iterrows():
        tx_year = row['date_dt'].year
        ticker = str(row['ticker']).replace(" ", "").upper() if row['ticker'] else ''
        exchange = str(row['exchange']).strip() if row['exchange'] else 'Main'
        action = row['action']
        qty = float(row['quantity']) if row['quantity'] else 0.0
        price = float(row['price']) if row['price'] else 0.0
        trade_fee = float(row['fee']) if ('fee' in row and pd.notnull(row['fee'])) else 0.0
        foreign_tax = float(row['foreign_tax']) if ('foreign_tax' in row and pd.notnull(row['foreign_tax'])) else 0.0
        
        key = (ticker, exchange)
        if key not in portfolio_state:
            portfolio_state[key] = {'qty': 0.0, 'avg_price': 0.0}

        state = portfolio_state[key]

        if action == 'BUY':
            total_cost = (state['qty'] * state['avg_price']) + (qty * price) + trade_fee
            state['qty'] += qty
            state['avg_price'] = total_cost / state['qty'] if state['qty'] > 0 else 0.0
            
            if tx_year == selected_year:
                purchase_amount = (qty * price) + trade_fee
                code_743_purchases += purchase_amount
                year_records.append({
                    'Date': row['date'],
                    'Asset': ticker,
                    'Action': 'BUY',
                    'Amount (EUR)': round(purchase_amount, 2),
                    'E1 Code': '743 (Purchases)'
                })

        elif action == 'SELL':
            net_proceeds = (qty * price) - trade_fee
            profit = net_proceeds - (qty * state['avg_price'])
            state['qty'] -= qty

            if tx_year == selected_year:
                code_659_realised_gains += profit
                year_records.append({
                    'Date': row['date'],
                    'Asset': ticker,
                    'Action': 'SELL',
                    'Amount (EUR)': round(profit, 2),
                    'E1 Code': '659/660 (Capital Gains)'
                })

        elif action == 'DIVIDEND':
            if tx_year == selected_year:
                div_gross = price if price > 0 else (qty * price)
                code_659_dividends_gross += div_gross
                foreign_tax_total += foreign_tax
                year_records.append({
                    'Date': row['date'],
                    'Asset': ticker,
                    'Action': 'DIVIDEND',
                    'Amount (EUR)': round(div_gross, 2),
                    'E1 Code': '295/296 (Gross) & 029/030 (Tax)'
                })

    details_df = pd.DataFrame(year_records)
    return code_743_purchases, code_659_realised_gains, code_659_dividends_gross, foreign_tax_total, details_df

# Load main data
raw_df, port_df, total_realised, total_divs, total_fees = get_portfolio_data()

# Navigation Tabs
tab1, tab2, tab3 = st.tabs(["Dashboard", "Transaction Management", "Tax / E1 Helper"])

with tab1:
    if not port_df.empty:
        growth_df = get_portfolio_growth_df(raw_df)
        
        # View Mode Selector (Live vs Historical Year Snapshot)
        col_view, _ = st.columns([1, 2])
        with col_view:
            available_years = []
            if not raw_df.empty:
                available_years = sorted(pd.to_datetime(raw_df['date']).dt.year.unique(), reverse=True)
            
            view_mode = st.selectbox("Dashboard View Mode", ["Live / Current"] + [str(y) for y in available_years])
            
        if view_mode == "Live / Current":
            total_value = port_df['Current Value'].sum()
            total_invested = port_df['Invested Value'].sum()
            total_unrealised = port_df['Unrealised PnL (EUR)'].sum()
            total_unrealised_pct = (total_unrealised / total_invested) * 100 if total_invested > 0 else 0.0
            
            disp_realised = total_realised
            disp_divs = total_divs
            disp_fees = total_fees
        else:
            sel_year = int(view_mode)
            if not growth_df.empty:
                growth_df_temp = growth_df.copy()
                growth_df_temp['Year'] = pd.to_datetime(growth_df_temp['Date']).dt.year
                year_growth = growth_df_temp[growth_df_temp['Year'] <= sel_year]
                
                if not year_growth.empty:
                    last_day = year_growth.iloc[-1]
                    total_value = float(last_day['Portfolio Value'])
                    total_invested = float(last_day['Invested Capital'])
                    total_unrealised = float(last_day['Unrealised PnL'])
                    total_unrealised_pct = (total_unrealised / total_invested) * 100 if total_invested > 0 else 0.0
                else:
                    total_value, total_invested, total_unrealised, total_unrealised_pct = 0.0, 0.0, 0.0, 0.0
            else:
                total_value, total_invested, total_unrealised, total_unrealised_pct = 0.0, 0.0, 0.0, 0.0
                
            disp_realised, disp_divs, disp_fees = get_snapshot_totals(raw_df, sel_year)
            st.caption(f"Showing portfolio snapshot as of end of year **{sel_year}**")

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Value", f"EUR {total_value:,.2f}")
        col2.metric("Total Invested", f"EUR {total_invested:,.2f}")
        col3.metric("Unrealised PnL", f"EUR {total_unrealised:,.2f}", f"{total_unrealised_pct:.2f}%")
        
        st.write("") # Spacer
        
        col4, col5, col6 = st.columns(3)
        col4.metric("Realised PnL", f"EUR {disp_realised:,.2f}")
        col5.metric("Total Dividends", f"EUR {disp_divs:,.2f}")
        col6.metric("Total Fees", f"EUR {disp_fees:,.2f}")
        st.markdown("---")

        # Annual Performance Summary Table
        with st.expander("Annual Performance Summary", expanded=True):
            annual_perf_df = get_annual_performance_df(growth_df)
            if not annual_perf_df.empty:
                st.dataframe(annual_perf_df, use_container_width=True, hide_index=True)
            else:
                st.info("No sufficient historical data for annual performance summary.")

        # Collapsible Historical Portfolio Growth Chart
        with st.expander("Historical Portfolio Growth", expanded=True):
            if not growth_df.empty:
                fig_growth = go.Figure()
                
                fig_growth.add_trace(go.Scatter(
                    x=growth_df['Date'],
                    y=growth_df['Portfolio Value'],
                    mode='lines',
                    name='Portfolio Value (EUR)',
                    line=dict(color='#00CC96', width=2.5),
                    hovertemplate='<b>Date</b>: %{x|%Y-%m-%d}<br><b>Portfolio Value</b>: EUR %{y:,.2f}<extra></extra>'
                ))
                
                fig_growth.add_trace(go.Scatter(
                    x=growth_df['Date'],
                    y=growth_df['Invested Capital'],
                    mode='lines',
                    name='Invested Capital (EUR)',
                    line=dict(color='#636EFA', width=2, dash='dash'),
                    hovertemplate='<b>Invested Capital</b>: EUR %{y:,.2f}<extra></extra>'
                ))
                
                fig_growth.update_layout(
                    margin=dict(t=20, b=20, l=10, r=10),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                    xaxis_title="Date",
                    yaxis_title="Amount (EUR)",
                    hovermode="x unified"
                )
                st.plotly_chart(fig_growth, use_container_width=True)
            else:
                st.info("Add transactions to generate growth history.")

        col_chart, col_table = st.columns([1, 2])

        with col_chart:
            # Collapsible Portfolio Allocation Chart
            with st.expander("Portfolio Allocation", expanded=True):
                plot_df = port_df.dropna(subset=['Current Value'])
                if not plot_df.empty and plot_df['Current Value'].sum() > 0:
                    fig = px.pie(plot_df, values='Current Value', names='Ticker', hover_data=['Exchange'], hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
                    fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.write("Add data to display allocation chart.")

        with col_table:
            # Collapsible Asset Details Table
            with st.expander("Asset Details", expanded=True):
                st.dataframe(
                    port_df[['Ticker', 'Exchange', 'Category', 'Qty', 'Avg Price', 'Live Price', 'Current Value', 'Unrealised PnL (EUR)', 'Unrealised PnL (%)', 'Dividends', 'Fees']], 
                    use_container_width=True, 
                    hide_index=True
                )
    else:
        st.info("Portfolio is empty. Add a new transaction from the sidebar.")

with tab2:
    st.subheader("Transaction History & Management")
    if not raw_df.empty:
        st.dataframe(raw_df, use_container_width=True, hide_index=True)
        st.markdown("---")
        
        col_edit, col_del = st.columns(2)
        
        with col_edit:
            st.markdown("### Edit Transaction")
            tx_ids = raw_df['id'].tolist()
            selected_edit_id = st.selectbox("Select Transaction ID to Edit", tx_ids, key="edit_sel")
            selected_row = raw_df[raw_df['id'] == selected_edit_id].iloc[0]
            
            with st.form("edit_form"):
                try:
                    init_date = datetime.strptime(selected_row['date'], "%Y-%m-%d").date()
                except Exception:
                    init_date = date.today()
                    
                e_date = st.date_input("Date", init_date)
                e_ticker = st.text_input("Ticker", selected_row['ticker']).replace(" ", "").upper()
                e_exchange = st.text_input("Exchange / Broker", selected_row['exchange']).strip()
                categories = ["Stock", "Crypto", "ETF", "Robo-Advisor"]
                e_cat_idx = categories.index(selected_row['category']) if selected_row['category'] in categories else 0
                e_category = st.selectbox("Category", categories, index=e_cat_idx)
                
                actions = ["BUY", "SELL", "DIVIDEND", "FEE", "SYNC_VALUE"]
                e_act_idx = actions.index(selected_row['action']) if selected_row['action'] in actions else 0
                e_action = st.selectbox("Action", actions, index=e_act_idx)
                
                e_qty = st.number_input("Quantity", min_value=0.0, format="%.4f", value=float(selected_row['quantity']))
                e_price = st.number_input("Price / Amount / Total Value (EUR)", min_value=0.01, format="%.2f", value=float(selected_row['price']))
                e_fee = st.number_input("Fee (EUR)", min_value=0.0, format="%.2f", value=float(selected_row['fee']) if ('fee' in selected_row and pd.notnull(selected_row['fee'])) else 0.0)
                e_ftax = st.number_input("Foreign Tax Paid (EUR)", min_value=0.0, format="%.2f", value=float(selected_row['foreign_tax']) if ('foreign_tax' in selected_row and pd.notnull(selected_row['foreign_tax'])) else 0.0)
                
                edit_submit = st.form_submit_button("Update Transaction")
                if edit_submit:
                    run_stmt('''
                        UPDATE transactions 
                        SET date=?, ticker=?, category=?, exchange=?, action=?, quantity=?, price=?, fee=?, foreign_tax=?
                        WHERE id=?
                    ''', (e_date.strftime("%Y-%m-%d"), e_ticker, e_category, e_exchange, e_action, e_qty, e_price, e_fee, e_ftax, selected_edit_id))
                    st.success(f"Transaction ID {selected_edit_id} updated successfully.")
                    st.rerun()

        with col_del:
            st.markdown("### Delete Transaction")
            selected_del_id = st.selectbox("Select Transaction ID to Delete", tx_ids, key="del_sel")
            del_row = raw_df[raw_df['id'] == selected_del_id].iloc[0]
            st.warning(f"Transaction to delete: {del_row['action']} {del_row['ticker']} ({del_row['quantity']} units @ EUR {del_row['price']}) on {del_row['date']}")
            
            if st.button("Delete Transaction", type="primary"):
                run_stmt("DELETE FROM transactions WHERE id=?", (selected_del_id,))
                st.success(f"Transaction ID {selected_del_id} deleted successfully.")
                st.rerun()
    else:
        st.info("No recorded transactions in the database.")

with tab3:
    st.subheader("Tax / E1 Declaration Helper")
    
    if not raw_df.empty:
        raw_df_copy = raw_df.copy()
        raw_df_copy['year_temp'] = pd.to_datetime(raw_df_copy['date']).dt.year
        available_years = sorted(raw_df_copy['year_temp'].unique(), reverse=True)
        
        selected_tax_year = st.selectbox("Select Tax Year", available_years)
        
        c743, c659_gains, c659_divs, f_tax, tax_details_df = get_tax_e1_data(raw_df, selected_tax_year)
        
        st.markdown(f"### Tax Summary for Year **{selected_tax_year}**")
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Code 743 (Purchases)", f"EUR {c743:,.2f}")
        m2.metric("Code 659 (Realised Gains)", f"EUR {c659_gains:,.2f}")
        m3.metric("Code 295/296 (Gross Dividends)", f"EUR {c659_divs:,.2f}")
        m4.metric("Code 029/030 (Foreign Tax Paid)", f"EUR {f_tax:,.2f}")
        
        st.markdown("---")
        st.markdown("### Transaction Breakdown for Tax Year")
        
        if not tax_details_df.empty:
            st.dataframe(tax_details_df, use_container_width=True, hide_index=True)
        else:
            st.info(f"No taxable events recorded for {selected_tax_year}.")
    else:
        st.info("No transactions available to generate tax report.")

# 7. Sidebar Form for New Transactions
st.sidebar.header("Add New Transaction")
with st.sidebar.form("add_transaction_form"):
    t_date = st.date_input("Date", date.today())
    t_ticker = st.text_input("Ticker (e.g., AAPL, VUAA.MI, REV-ROBO)").replace(" ", "").upper()
    t_exchange = st.text_input("Exchange / Broker (e.g., Binance, IBKR, Revolut)").strip()
    t_category = st.selectbox("Category", ["Stock", "Crypto", "ETF", "Robo-Advisor"])
    t_action = st.selectbox("Action", ["BUY", "SELL", "DIVIDEND", "FEE", "SYNC_VALUE"])
    t_qty = st.number_input("Quantity (for BUY/SELL)", min_value=0.0, format="%.4f", value=0.0)
    t_price = st.number_input("Price / Amount / Total Value (EUR)", min_value=0.01, format="%.2f")
    t_fee = st.number_input("Transaction Fee (EUR)", min_value=0.0, format="%.2f", value=0.0)
    t_ftax = st.number_input("Foreign Tax Paid (EUR) [For DIVIDEND]", min_value=0.0, format="%.2f", value=0.0)
    submit = st.form_submit_button("Add Transaction")
    
    if submit and t_ticker:
        run_stmt(
            "INSERT INTO transactions (date, ticker, category, exchange, action, quantity, price, fee, foreign_tax) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)", 
            (t_date.strftime("%Y-%m-%d"), t_ticker, t_category, t_exchange if t_exchange else 'Main', t_action, t_qty, t_price, t_fee, t_ftax)
        )
        st.sidebar.success("Transaction added successfully.")
        st.rerun()
