"""
Regime signal fetcher. Pulls three signals and returns a regime classification.

Usage:
    python skills/market_data/fetcher.py            # full report
    python skills/market_data/fetcher.py --json     # machine-readable output
"""
import argparse
import json
import sys
from dataclasses import dataclass, asdict
from datetime import date

import requests
import yfinance as yf


@dataclass
class SignalResult:
    vote: str  # "risk-on" | "neutral" | "risk-off"
    detail: str


@dataclass
class RegimeReport:
    date: str
    trend: SignalResult
    vix: SignalResult
    yield_curve: SignalResult
    regime: str  # "RISK-ON" | "NEUTRAL" | "RISK-OFF"
    confirmed: bool  # False = day 1 of potential change; True = confirmed
    votes: dict


def get_trend_signal() -> SignalResult:
    hist = yf.Ticker("SPY").history(period="1y")
    if len(hist) < 200:
        raise RuntimeError("Insufficient SPY history for 200-day SMA")
    price = float(hist["Close"].iloc[-1])
    sma200 = float(hist["Close"].rolling(200).mean().iloc[-1])
    vote = "risk-on" if price > sma200 else "risk-off"
    return SignalResult(
        vote=vote,
        detail=f"SPY ${price:.2f} vs 200d SMA ${sma200:.2f} -> {vote}",
    )


def get_vix_signal() -> SignalResult:
    hist = yf.Ticker("^VIX").history(period="5d")
    if hist.empty:
        raise RuntimeError("VIX data unavailable")
    level = float(hist["Close"].iloc[-1])
    if level < 20:
        vote = "risk-on"
    elif level <= 25:
        vote = "neutral"
    else:
        vote = "risk-off"
    return SignalResult(
        vote=vote,
        detail=f"VIX {level:.2f} -> {vote}",
    )


def get_yield_curve_signal() -> SignalResult:
    # FRED T10Y2Y: 10-year minus 2-year treasury spread (percentage points)
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=T10Y2Y"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()

    spread = None
    for line in reversed(resp.text.strip().splitlines()):
        parts = line.split(",")
        if len(parts) == 2 and parts[1].strip() not in (".", ""):
            spread = float(parts[1].strip())
            break

    if spread is None:
        raise RuntimeError("Could not parse yield curve data from FRED")

    if spread > 0:
        vote = "risk-on"
    elif spread >= -0.25:
        vote = "neutral"
    else:
        vote = "risk-off"

    return SignalResult(
        vote=vote,
        detail=f"10yr-2yr spread {spread:+.2f}% -> {vote}",
    )


def _majority_vote(votes: list[str]) -> str:
    counts = {"risk-on": 0, "neutral": 0, "risk-off": 0}
    for v in votes:
        counts[v] += 1
    if counts["risk-off"] >= 2:
        return "RISK-OFF"
    if counts["risk-on"] >= 2:
        return "RISK-ON"
    return "NEUTRAL"


def fetch_regime() -> RegimeReport:
    trend = get_trend_signal()
    vix = get_vix_signal()
    yc = get_yield_curve_signal()

    votes = [trend.vote, vix.vote, yc.vote]
    regime = _majority_vote(votes)

    return RegimeReport(
        date=date.today().isoformat(),
        trend=trend,
        vix=vix,
        yield_curve=yc,
        regime=regime,
        confirmed=False,  # confirmation logic lives in the routine (reads prior day's memory)
        votes={"trend": trend.vote, "vix": vix.vote, "yield_curve": yc.vote},
    )


def print_report(report: RegimeReport) -> None:
    print(f"=== REGIME REPORT {report.date} ===")
    print(f"  {report.trend.detail}")
    print(f"  {report.vix.detail}")
    print(f"  {report.yield_curve.detail}")
    print(f"  Regime: {report.regime}")
    print(f"  Confirmed: {'YES' if report.confirmed else 'NO - day 1, await tomorrow to confirm'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="Output JSON instead of human-readable")
    args = parser.parse_args()

    try:
        report = fetch_regime()
        if args.json:
            print(json.dumps(asdict(report), indent=2))
        else:
            print_report(report)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
