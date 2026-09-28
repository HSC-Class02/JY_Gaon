from pathlib import Path
import json, html
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DATA=ROOT/"data"; OUT=ROOT/"dashboard"
OUT.mkdir(exist_ok=True)

metric_labels={
 "revenue":"매출액","operating_income":"영업이익","net_income":"당기순이익",
 "total_assets":"총자산","total_liabilities":"총부채","equity":"자본총계",
 "cash":"현금및현금성자산","interest_bearing_debt":"이자부차입금","net_debt":"순차입금",
 "cfo":"영업활동현금흐름","capex":"CAPEX","fcf":"FCF",
 "operating_margin":"영업이익률","net_margin":"순이익률","gross_margin":"매출총이익률",
 "roa":"ROA","roe":"ROE","roic":"ROIC","current_ratio":"유동비율","quick_ratio":"당좌비율",
 "debt_ratio":"부채비율","equity_ratio":"자기자본비율","debt_dependency":"차입금의존도",
 "interest_coverage":"이자보상배율","net_debt_ebitda":"순차입금/EBITDA","asset_turnover":"총자산회전율",
 "dso":"DSO","dio":"DIO","dpo":"DPO","ccc":"CCC","revenue_growth":"매출증가율",
 "cfo_net_income":"CFO/순이익"
}
amount_cols={"revenue","operating_income","net_income","total_assets","total_liabilities","equity","cash",
             "interest_bearing_debt","net_debt","cfo","capex","fcf","gross_profit","sga","pretax_income","ppe","receivables","inventory"}
pct_cols={"gross_margin","operating_margin","net_margin","ebitda_margin","roa","roe","roic","current_ratio","quick_ratio",
          "debt_ratio","equity_ratio","debt_dependency","revenue_growth"}
def load(name):
    p=DATA/name
    if not p.exists(): return pd.DataFrame()
    return pd.read_csv(p)

annual=load("annual.csv"); half=load("half_year.csv"); quarterly=load("quarterly.csv")
latest=(annual.sort_values("year").iloc[-1].to_dict() if not annual.empty else {})
def jsdf(df):
    if df.empty: return []
    return df.replace({float("nan"):None}).to_dict(orient="records")

def fmt(v, key):
    if v is None or pd.isna(v): return "—"
    try:
        if key in amount_cols: return f"{float(v):,.0f}"
        if key in pct_cols: return f"{float(v):,.1f}%"
        return f"{float(v):,.2f}"
    except: return str(v)

def table(df, title, columns):
    if df.empty:
        return f'<section><h2>{title}</h2><div class="empty">아직 수집된 데이터가 없습니다. GitHub Actions에서 DART API 수집을 실행하세요.</div></section>'
    head="".join(f"<th>{html.escape(metric_labels.get(c,c))}</th>" for c in columns)
    body=[]
    for _,r in df.sort_values(["year"], ascending=False).iterrows():
        cells=[f"<td>{html.escape(str(r.get('year','')))}</td>"]
        for c in columns[1:]:
            cells.append(f"<td>{fmt(r.get(c),c)}</td>")
        body.append("<tr>"+ "".join(cells)+"</tr>")
    return f'<section><h2>{title}</h2><div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div></section>'

annual_cols=["year","revenue","operating_income","net_income","total_assets","total_liabilities","equity",
             "cfo","capex","fcf","operating_margin","net_margin","roa","roe","debt_ratio","current_ratio"]
half_cols=["year","revenue","operating_income","net_income","cfo","capex","fcf","operating_margin","net_margin","current_ratio","debt_ratio"]
quarter_cols=["year","period","revenue","operating_income","net_income","cfo","fcf","operating_margin","net_margin"]

peer_rows=[
("LS전선","비상장","전력·산업용 전선"),
("대한전선","001440","전력·산업용 전선"),
("일진전기","103590","전선 및 전력기기"),
("LS에코에너지","229640","전선·케이블"),
("대원전선","006340","전선 제조"),
("KBI메탈","024840","전선/전장 관련"),
]
peer_html="".join(f"<tr><td>{a}</td><td>{b}</td><td>{c}</td></tr>" for a,b,c in peer_rows)

payload={"annual":jsdf(annual),"half_year":jsdf(half),"quarterly":jsdf(quarterly)}
data_json=json.dumps(payload,ensure_ascii=False).replace("</","<\\/")
latest_cards=""
for key in ["revenue","operating_income","net_income","cfo","operating_margin","roe","debt_ratio","current_ratio"]:
    latest_cards+=f'<div class="card"><div class="label">{metric_labels[key]}</div><div class="value">{fmt(latest.get(key),key)}</div></div>'

