import streamlit as st
import sqlite3
import pandas as pd
import yfinance as yf
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from datetime import date, datetime, timedelta

# 1. Page Configuration
st.set_page_config(page_title="Personal Investment Dashboard", layout="wide")
st.title("Personal Investment Dashboard")

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

# 2. Function to Load & Calculate Portfolio Data
def get_portfolio_data():
    conn = sqlite3.connect('portfolio.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            ticker TEXT,
            category TEXT,
            exchange TEXT,
            action TEXT,
            quantity REAL,
            price REAL,
            fee REAL DEFAULT 0.0
        )
    ''')
    
    cursor.execute("PRAGMA table_info(transactions)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'exchange' not in columns:
        cursor.execute("ALTER TABLE transactions ADD COLUMN exchange TEXT DEFAULT 'Main'")
        conn.commit()
    if 'fee' not in columns:
        cursor.execute("ALTER TABLE transactions ADD COLUMN fee REAL DEFAULT 0.0")
        conn.commit()
        
    df = pd.read_sql_query("SELECT * FROM transactions", conn)
    conn.close()
    
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

# 3. Function to Calculate Historical Portfolio Growth
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

raw_df, port_df, total_realised, total_divs, total_fees = get_portfolio_data()

# Navigation Tabs
tab1, tab2 = st.tabs(["Dashboard", "Transaction Management"])

with tab1:
    if not port_df.empty:
        total_value = port_df['Current Value'].sum()
        total_invested = port_df['Invested Value'].sum()
        total_unrealised = port_df['Unrealised PnL (EUR)'].sum()
        total_unrealised_pct = (total_unrealised / total_invested) * 100 if total_invested > 0 else 0.0

        col1, col2, col3 = st.columns(3)
        col1.metric("Total Value", f"EUR {total_value:,.2f}")
        col2.metric("Total Invested", f"EUR {total_invested:,.2f}")
        col3.metric("Unrealised PnL", f"EUR {total_unrealised:,.2f}", f"{total_unrealised_pct:.2f}%")
        
        st.write("") # Spacer
        
        col4, col5, col6 = st.columns(3)
        col4.metric("Realised PnL", f"EUR {total_realised:,.2f}")
        col5.metric("Total Dividends", f"EUR {total_divs:,.2f}")
        col6.metric("Total Fees", f"EUR {total_fees:,.2f}")
        st.markdown("---")

        # Collapsible Historical Portfolio Growth Chart
        with st.expander("Historical Portfolio Growth", expanded=True):
            growth_df = get_portfolio_growth_df(raw_df)
            
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
                
                edit_submit = st.form_submit_button("Update Transaction")
                if edit_submit:
                    conn = sqlite3.connect('portfolio.db')
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE transactions 
                        SET date=?, ticker=?, category=?, exchange=?, action=?, quantity=?, price=?, fee=?
                        WHERE id=?
                    ''', (e_date.strftime("%Y-%m-%d"), e_ticker, e_category, e_exchange, e_action, e_qty, e_price, e_fee, selected_edit_id))
                    conn.commit()
                    conn.close()
                    st.success(f"Transaction ID {selected_edit_id} updated successfully.")
                    st.rerun()

        with col_del:
            st.markdown("### Delete Transaction")
            selected_del_id = st.selectbox("Select Transaction ID to Delete", tx_ids, key="del_sel")
            del_row = raw_df[raw_df['id'] == selected_del_id].iloc[0]
            st.warning(f"Transaction to delete: {del_row['action']} {del_row['ticker']} ({del_row['quantity']} units @ EUR {del_row['price']}) on {del_row['date']}")
            
            if st.button("Delete Transaction", type="primary"):
                conn = sqlite3.connect('portfolio.db')
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transactions WHERE id=?", (selected_del_id,))
                conn.commit()
                conn.close()
                st.success(f"Transaction ID {selected_del_id} deleted successfully.")
                st.rerun()
    else:
        st.info("No recorded transactions in the database.")

# 4. Sidebar Form for New Transactions
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
    submit = st.form_submit_button("Add Transaction")
    
    if submit and t_ticker:
        conn = sqlite3.connect('portfolio.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (date, ticker, category, exchange, action, quantity, price, fee) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
            (t_date.strftime("%Y-%m-%d"), t_ticker, t_category, t_exchange if t_exchange else 'Main', t_action, t_qty, t_price, t_fee)
        )
        conn.commit()
        conn.close()
        st.sidebar.success("Transaction added successfully.")
        st.rerun()
