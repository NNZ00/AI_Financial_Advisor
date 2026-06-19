import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from financial_advisor.config import (
    GOOGLE_API_KEY, 
    TAVILY_API_KEY,
    LANGSMITH_API_KEY,

    WORKHORSE_MODEL, 
    STRATEGIST_MODEL, 
    workhorse_llm,
)


def check_keys():
    print("Checking environment variables...")
    checks = {
        "GOOGLE_API_KEY": GOOGLE_API_KEY,
        "TAVILY_API_KEY": TAVILY_API_KEY,
        "LANGSMITH_API_KEY": LANGSMITH_API_KEY,
    }

    all_ok = True
    
    for name, value in checks.items():
        # check for empty string or None
        if not value:
            all_ok = False

        print(f"  [{'OK' if value else 'MISSING'}] {name}")
    
    print(f"  Workhorse model:  {WORKHORSE_MODEL}")
    print(f"  Strategist model: {STRATEGIST_MODEL}")
    return all_ok


def check_llm():
    print("\nPinging the workhorse model (this confirms key + model string)...")
    resp = workhorse_llm().invoke("Reply with exactly one word: pong")
    print(f"  Model replied: {resp.content!r}")


def check_market_data():
    print("\nChecking market data (yfinance, no key needed)...")
    try:
        import yfinance as yf
        data = yf.Ticker("AAPL").history(period="1d")
        if not data.empty:
            print(f"  yfinance OK - AAPL last close: {round(float(data['Close'].iloc[-1]), 2)}")
        else:
            print("  yfinance returned no rows (possibly a temporary hiccup).")
    except Exception as e:
        print(f"  yfinance check failed: {e}")


if __name__ == "__main__":
    if check_keys():
        check_llm()
        check_market_data()
        print("\nEnvironment looks good. Ready for Stage 1.")
    else:
        print("\nSome keys are missing - fill them in .env and re-run.")
