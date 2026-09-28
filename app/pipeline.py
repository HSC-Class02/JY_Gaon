from __future__ import annotations
import csv, io, json, os, re, zipfile
from datetime import date
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd

from .dart_client import DartClient, REPORT_CODES, extract_metrics
from .ratios import calculate

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
REPORTS = ROOT / "reports"
CFG = json.loads((ROOT/"config.json").read_text(encoding="utf-8"))
DATA.mkdir(exist_ok=True); (REPORTS/"raw").mkdir(parents=True, exist_ok=True); (REPORTS/"metadata").mkdir(parents=True, exist_ok=True)

BASE_COLUMNS = [
    "year","period","report_code","report_name","fs_div","rcept_no","rcept_dt",
    "source_url",
    "total_assets","cash","receivables","inventory","ppe","current_assets","current_liabilities",
    "total_liabilities","equity","revenue","gross_profit","sga","operating_income","pretax_income",
    "net_income","controlling_net_income","interest_bearing_debt","interest_expense",
    "depreciation","amortization","ebitda","cfo","cfi","cff","capex","fcf","net_debt",
    "gross_margin","operating_margin","net_margin","ebitda_margin","roa","roe","roic",
    "current_ratio","quick_ratio","debt_ratio","equity_ratio","debt_dependency",
    "interest_coverage","net_debt_ebitda","asset_turnover","dso","dio","dpo","ccc",
    "revenue_growth","cfo_net_income"
]

def report_name(code):
    return {"11011":"사업보고서","11012":"반기보고서","11013":"1분기보고서","11014":"3분기보고서"}.get(code, code)

def is_target(r):
    name = str(r.get("report_nm",""))
    return any(x in name for x in ["사업보고서","반기보고서","분기보고서"])

def discover(client, year):
    # Filing date can differ from fiscal year; search the entire calendar year.
    return client.filings(CFG["corp_code"], f"{year}0101", f"{year}1231").get("list", [])

def save_json(path, obj):
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)

def legacy_extract(zip_bytes):
    """Best-effort extraction for pre-2015 DART document archives.
    It deliberately keeps the result marked as legacy/unverified instead of
    silently mixing it with OpenDART XBRL values.
    """
    rows=[]
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
            names=[n for n in z.namelist() if n.lower().endswith((".xml",".html",".htm"))]
            for n in names:
                raw=z.read(n)
                text=raw.decode("utf-8", errors="ignore")
                soup=BeautifulSoup(text,"lxml")
                for table in soup.find_all("table"):
                    try:
                        df=pd.read_html(io.StringIO(str(table)))[0]
                    except Exception:
                        continue
                    if df.shape[0] == 0: continue
                    for _, rr in df.iterrows():
                        vals=[str(x) for x in rr.tolist()]
                        joined=" | ".join(vals)
                        if re.search(r"매출|영업이익|당기순이익|자산총계|부채총계|자본총계", joined):
                            rows.append({"file":n,"row":vals})
    except zipfile.BadZipFile:
        return []
    return rows


def legacy_metrics_from_rows(extracted):
    vals={}
    patterns={
      "revenue": [r"^매출액$", r"수익.*매출", r"revenue"],
      "operating_income":[r"영업이익",r"operatingincome"],
      "net_income":[r"당기순이익",r"순이익",r"netincome"],
      "total_assets":[r"자산총계",r"assets"],
      "current_assets":[r"유동자산"],
      "total_liabilities":[r"부채총계",r"liabilities"],
      "current_liabilities":[r"유동부채"],
      "equity":[r"자본총계",r"equity"],
      "cash":[r"현금및현금성자산",r"현금.*단기예금",r"cash"],
      "receivables":[r"매출채권",r"accountsreceivable"],
      "inventory":[r"재고자산",r"inventories"],
      "ppe":[r"유형자산",r"property"],
      "gross_profit":[r"매출총이익"],
      "cfo":[r"영업활동.*현금흐름",r"영업활동으로인한현금"],
      "cfi":[r"투자활동.*현금흐름",r"투자활동으로인한현금"],
      "cff":[r"재무활동.*현금흐름",r"재무활동으로인한현금"],
    }
    for item in extracted:
        row=item.get("row",[])
        text=" ".join(row)
        for key,pats in patterns.items():
            if key in vals: continue
            if any(re.search(p, re.sub(r"\s+","",str(row[0] if row else "")), re.I) or re.search(p,re.sub(r"\s+","",text),re.I) for p in pats):
                nums=[]
                for cell in row[1:]:
                    raw=str(cell).replace(",","").replace(" ","")
                    m=re.search(r"[-+]?\d+(?:\.\d+)?",raw)
                    if m:
                        try: nums.append(float(m.group()))
                        except: pass
                if nums:
                    vals[key]=nums[0]
    if vals.get("operating_income") is not None:
        vals["ebitda"]=vals["operating_income"]
    if vals.get("cfo") is not None:
        vals["fcf"]=vals["cfo"]
    if vals.get("cash") is not None and vals.get("total_liabilities") is not None:
        pass
    return vals

