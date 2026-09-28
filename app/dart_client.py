from __future__ import annotations
import io, json, os, re, zipfile
from pathlib import Path
from typing import Any
import requests

BASE = "https://opendart.fss.or.kr/api"
TIMEOUT = 30

REPORT_CODES = {
    "annual": "11011",
    "half_year": "11012",
    "quarterly_q1": "11013",
    "quarterly_q3": "11014",
}

class DartAPIError(RuntimeError):
    pass

class DartClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise DartAPIError("DART_API_KEY is not set.")
        self.api_key = api_key

    def get_json(self, endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
        p = {"crtfc_key": self.api_key, **params}
        r = requests.get(f"{BASE}/{endpoint}", params=p, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if str(data.get("status")) != "000":
            raise DartAPIError(f"DART {data.get('status')}: {data.get('message')}")
        return data

    def financials(self, corp_code: str, year: int, reprt_code: str, fs_div: str = "CFS"):
        return self.get_json(
            "fnlttSinglAcntAll.json",
            {"corp_code": corp_code, "bsns_year": str(year),
             "reprt_code": reprt_code, "fs_div": fs_div},
        )

    def filings(self, corp_code: str, bgn_de: str, end_de: str, page_no: int = 1):
        return self.get_json(
            "list.json",
            {"corp_code": corp_code, "bgn_de": bgn_de, "end_de": end_de,
             "pblntf_ty": "A", "last_reprt_at": "Y", "sort": "date", "sort_mth": "asc",
             "page_no": str(page_no), "page_count": "100"},
        )

    def document(self, rcept_no: str) -> bytes:
        p = {"crtfc_key": self.api_key, "rcept_no": rcept_no}
        r = requests.get(f"{BASE}/document.xml", params=p, timeout=60)
        r.raise_for_status()
        return r.content

def _num(x):
    if x is None or x == "":
        return None
    try:
        return float(str(x).replace(",", "").strip())
    except Exception:
        return None

def clean_account_name(name: str) -> str:
    return re.sub(r"\s+", "", str(name or "")).lower()

def pick(rows, patterns, sj=None, prefer_ids=()):
    candidates = []
    for row in rows:
        if sj and row.get("sj_div") != sj:
            continue
        text = clean_account_name(row.get("account_nm"))
        aid = clean_account_name(row.get("account_id"))
        score = 0
        for pat in patterns:
            if re.search(pat, text):
                score += 10
            if re.search(pat, aid):
                score += 3
        if score:
            if aid in [clean_account_name(x) for x in prefer_ids]:
                score += 20
            val = _num(row.get("thstrm_amount"))
            if val is not None:
                candidates.append((score, len(text), row, val))
    if not candidates:
        return None
    candidates.sort(key=lambda x: (-x[0], x[1]))
    return candidates[0][3]

def extract_metrics(rows):
    # DART amounts are KRW million in the API. Preserve the source unit.
    m = {}
    m["total_assets"] = pick(rows, [r"^자산총계$", r"assets$"], "BS",
                             ["ifrs-full_Assets"])
    m["cash"] = pick(rows, [r"현금및현금성자산", r"cashandcashequivalents"], "BS")
    m["receivables"] = pick(rows, [r"매출채권", r"tradeandothercurrentreceivables"], "BS")
    m["inventory"] = pick(rows, [r"재고자산", r"inventories"], "BS")
    m["ppe"] = pick(rows, [r"유형자산", r"propertyplantandequipment"], "BS")
    m["current_assets"] = pick(rows, [r"유동자산", r"currentassets"], "BS")
    m["current_liabilities"] = pick(rows, [r"유동부채", r"currentliabilities"], "BS")
    m["total_liabilities"] = pick(rows, [r"부채총계", r"liabilities"], "BS")
    m["equity"] = pick(rows, [r"자본총계", r"equity"], "BS")

    m["revenue"] = pick(rows, [r"매출액", r"수익\(매출액\)", r"revenue$"], "IS")
    m["gross_profit"] = pick(rows, [r"매출총이익", r"grossprofit"], "IS")
    m["sga"] = pick(rows, [r"판매비와관리비", r"sellinggeneraladministrativeexpense"], "IS")
    m["operating_income"] = pick(rows, [r"영업이익", r"operatingincome"], "IS")
    m["pretax_income"] = pick(rows, [r"법인세비용차감전순이익", r"세전이익", r"profitlossbeforetax"], "IS")
    m["interest_expense"] = pick(rows, [r"이자비용", r"금융비용", r"interestexpense"], "IS")
    m["net_income"] = pick(rows, [r"당기순이익", r"profitloss$"], "IS")
    m["controlling_net_income"] = pick(rows, [r"지배기업의소유주에게귀속되는당기순이익",
                                               r"지배주주", r"profitlossattributabletoownersofparent"], "IS")
    m["depreciation"] = pick(rows, [r"감가상각비", r"depreciation"], "CF")
    m["amortization"] = pick(rows, [r"무형자산상각비", r"amortization"], "CF")
    m["cfo"] = pick(rows, [r"영업활동으로인한현금흐름", r"netcashprovidedbyusedinoperatingactivities"], "CF")
    m["cfi"] = pick(rows, [r"투자활동으로인한현금흐름", r"netcashprovidedbyusedininvestingactivities"], "CF")
    m["cff"] = pick(rows, [r"재무활동으로인한현금흐름", r"netcashprovidedbyusedinfinancingactivities"], "CF")

    debt_patterns = [
        r"단기차입금", r"장기차입금", r"유동성장기차입금",
        r"사채", r"차입금", r"shorttermborrowings",
        r"longtermborrowings", r"currentportionoflongterm"
    ]
    debt_values = []
    for row in rows:
        if row.get("sj_div") != "BS":
            continue
        nm = clean_account_name(row.get("account_nm"))
        aid = clean_account_name(row.get("account_id"))
        if any(re.search(p, nm) or re.search(p, aid) for p in debt_patterns):
            v = _num(row.get("thstrm_amount"))
            if v is not None:
                debt_values.append(v)
    m["interest_bearing_debt"] = sum(debt_values) if debt_values else None
    m["capex"] = None
    capex_parts = []
    for row in rows:
        if row.get("sj_div") != "CF":
            continue
        nm = clean_account_name(row.get("account_nm"))
        if re.search(r"유형자산의취득|무형자산의취득|propertyplantandequipment.*acquisition|intangible.*acquisition", nm):
            v = _num(row.get("thstrm_amount"))
            if v is not None:
                capex_parts.append(abs(v))
    if capex_parts:
        m["capex"] = sum(capex_parts)
    if m["capex"] is not None and m["cfo"] is not None:
        m["fcf"] = m["cfo"] - m["capex"]
    else:
        m["fcf"] = None
    if m["interest_bearing_debt"] is not None and m["cash"] is not None:
        m["net_debt"] = m["interest_bearing_debt"] - m["cash"]
    else:
        m["net_debt"] = None
    if m["operating_income"] is not None:
        m["ebitda"] = m["operating_income"] + (m["depreciation"] or 0) + (m["amortization"] or 0)
    else:
        m["ebitda"] = None
    return m
