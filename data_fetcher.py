import requests
import streamlit as st

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None


@st.cache_data(ttl=3600)
def _fetch_with_cache(ticker_symbol: str) -> dict:
    """Internal cached helper. Raises ValueError if data is empty so Streamlit DOES NOT cache failures."""
    if yf is None:
        raise ValueError("yfinance package is missing")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    })

    stock = yf.Ticker(ticker_symbol, session=session)
    info = getattr(stock, 'info', {}) or {}

    price = info.get('currentPrice') or info.get('regularMarketPrice')
    if not price and not info.get('longName'):
        # Raising an error prevents @st.cache_data from caching an empty dictionary!
        raise ValueError(f"No valid info returned for {ticker_symbol}")

    return info


def get_raw_stock_info(ticker_symbol: str) -> dict:
    """Public function called by data_processor.py."""
    try:
        # Try cached fetch first
        return _fetch_with_cache(ticker_symbol)
    except Exception:
        # Direct fallback attempt if cached attempt raised ValueError
        try:
            stock = yf.Ticker(ticker_symbol)
            info = stock.info or {}
            if info.get('currentPrice') or info.get('regularMarketPrice') or info.get('longName'):
                return info
        except Exception:
            pass
        return {}


if __name__ == "__main__":
    ticker = "AAPL"
    data = get_raw_stock_info(ticker)
    print(f"Company: {data.get('longName')}")
    print(f"Price: ${data.get('currentPrice') or data.get('regularMarketPrice')}")