def build_period_rows(api_rows, year, code, rcept_no, rcept_dt):
    # Filter to actual accounts; DART may include multiple comparative columns.
    metrics = extract_metrics(api_rows)
    row = {"year": year, "period": {"11011":"annual","11012":"half_year","11013":"quarterly_q1","11014":"quarterly_q3"}[code],
           "report_code": code, "report_name": report_name(code), "fs_div": CFG["fs_div"],
           "rcept_no": rcept_no, "rcept_dt": rcept_dt,
           "source_url": f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcept_no}"}
    row.update(metrics)
    return row

def make_quarters(raw):
    # raw = report rows for the same fiscal year. Flows are derived from cumulative reports.
    out=[]
    for y, g in raw.groupby("year"):
        g=g.sort_values("period")
        lookup={r["period"]:r for r in g.to_dict("records")}
        annual=lookup.get("annual"); h1=lookup.get("half_year"); q1=lookup.get("quarterly_q1"); q3=lookup.get("quarterly_q3")
        if not annual: continue
        def derive(label, base, sub):
            if not base: return None
            r=dict(base); r["period"]=label; r["report_name"]=f"{label} (derived)"
            flow_cols=["revenue","gross_profit","sga","operating_income","pretax_income","net_income",
                       "controlling_net_income","interest_expense","depreciation","amortization",
                       "cfo","cfi","cff","capex","fcf"]
            if sub:
                for c in flow_cols:
                    if base.get(c) is not None and sub.get(c) is not None:
                        r[c]=base[c]-sub[c]
            # Balance-sheet values remain the period-end balance from the base report.
            # Recalculate EBITDA and net debt.
            if r.get("operating_income") is not None:
                r["ebitda"]=r["operating_income"]+(r.get("depreciation") or 0)+(r.get("amortization") or 0)
            if r.get("interest_bearing_debt") is not None and r.get("cash") is not None:
                r["net_debt"]=r["interest_bearing_debt"]-r["cash"]
            return r
        q1r=derive("Q1", q1, None) if q1 else None
        q2r=derive("Q2", h1, q1) if h1 and q1 else None
        q3r=derive("Q3", q3, h1) if q3 and h1 else None
        q4r=derive("Q4", annual, q3) if q3 else None
        prev=None
        for r in [q1r,q2r,q3r,q4r]:
            if r:
                rr=calculate(r, prev)
                out.append(rr); prev=r
    return out

