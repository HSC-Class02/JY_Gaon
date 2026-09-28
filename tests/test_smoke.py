import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.ratios import calculate

def test_ratio_smoke():
    x={"revenue":1000,"gross_profit":300,"operating_income":100,"net_income":60,
       "total_assets":1000,"equity":500,"current_assets":400,"current_liabilities":200,
       "total_liabilities":500,"interest_bearing_debt":200,"cash":50,
       "receivables":100,"inventory":150,"cfo":80,"capex":30}
    r=calculate(x,{})
    assert round(r["operating_margin"],1)==10.0
    assert round(r["debt_ratio"],1)==100.0
    assert round(r["fcf"],1)==50.0
