import streamlit as st
import sqlite3
import pandas as pd
import yfinance as yf
import plotly.express as px
import numpy as np
from datetime import date, datetime

# 1. Vasikes rythmiseis selidas
st.set_page_config(page_title="My Portfolio", layout="wide")
st.title("Investment Dashboard")

# 2. Synartisi gia anagnosi kai ypologismo dedomenon
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
        return df, pd.DataFrame(), 0, 0, 0

    portfolio = {}
    realised_pnl_total = 0
    total_dividends_overall = 0
    total_fees_overall = 0
    
    for index, row in df.iterrows():
        ticker = row['ticker']
        exchange = row['exchange'] if row['exchange'] else 'Main'
        action = row['action']
        qty = row['quantity'] if row['quantity'] else 0.0
        price = row['price'] if row['price'] else 0.0
        trade_fee = row['fee'] if ('fee' in row and pd.notnull(row['fee'])) else 0.0
        
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
                'Fees': 0.0
            }
            
        p = portfolio[key]
        
        if action == 'BUY':
            total_cost = (p['Qty'] * p['Avg Price']) + (qty * price) + trade_fee
            p['Qty'] += qty
            p['Avg Price'] = total_cost / p['Qty'] if p['Qty'] > 0 else 0
            p['Fees'] += trade_fee
            total_fees_overall += trade_fee
            
        elif action == 'SELL':
            net_proceeds = (qty * price) - trade_fee
            profit = net_proceeds - (qty * p['Avg Price'])
            p['Realised PnL'] += profit
            realised_pnl_total += profit
            p['Qty'] -= qty
            p['Fees'] += trade_fee
            total_fees_overall += trade_fee
            
        elif action == 'DIVIDEND':
            div_amount = price if price > 0 else (qty * price)
            p['Dividends'] += div_amount
            total_dividends_overall += div_amount
            
        elif action == 'FEE':
            fee_amount = price if price > 0 else trade_fee
            p['Fees'] += fee_amount
            total_fees_overall += fee_amount

    port_df = pd.DataFrame(list(portfolio.values()))
    if port_df.empty:
        return df, pd.DataFrame(), 0, 0, 0
        
    port_df = port_df[port_df['Qty'] > 0].copy()

    if not port_df.empty:
        unique_tickers = " ".join(port_df['Ticker'].unique().tolist())
        try:
            live_data = yf.download(unique_tickers, period="1d", group_by='ticker', progress=False)
            live_prices = {}
            for ticker in port_df['Ticker'].unique():
                try:
                    if len(port_df['Ticker'].unique()) == 1:
                        live_prices[ticker] = float(live_data['Close'].iloc[-1])
                    else:
                        live_prices[ticker] = float(live_data[ticker]['Close'].iloc[-1])
                except:
                    live_prices[ticker] = np.nan
        except Exception:
            live_prices = {ticker: np.nan for ticker in port_df['Ticker'].unique()}
            
        port_df['Live Price'] = port_df['Ticker'].map(live_prices)
        
        port_df['Current Value'] = port_df['Qty'] * port_df['Live Price']
        port_df['Invested Value'] = port_df['Qty'] * port_df['Avg Price']
        port_df['Unrealised PnL (€)'] = port_df['Current Value'] - port_df['Invested Value']
        port_df['Unrealised PnL (%)'] = ((port_df['Live Price'] - port_df['Avg Price']) / port_df['Avg Price']) * 100
        port_df = port_df.round(2)
        
    return df, port_df, realised_pnl_total, total_dividends_overall, total_fees_overall

raw_df, port_df, total_realised, total_divs, total_fees = get_portfolio_data()

# Dimiourgia Tabs gia plori diacheirisi
tab1, tab2 = st.tabs(["Dashboard", "Transaction Management"])

with tab1:
    if not port_df.empty:
        total_value = port_df['Current Value'].sum()
        total_invested = port_df['Invested Value'].sum()
        total_unrealised = port_df['Unrealised PnL (€)'].sum()
        total_unrealised_pct = (total_unrealised / total_invested) * 100 if total_invested > 0 else 0

        col1, col2, col3, col4, col5, col6 = st.columns(6)
        col1.metric("Total Value", f"€{total_value:,.2f}")
        col2.metric("Total Invested", f"€{total_invested:,.2f}")
        col3.metric("Unrealised PnL", f"€{total_unrealised:,.2f}", f"{total_unrealised_pct:.2f}%")
        col4.metric("Realised PnL", f"€{total_realised:,.2f}")
        col5.metric("Total Dividends", f"€{total_divs:,.2f}")
        col6.metric("Total Fees", f"€{total_fees:,.2f}")
        st.markdown("---")

        col_chart, col_table = st.columns([1, 2])

        with col_chart:
            st.subheader("Portfolio")
            plot_df = port_df.dropna(subset=['Current Value'])
            if not plot_df.empty and plot_df['Current Value'].sum() > 0:
                fig = px.pie(plot_df, values='Current Value', names='Ticker', hover_data=['Exchange'], hole=0.4, color_discrete_sequence=px.colors.sequential.Teal)
                fig.update_layout(margin=dict(t=0, b=0, l=0, r=0))
                st.plotly_chart(fig, use_container_width=True)
            else:
                 st.write("Insert Data for graph")

        with col_table:
            st.subheader("Asset Details")
            st.dataframe(
                port_df[['Ticker', 'Exchange', 'Category', 'Qty', 'Avg Price', 'Live Price', 'Current Value', 'Unrealised PnL (€)', 'Unrealised PnL (%)', 'Dividends', 'Fees']], 
                use_container_width=True, 
                hide_index=True
            )
    else:
        st.info("Portfolio is empty. Insert a transaction from menu on the left")

