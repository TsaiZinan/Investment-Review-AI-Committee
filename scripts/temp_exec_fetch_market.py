import argparse
import csv
import json
import urllib.request
from datetime import date
from pathlib import Path


FRED_SERIES = [
    "DGS10",
    "DGS2",
    "DFII10",
    "T10Y2Y",
    "DTWEXBGS",
    "T10YIE",
    "GVZCLS",
]


def fetch_fred_series(series_id: str):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"
    with urllib.request.urlopen(url, timeout=20) as resp:
        raw = resp.read().decode("utf-8", errors="replace")

    rows = list(csv.reader(raw.splitlines()))
    if len(rows) < 2:
        return {"id": series_id, "url": url, "date": None, "value": None}

    date_idx = None
    value_idx = None
    header = rows[0]
    for i, h in enumerate(header):
        hl = h.strip().lower()
        if hl in {"date", "observation_date"}:
            date_idx = i
        if h.strip() == series_id:
            value_idx = i

    if date_idx is None or value_idx is None:
        return {"id": series_id, "url": url, "date": None, "value": None}

    last_date = None
    last_value = None
    for r in rows[1:]:
        if len(r) <= max(date_idx, value_idx):
            continue
        d = (r[date_idx] or "").strip()
        v = (r[value_idx] or "").strip()
        if not d or not v or v == ".":
            continue
        try:
            last_date = d
            last_value = float(v)
        except ValueError:
            continue

    return {"id": series_id, "url": url, "date": last_date, "value": last_value}


def fetch_fund_estimate(fund_code: str):
    url = f"https://fundgz.1234567.com.cn/js/{fund_code}.js"
    with urllib.request.urlopen(url, timeout=20) as resp:
        raw = resp.read().decode("utf-8", errors="replace").strip()

    left = raw.find("(")
    right = raw.rfind(")")
    if left == -1 or right == -1 or right <= left:
        return {"fund_code": fund_code, "url": url, "data": None}

    payload = raw[left + 1 : right]
    try:
        data = json.loads(payload)
    except Exception:
        data = None
    return {"fund_code": fund_code, "url": url, "data": data}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--strategy-json", required=True)
    p.add_argument("--output", required=True)
    args = p.parse_args()

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    strategy_path = Path(args.strategy_json)
    strategy = json.loads(strategy_path.read_text(encoding="utf-8"))
    plan = strategy.get("investment_plan", [])
    codes = []
    for x in plan:
        c = x.get("fund_code")
        if c:
            codes.append(c)
    codes = list(dict.fromkeys(codes))

    out = {"fetched_at": date.today().isoformat(), "fred": {}, "funds": {}}
    for sid in FRED_SERIES:
        try:
            out["fred"][sid] = fetch_fred_series(sid)
        except Exception as e:
            out["fred"][sid] = {"id": sid, "url": f"https://fred.stlouisfed.org/series/{sid}", "date": None, "value": None, "error": str(e)}

    for code in codes:
        try:
            out["funds"][code] = fetch_fund_estimate(code)
        except Exception as e:
            out["funds"][code] = {"fund_code": code, "url": f"https://fundgz.1234567.com.cn/js/{code}.js", "data": None, "error": str(e)}

    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