html_doc=f"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>가온전선 DART Financial Dashboard</title>
<script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
<style>
:root{{--ink:#172033;--muted:#64748b;--line:#e5e7eb;--panel:#fff;--bg:#f5f7fb;--accent:#0f766e}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,"Noto Sans KR",Arial,sans-serif}}
.container{{max-width:1440px;margin:auto;padding:28px 22px 70px}}header{{background:#111827;color:#fff;padding:34px;border-radius:20px;margin-bottom:20px}}
h1{{margin:0 0 8px;font-size:30px}}h2{{font-size:19px;margin:30px 0 14px}}p{{color:var(--muted)}}header p{{color:#cbd5e1;margin:0}}
.grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}}.card{{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:18px;box-shadow:0 4px 16px #0f172a0a}}
.label{{font-size:13px;color:var(--muted);margin-bottom:8px}}.value{{font-size:25px;font-weight:750}}
.chartgrid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}}.chart{{background:#fff;border:1px solid var(--line);border-radius:16px;padding:8px;min-height:380px}}
.table-wrap{{overflow:auto;background:#fff;border:1px solid var(--line);border-radius:16px}}
table{{width:100%;border-collapse:collapse;min-width:900px}}th,td{{padding:12px 13px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}}th:first-child,td:first-child{{text-align:left}}th{{background:#f8fafc;color:#475569;font-size:12px;position:sticky;top:0}}td{{font-size:13px}}
.empty{{background:#fff;border:1px dashed #cbd5e1;padding:28px;border-radius:16px;color:#64748b}}
.badge{{display:inline-block;padding:6px 10px;border-radius:999px;background:#ecfdf5;color:#047857;font-size:12px;font-weight:700}}
footer{{margin-top:36px;color:#64748b;font-size:12px}}a{{color:#0f766e}}
@media(max-width:900px){{.grid{{grid-template-columns:repeat(2,1fr)}}.chartgrid{{grid-template-columns:1fr}}}}@media(max-width:560px){{.grid{{grid-template-columns:1fr}}}}
</style></head>
<body><main class="container">
<header><span class="badge">DART · OpenDART · 자동 업데이트</span><h1>가온전선 재무 Dashboard</h1>
<p>사업보고서 · 반기보고서 · 분기보고서 | 2010~현재 | 연결 기준 기본 분석</p></header>
<div class="grid">{latest_cards}</div>
<h2>주요 추세</h2><div class="chartgrid"><div id="profit" class="chart"></div><div id="cash" class="chart"></div></div>
<h2>수익성·재무안정성</h2><div class="chartgrid"><div id="margins" class="chart"></div><div id="solvency" class="chart"></div></div>
{table(annual,"Annual · 사업보고서",annual_cols)}
{table(half,"Half-year · 반기보고서",half_cols)}
{table(quarterly,"Quarterly · 분기 기준",quarter_cols)}
<section><h2>국내 Peer firms</h2><div class="table-wrap"><table><thead><tr><th>기업</th><th>종목코드</th><th>비교 범위</th></tr></thead><tbody>{peer_html}</tbody></table></div></section>
<footer>Source: Financial Supervisory Service OpenDART. 재무비율 정의와 분석 순서는 프로젝트에 첨부된 「재무제표 및 재무비율 실무 가이드」를 기준으로 구현했습니다. 금액 단위는 DART API 원자료의 단위를 따릅니다.</footer>
</main>
<script>
const DATA={data_json};
function annualSorted(){{return [...DATA.annual].sort((a,b)=>a.year-b.year)}}
const a=annualSorted(), years=a.map(x=>x.year);
function trace(y,name){{return {{x:years,y:a.map(x=>x[y]),name,mode:'lines+markers',connectgaps:false}}}}
const common={{margin:{{l:55,r:20,t:55,b:45}},paper_bgcolor:'#fff',plot_bgcolor:'#fff',legend:{{orientation:'h'}},font:{{family:'Inter,Noto Sans KR,Arial'}}}};
Plotly.newPlot('profit',[trace('revenue','매출액'),trace('operating_income','영업이익'),trace('net_income','당기순이익')],{{...common,title:'매출 및 이익 추세',yaxis:{{title:'DART 원자료 단위'}}}},{{responsive:true}});
Plotly.newPlot('cash',[trace('cfo','CFO'),trace('capex','CAPEX'),trace('fcf','FCF')],{{...common,title:'현금창출력과 투자',yaxis:{{title:'DART 원자료 단위'}}}},{{responsive:true}});
Plotly.newPlot('margins',[trace('operating_margin','영업이익률'),trace('net_margin','순이익률'),trace('roe','ROE')],{{...common,title:'수익성 지표',yaxis:{{ticksuffix:'%'}}}},{{responsive:true}});
Plotly.newPlot('solvency',[trace('debt_ratio','부채비율'),trace('current_ratio','유동비율'),trace('equity_ratio','자기자본비율')],{{...common,title:'재무안정성 지표',yaxis:{{ticksuffix:'%'}}}},{{responsive:true}});
</script></body></html>"""
(OUT/"index.html").write_text(html_doc,encoding="utf-8")
print("dashboard written", OUT/"index.html")
