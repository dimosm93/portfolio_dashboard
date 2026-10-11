import yfinance as yf

def get_raw_stock_info(ticker_symbol: str) -> dict:
    stock = yf.Ticker(ticker_symbol)
    info = stock.info
    
    # check stock for real value
    price = info.get('currentPrice') or info.get('regularMarketPrice')
    
    if not price and not info.get('longName'):
        print(f"⚠️ Warning: No valid data found for stock '{ticker_symbol}'.")
        return {}
        
    return info

if __name__ == "__main__":
    # Test our function with Apple
    ticker = "σκατα"
    data = get_raw_stock_info(ticker)
    
    # Print target keys
    print(f"Company: {data.get('longName')}")
    print(f"Price: ${data.get('currentPrice') or data.get('regularMarketPrice')}")
    print(f"Trailing P/E: {data.get('trailingPE')}")
    print(f"PEG Ratio: {data.get('pegRatio')}")
    print(f"EV/EBITDA: {data.get('enterpriseToEbitda')}")