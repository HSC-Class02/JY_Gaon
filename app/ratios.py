from __future__ import annotations
import math

def div(a,b):
    if a is None or b in (None,0): return None
    return a/b

def pct(a,b):
    x=div(a,b)
    return x*100 if x is not None else None

def avg(a,b):
    vals=[x for x in (a,b) if x is not None]
    return sum(vals)/len(vals) if len(vals)==2 else None

def calculate(m, prev=None):
    prev = prev or {}
    out = dict(m)
    out["gross_margin"] = pct(m.get("gross_profit"), m.get("revenue"))
    out["operating_margin"] = pct(m.get("operating_income"), m.get("revenue"))
    out["net_margin"] = pct(m.get("net_income"), m.get("revenue"))
    out["ebitda_margin"] = pct(m.get("ebitda"), m.get("revenue"))

    avg_assets = avg(m.get("total_assets"), prev.get("total_assets"))
    avg_equity = avg(m.get("equity"), prev.get("equity"))
    out["roa"] = pct(m.get("net_income"), avg_assets)
    out["roe"] = pct(m.get("controlling_net_income") or m.get("net_income"), avg_equity)

    # Operating-profit proxy for NOPAT. WACC is intentionally not estimated automatically.
    tax_rate = None
    if m.get("pretax_income") and m.get("net_income") is not None:
        tax_rate = 1 - div(m["net_income"], m["pretax_income"])
        if tax_rate < 0 or tax_rate > 1: tax_rate = None
    nopat = m.get("operating_income") * (1-tax_rate) if m.get("operating_income") is not None and tax_rate is not None else None
    invested_capital = None
    if m.get("interest_bearing_debt") is not None and m.get("equity") is not None and m.get("cash") is not None:
        invested_capital = m["interest_bearing_debt"] + m["equity"] - m["cash"]
    out["nopat"] = nopat
    out["invested_capital"] = invested_capital
    out["roic"] = pct(nopat, avg(invested_capital, prev.get("invested_capital")))

    if m.get("fcf") is None and m.get("cfo") is not None and m.get("capex") is not None:
        out["fcf"] = m["cfo"] - m["capex"]
    out["current_ratio"] = pct(m.get("current_assets"), m.get("current_liabilities"))
    # Current assets less inventory as a practical quick-asset proxy.
    quick_assets = None
    if m.get("current_assets") is not None and m.get("inventory") is not None:
        quick_assets = m["current_assets"] - m["inventory"]
    out["quick_ratio"] = pct(quick_assets, m.get("current_liabilities"))
    out["debt_ratio"] = pct(m.get("total_liabilities"), m.get("equity"))
    out["equity_ratio"] = pct(m.get("equity"), m.get("total_assets"))
    out["debt_dependency"] = pct(m.get("interest_bearing_debt"), m.get("total_assets"))
    out["interest_coverage"] = div(m.get("operating_income"), abs(m.get("interest_expense")) if m.get("interest_expense") is not None else None)
    out["net_debt_ebitda"] = div(m.get("net_debt"), m.get("ebitda"))

    out["asset_turnover"] = div(m.get("revenue"), avg_assets)
    out["revenue_growth"] = pct(m.get("revenue") - prev.get("revenue"), prev.get("revenue")) if prev.get("revenue") not in (None,0) else None

    ar_avg = avg(m.get("receivables"), prev.get("receivables"))
    inv_avg = avg(m.get("inventory"), prev.get("inventory"))
    # Approximate turnover denominators: revenue for AR, COGS for inventory.
    cogs = None
    if m.get("revenue") is not None and m.get("gross_profit") is not None:
        cogs = m["revenue"] - m["gross_profit"]
    ar_turn = div(m.get("revenue"), ar_avg)
    inv_turn = div(cogs, inv_avg)
    out["dso"] = div(365, ar_turn)
    out["dio"] = div(365, inv_turn)

    # DPO requires credit purchases, which is not consistently available from the main statements.
    out["dpo"] = None
    out["ccc"] = None
    if out["dso"] is not None and out["dio"] is not None and out["dpo"] is not None:
        out["ccc"] = out["dso"] + out["dio"] - out["dpo"]

    out["cfo_net_income"] = div(m.get("cfo"), m.get("net_income"))
    return out