def run():
    api_key=os.getenv("DART_API_KEY")
    client=DartClient(api_key)
    start=int(CFG["start_year"]); end=date.today().year
    raw=[]
    legacy_raw=[]
    filing_meta=[]
    for year in range(start,end+1):
        filings=discover(client, year)
        targets=[x for x in filings if is_target(x)]
        for f in targets:
            filing_meta.append(f)
        for code in REPORT_CODES.values():
            if year < 2015:
                continue
            try:
                data=client.financials(CFG["corp_code"], year, code, CFG["fs_div"])
                rows=data.get("list",[])
                if not rows: continue
                # Find receipt number/date from filing search, if available.
                matches=[x for x in targets if code in {"11011","11012","11013","11014"} and
                         ((code=="11011" and "사업보고서" in x.get("report_nm","")) or
                          (code=="11012" and "반기보고서" in x.get("report_nm","")) or
                          (code=="11013" and "분기보고서" in x.get("report_nm","") and "1분기" in x.get("report_nm","")) or
                          (code=="11014" and "분기보고서" in x.get("report_nm","") and "3분기" in x.get("report_nm","")))]
                f=matches[-1] if matches else {}
                raw.append(build_period_rows(rows, year, code, f.get("rcept_no",""), f.get("rcept_dt","")))
                save_json(REPORTS/"metadata"/f"{year}_{code}.json", data)
            except Exception as e:
                # A report may not exist yet or may be unavailable. Preserve the error in metadata.
                save_json(REPORTS/"metadata"/f"{year}_{code}_error.json", {"year":year,"report_code":code,"error":str(e)})
        # Archive report documents for 2010-2014 (and metadata for later years).
        for f in targets:
            rc=f.get("rcept_no")
            if not rc: continue
            target=REPORTS/"raw"/f"{rc}.zip"
            if not target.exists():
                try:
                    target.write_bytes(client.document(rc))
                except Exception as e:
                    save_json(REPORTS/"metadata"/f"{rc}_document_error.json", {"error":str(e),"filing":f})
                else:
                    legacy=legacy_extract(target.read_bytes())
                    if legacy:
                        save_json(REPORTS/"metadata"/f"{rc}_legacy_extract.json", legacy)
                        if year < 2015:
                            code = "11011" if "사업보고서" in f.get("report_nm","") else ("11012" if "반기보고서" in f.get("report_nm","") else ("11013" if "1분기" in f.get("report_nm","") else "11014"))
                            lm=legacy_metrics_from_rows(legacy)
                            if lm:
                                rr={"year":year,"period":{"11011":"annual","11012":"half_year","11013":"quarterly_q1","11014":"quarterly_q3"}[code],
                                    "report_code":code,"report_name":report_name(code)+" (legacy)","fs_div":"LEGACY",
                                    "rcept_no":rc,"rcept_dt":f.get("rcept_dt",""),
                                    "source_url":f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rc}"}
                                rr.update(lm); legacy_raw.append(rr)

    if legacy_raw:
        ldf=pd.DataFrame(legacy_raw)
        for c in BASE_COLUMNS:
            if c not in ldf.columns: ldf[c]=None
        ldf[BASE_COLUMNS].to_csv(DATA/"legacy_2010_2014.csv",index=False,encoding="utf-8-sig")
    df=pd.DataFrame(raw)
    if df.empty:
        raise RuntimeError("No OpenDART financial data was collected. Check DART_API_KEY and API access.")
    prev_by_year={}
    enriched=[]
    for _, r in df.sort_values(["year","period"]).iterrows():
        d=r.to_dict()
        prev=prev_by_year.get(d["year"]-1,{})
        enriched.append(calculate(d,prev))
        prev_by_year[d["year"]]=d
    df=pd.DataFrame(enriched)
    for c in BASE_COLUMNS:
        if c not in df.columns: df[c]=None
    df=df[BASE_COLUMNS]
    df.to_csv(DATA/"raw_periods.csv",index=False,encoding="utf-8-sig")

    annual=df[df.period=="annual"].copy()
    half=df[df.period=="half_year"].copy()
    quarters=pd.DataFrame(make_quarters(df))
    for out, dest in [(annual,"annual.csv"),(half,"half_year.csv"),(quarters,"quarterly.csv")]:
        if not out.empty:
            for c in BASE_COLUMNS:
                if c not in out.columns: out[c]=None
            out[BASE_COLUMNS].to_csv(DATA/dest,index=False,encoding="utf-8-sig")
    save_json(REPORTS/"filings.json", filing_meta)
    print(f"Collected {len(df)} report periods; annual={len(annual)}, half={len(half)}, quarterly={len(quarters)}")

if __name__ == "__main__":
    run()
