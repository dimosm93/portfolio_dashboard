import requests
import streamlit as st

try:
    import yfinance as yf
except ImportError:  # pragma: no cover - handled at runtime if dependency is missing
    yf = None


@st.cache_data(ttl=3600)
def get_raw_stock_info(ticker_symbol: str) -> dict:
    if yf is None:
        print("⚠️ Warning: 'yfinance' is not installed. Please install it with: pip install yfinance")
        return {}

    try:
        # Create a session with a standard browser User-Agent to avoid Yahoo Cloud block
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        })

        stock = yf.Ticker(ticker_symbol, session=session)
        info = stock.info if hasattr(stock, 'info') else {}

        if not info:
            return {}

        price = info.get('currentPrice') or info.get('regularMarketPrice')

        if not price and not info.get('longName'):
            print(f"⚠️ Warning: No valid data found for stock '{ticker_symbol}'.")
            return {}

        return info
    except Exception as e:
        print(f"Error fetching data for {ticker_symbol}: {e}")
        return {}


if __name__ == "__main__":
    # Test our function with Apple
    ticker = "AAPL"
    data = get_raw_stock_info(ticker)

    # Print target keys
    print(f"Company: {data.get('longName')}")
    print(f"Price: ${data.get('currentPrice') or data.get('regularMarketPrice')}")
    print(f"Trailing P/E: {data.get('trailingPE')}")
    print(f"PEG Ratio: {data.get('pegRatio')}")
    print(f"EV/EBITDA: {data.get('enterpriseToEbitda')}")