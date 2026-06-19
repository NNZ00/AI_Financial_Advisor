"""
Market-data tool (yfinance) for the Researcher agent.

Resolves a ticker robustly across exchanges. Hardened to handle unavailability.
"""
import logging

import yfinance as yf
from langchain_core.tools import tool

# yfinance logs the expected 404s loudly while we probe symbols — quiet it down.
logging.getLogger("yfinance").setLevel(logging.CRITICAL)

# Common Yahoo exchange suffixes, tried when a bare symbol doesn't resolve.
_EXCHANGE_SUFFIXES = (".DE", ".MI", ".AS", ".L", ".PA", ".SW")


def _resolve_history(ticker: str):
    """Return (resolved_symbol, 1y history) or (None, None) if nothing resolves.

    Each candidate fetch is guarded, so a transient error on one symbol doesn't
    abort the probe — we just move on to the next candidate.
    """
    base = ticker.strip().upper()
    candidates = [base]
    if "." not in base:  # only probe suffixes for unqualified symbols
        candidates += [base + suffix for suffix in _EXCHANGE_SUFFIXES]

    for symbol in candidates:
        try:
            history = yf.Ticker(symbol).history(period="1y")
        except Exception:
            continue   # transient/network error on this symbol — try the next
        if not history.empty:
            return symbol, history
    return None, None


@tool
def get_market_data(ticker: str) -> str:
    """Fetch recent market data for a stock or ETF ticker."""
    
    try:
        symbol, history = _resolve_history(ticker)
        if history is None:
            return (
                f"No data found for '{ticker}'. The symbol may be wrong, or the data "
                f"service may be momentarily unavailable. Try a Yahoo Finance symbol "
                f"with an exchange suffix (e.g. 'VWCE.DE') or a broad US-listed ETF "
                f"(e.g. 'VT', 'VOO', 'AGG'), or proceed with the instruments you have."
            )

        close = history["Close"].dropna()
        if len(close) < 2:
            return f"Only sparse data available for '{symbol}'; not enough history to summarize reliably."

        last_price = float(close.iloc[-1])
        one_year_return = (last_price / float(close.iloc[0]) - 1) * 100
        annual_vol = float(close.pct_change().dropna().std() * (252 ** 0.5) * 100)

        return (
            f"{symbol}: last price {last_price:.2f}, "
            f"1y return {one_year_return:+.1f}%, "
            f"annualized volatility {annual_vol:.1f}%."
        )
    except Exception as exc:
        # Fail closed: hand the agent a clean observation, never an exception.
        return (
            f"Market data for '{ticker}' is temporarily unavailable ({type(exc).__name__}). "
            "Proceed with other instruments or your general knowledge; do not retry repeatedly."
        )
