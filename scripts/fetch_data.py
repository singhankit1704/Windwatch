"""Download Elexon data once and save small CSVs into data/.
Run locally (needs internet):  python scripts/fetch_data.py
- Actuals: FUELHH, fuelType WIND, Jan 2026
- Forecasts: WINDFOR, published 15 Dec 2025 -> 31 Jan 2026, targets in Jan 2026, horizon <= 48h
"""
import requests, pandas as pd
from datetime import datetime, timedelta, timezone

BASE = "https://data.elexon.co.uk/bmrs/api/v1/datasets"
UTC = timezone.utc

def get(dataset, params):
    r = requests.get(f"{BASE}/{dataset}/stream", params=params, timeout=120)
    r.raise_for_status()
    return r.json()

def actuals():
    rows = get("FUELHH", {"settlementDateFrom": "2026-01-01", "settlementDateTo": "2026-01-31",
                          "fuelType": "WIND", "format": "json"})
    df = pd.DataFrame(rows)
    df = df[df["fuelType"] == "WIND"][["startTime", "generation"]]
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    return df.drop_duplicates("startTime").sort_values("startTime")

def forecasts():
    out, start, end = [], datetime(2025, 12, 15, tzinfo=UTC), datetime(2026, 2, 1, tzinfo=UTC)
    while start < end:  # small windows keep each request light
        stop = min(start + timedelta(days=2), end)
        out += get("WINDFOR", {"publishDateTimeFrom": start.strftime("%Y-%m-%dT%H:%MZ"),
                               "publishDateTimeTo": stop.strftime("%Y-%m-%dT%H:%MZ"), "format": "json"})
        print("fetched up to", stop)
        start = stop
    df = pd.DataFrame(out)[["startTime", "publishTime", "generation"]]
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df = df.drop_duplicates(["startTime", "publishTime"])
    df = df[(df.startTime >= "2026-01-01") & (df.startTime < "2026-02-01")]
    h = (df.startTime - df.publishTime) / pd.Timedelta(hours=1)
    return df[(h >= 0) & (h <= 48)].sort_values(["startTime", "publishTime"])

if __name__ == "__main__":
    a, f = actuals(), forecasts()
    a.to_csv("data/actuals.csv", index=False); f.to_csv("data/forecasts.csv", index=False)
    print(len(a), "actual rows,", len(f), "forecast rows")
