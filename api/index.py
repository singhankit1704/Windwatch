"""WindWatch API (FastAPI + pandas).
Sections: 1) data loading  2) analysis functions  3) routes.
Time zone: January in the UK is GMT, so UTC == UK local time. No DST handling needed.
"""
from pathlib import Path
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException

DATA = Path(__file__).resolve().parent.parent / "data"
app = FastAPI(title="WindWatch API")

# ---------- 1) data ----------
actuals = pd.read_csv(DATA / "actuals.csv", parse_dates=["startTime"])
fc = pd.read_csv(DATA / "forecasts.csv", parse_dates=["startTime", "publishTime"])
actuals = actuals.rename(columns={"generation": "actual"})
fc = fc.rename(columns={"generation": "forecast"})
fc["horizon_h"] = (fc.startTime - fc.publishTime) / pd.Timedelta(hours=1)

# ---------- 2) analysis ----------
def decision_forecast(cutoff_hour: int) -> pd.DataFrame:
    """For every target time T, the latest forecast published before the day-ahead
    decision deadline: (day before T) at cutoff_hour:00 UTC."""
    d = fc.copy()
    d["deadline"] = d.startTime.dt.normalize() - pd.Timedelta(days=1) + pd.Timedelta(hours=cutoff_hour)
    d = d[d.publishTime <= d.deadline].sort_values("publishTime").groupby("startTime").tail(1)
    return d.sort_values("startTime")

def with_error(df: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(actuals, on="startTime", how="inner")
    df["error"] = df.actual - df.forecast          # + means wind beat forecast, - means shortfall
    df["abs_error"] = df.error.abs()
    return df

def metrics(df: pd.DataFrame) -> dict:
    e, a = df.error, df.actual
    return {
        "n": int(len(df)),
        "mae": float(e.abs().mean()), "rmse": float(np.sqrt((e ** 2).mean())),
        "bias": float(e.mean()), "nmae_pct": float(e.abs().mean() / a.mean() * 100),
        "p50_abs": float(e.abs().quantile(.5)), "p90_abs": float(e.abs().quantile(.9)),
        "p95_abs": float(e.abs().quantile(.95)),
        "shortfall_p90": float(-e.quantile(.1)),   # 9 in 10 times, wind fell short by less than this
        "shortfall_p95": float(-e.quantile(.05)),
    }

def clean(obj):
    """NaN -> None so JSON is valid."""
    if isinstance(obj, pd.DataFrame):
        return obj.astype(object).where(obj.notna(), None).to_dict("records")
    return obj

# ---------- 3) routes ----------
@app.get("/api/meta")
def meta():
    return {"first_day": str(actuals.startTime.min().date()), "last_day": str(actuals.startTime.max().date())}

@app.get("/api/decision")
def decision(date: str, cutoff_hour: int = 9):
    """Forecast a buyer would have seen the day before `date`, next to what actually happened."""
    day = pd.Timestamp(date, tz="UTC")
    d = decision_forecast(cutoff_hour)
    d = d[(d.startTime >= day) & (d.startTime < day + pd.Timedelta(days=1))]
    if d.empty:
        raise HTTPException(404, "No forecast for that date")
    d = d.merge(actuals, on="startTime", how="left")
    d["time"] = d.startTime.dt.strftime("%H:%M")
    d["publish"] = d.publishTime.dt.strftime("%d %b %H:%M")
    return clean(d[["time", "forecast", "actual", "publish", "horizon_h"]])

@app.get("/api/accuracy")
def accuracy(cutoff_hour: int = 9):
    df = with_error(decision_forecast(cutoff_hour))
    df["date"] = df.startTime.dt.strftime("%Y-%m-%d")
    df["hour"] = df.startTime.dt.hour
    daily = df.groupby("date").agg(mae=("abs_error", "mean"), bias=("error", "mean"),
                                   actual=("actual", "mean")).reset_index()
    by_hour = df.groupby("hour").agg(mae=("abs_error", "mean"), bias=("error", "mean")).reset_index()
    counts, edges = np.histogram(df.error, bins=20)
    hist = [{"bin": f"{int(edges[i])}", "count": int(counts[i])} for i in range(len(counts))]
    return {"summary": metrics(df), "daily": clean(daily), "by_hour": clean(by_hour), "histogram": hist}

@app.get("/api/horizon")
def horizon():
    """Error vs how far ahead the forecast was made (all forecasts, not just the decision one)."""
    df = with_error(fc)
    df["bucket"] = (df.horizon_h // 6 * 6).astype(int)
    g = df.groupby("bucket").agg(mae=("abs_error", "mean"), bias=("error", "mean")).reset_index()
    g["label"] = g.bucket.astype(str) + "-" + (g.bucket + 6).astype(str) + "h"
    return clean(g)