with tab2:
    st.subheader("Istoriko Synallagon & Epexergasia / Diagrafi")
    if not raw_df.empty:
        st.dataframe(raw_df, use_container_width=True, hide_index=True)
        st.markdown("---")
        
        col_edit, col_del = st.columns(2)
        
        with col_edit:
            st.markdown("### Epexergasia Synallagis")
            tx_ids = raw_df['id'].tolist()
            selected_edit_id = st.selectbox("Epile3e ID Synallagis gia Epexergasia", tx_ids, key="edit_sel")
            selected_row = raw_df[raw_df['id'] == selected_edit_id].iloc[0]
            
            with st.form("edit_form"):
                try:
                    init_date = datetime.strptime(selected_row['date'], "%Y-%m-%d").date()
                except:
                    init_date = date.today()
                    
                e_date = st.date_input("Imerominia", init_date)
                e_ticker = st.text_input("Ticker", selected_row['ticker']).upper()
                e_exchange = st.text_input("Antallaktirio", selected_row['exchange'])
                categories = ["Stock", "Crypto", "ETF"]
                e_cat_idx = categories.index(selected_row['category']) if selected_row['category'] in categories else 0
                e_category = st.selectbox("Katigoria", categories, index=e_cat_idx)
                
                actions = ["BUY", "SELL", "DIVIDEND", "FEE"]
                e_act_idx = actions.index(selected_row['action']) if selected_row['action'] in actions else 0
                e_action = st.selectbox("Energeia", actions, index=e_act_idx)
                
                e_qty = st.number_input("Posotita", min_value=0.0, format="%.4f", value=float(selected_row['quantity']))
                e_price = st.number_input("Timi / Poso (€)", min_value=0.01, format="%.2f", value=float(selected_row['price']))
                e_fee = st.number_input("Promitheia (€)", min_value=0.0, format="%.2f", value=float(selected_row['fee']) if ('fee' in selected_row and pd.notnull(selected_row['fee'])) else 0.0)
                
                edit_submit = st.form_submit_button("Enimerosi Synallagis")
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
                    st.success(f"I synallagi me ID {selected_edit_id} enimerothike.")
                    st.rerun()

        with col_del:
            st.markdown("### Diagrafi Synallagis")
            selected_del_id = st.selectbox("Epile3e ID Synallagis gia Diagrafi", tx_ids, key="del_sel")
            del_row = raw_df[raw_df['id'] == selected_del_id].iloc[0]
            st.warning(f"Synallagi pros diagrafi: {del_row['action']} {del_row['ticker']} ({del_row['quantity']} units @ €{del_row['price']}) tin {del_row['date']}")
            
            if st.button("Diagrafi Synallagis", type="primary"):
                conn = sqlite3.connect('portfolio.db')
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transactions WHERE id=?", (selected_del_id,))
                conn.commit()
                conn.close()
                st.success(f"I synallagi me ID {selected_del_id} diagrafike.")
                st.rerun()
    else:
        st.info("Den hyparchoun katachorimenes synallagies sti basi.")

# 4. Plaino Menou gia Prosthiki Neas Synallagis
st.sidebar.header("Nea Synallagi")
with st.sidebar.form("add_transaction_form"):
    t_date = st.date_input("Imerominia", date.today())
    t_ticker = st.text_input("Ticker (p.x. AAPL, VUAA.MI)").upper()
    t_exchange = st.text_input("Antallaktirio / Broker (p.x. Binance, IBKR, Revolut)").strip()
    t_category = st.selectbox("Katigoria", ["Stock", "Crypto", "ETF"])
    t_action = st.selectbox("Energeia", ["BUY", "SELL", "DIVIDEND", "FEE"])
    t_qty = st.number_input("Posotita (gia BUY/SELL)", min_value=0.0, format="%.4f", value=0.0)
    t_price = st.number_input("Timi / Poso (€)", min_value=0.01, format="%.2f")
    t_fee = st.number_input("Promitheia Synallagis (€)", min_value=0.0, format="%.2f", value=0.0)
    submit = st.form_submit_button("Prosthiki")
    
    if submit and t_ticker:
        conn = sqlite3.connect('portfolio.db')
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO transactions (date, ticker, category, exchange, action, quantity, price, fee) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
            (t_date.strftime("%Y-%m-%d"), t_ticker, t_category, t_exchange if t_exchange else 'Main', t_action, t_qty, t_price, t_fee)
        )
        conn.commit()
        conn.close()
        st.sidebar.success("I synallagi prosthethike.")
        st.rerun()