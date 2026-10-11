import pandas as pd
from data_fetcher import get_raw_stock_info

# List of sectors that traditionally command higher growth multiples
GROWTH_SECTORS = ["Technology", "Healthcare", "Communication Services", "Consumer Cyclical"]

def get_sector_adjusted_valuation(pe_ratio: float, peg_ratio: float, ev_ebitda: float, sector: str) -> str:
    """
    Evaluates stock valuation using multi-factor metrics (PEG, P/E, EV/EBITDA)
    adjusted dynamically according to the stock's sector benchmarks.
    """
    # Check if at least one metric exists
    if pe_ratio is None and peg_ratio is None and ev_ebitda is None:
        return "N/A ⚪"

    # Define sector-adjusted thresholds
    is_growth = sector in GROWTH_SECTORS
    pe_low = 25.0 if is_growth else 15.0
    pe_high = 40.0 if is_growth else 25.0
    ev_low = 18.0 if is_growth else 12.0
    ev_high = 28.0 if is_growth else 20.0

    # 1. Undervalued Condition (Attractive multiples relative to sector)
    if (peg_ratio is not None and peg_ratio < 1.0) and (ev_ebitda is None or ev_ebitda < ev_low):
        return "Undervalued 🟢"
    if (peg_ratio is None and pe_ratio is not None and pe_ratio < pe_low) and (ev_ebitda is None or ev_ebitda < ev_low):
        return "Undervalued 🟢"

    # 2. Overvalued Condition (High multiples relative to sector)
    if (peg_ratio is not None and peg_ratio > 2.0) or (pe_ratio is not None and pe_ratio > pe_high) or (ev_ebitda is not None and ev_ebitda > ev_high):
        return "Overvalued 🔴"

    # 3. Fair Value (Balanced for sector context)
    return "Fair Value 🟡"


def clean_stock_data(raw_info: dict) -> dict:
    """
    Cleans and transforms raw financial data from yfinance into a 
    standardized dictionary containing metrics and sector-adjusted valuation ratings.
    """
    if not raw_info:
        return {}

    pe = raw_info.get('trailingPE')
    peg = raw_info.get('pegRatio')
    ev_ebitda = raw_info.get('enterpriseToEbitda')
    sector = raw_info.get('sector', 'N/A')

    cleaned_data = {
        'symbol': raw_info.get('symbol'),
        'name': raw_info.get('longName') or raw_info.get('shortName') or 'N/A',
        'price': raw_info.get('currentPrice') or raw_info.get('regularMarketPrice'),
        'valuation_rating': get_sector_adjusted_valuation(pe, peg, ev_ebitda, sector),
        'pe_ratio': pe,
        'peg_ratio': peg,
        'ev_ebitda': ev_ebitda,
        'sector': sector,
        'market_cap': raw_info.get('marketCap')
    }

    return cleaned_data


def create_stock_dataframe(tickers: list) -> pd.DataFrame:
    """
    Fetches, cleans, and consolidates financial data for multiple tickers
    into a structured Pandas DataFrame.
    """
    processed_list = []
    
    for symbol in tickers:
        cleaned_data = clean_stock_data(get_raw_stock_info(symbol))
        
        if cleaned_data:
            processed_list.append(cleaned_data)
            
    df = pd.DataFrame(processed_list)
    return df


if __name__ == "__main__":
    # Test multi-stock processing with sector-adjusted multi-factor logic
    test_tickers = ["AAPL", "MSFT", "NVDA", "INVALID_TICKER"]
    print(f"--- Fetching & Building DataFrame for: {test_tickers} ---")
    
    df_stocks = create_stock_dataframe(test_tickers)
    
    print("\nResulting DataFrame:")
    print(df_stocks.to_string())