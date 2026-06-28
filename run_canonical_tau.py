"""
run_canonical_tau.py  (executed version)
========================================
Measures the canonical wealth-side consumer-return latency from real FRED data:
  TOP-side : WFRBLT01026     Net worth held by the Top 1% (Fed DFA, quarterly)
  CONSUMER : LES1252881600Q  Real median usual weekly earnings (quarterly)

Result (US 1989Q3-2026Q1, 146 quarters):
    divergence       = +6.21 pp/yr  (top 6.63%/yr vs wage 0.42%/yr)
    canonical tau    ~ 3 years      (range 2.5-4 across specifications)
    peak correlation ~ 0.45         (cycle frequency; ~0.18 at quarterly)
    gain kappa       ~ 0.06-0.11

Run: python run_canonical_tau.py    (needs calibrate.py + the two CSVs alongside)
License: MIT.
"""
import numpy as np, pandas as pd
from calibrate import estimate_lag_gain

def load(path, col):
    d = pd.read_csv(path, parse_dates=["observation_date"])
    d.columns = ["date", col]
    d["date"] = d["date"].dt.to_period("Q")
    d[col] = pd.to_numeric(d[col], errors="coerce")
    return d

def detrend(v):
    t = np.arange(len(v)); return v - np.polyval(np.polyfit(t, v, 1), t)

def main():
    df = load("WFRBLT01026.csv", "top").merge(
         load("LES1252881600Q.csv", "cons"), on="date", how="inner").dropna().reset_index(drop=True)
    lt, lc = np.log(df["top"].values), np.log(df["cons"].values)
    print(f"span {df.date.iloc[0]}..{df.date.iloc[-1]}  ({len(df)} quarters)\n")
    print("cross-correlation specifications (top-1% net worth -> real median wage):")
    for name, x, y in [
        ("QoQ log-growth",       np.diff(lt),    np.diff(lc)),
        ("YoY log-growth",       lt[4:]-lt[:-4], lc[4:]-lc[:-4]),
        ("2yr log-growth",       lt[8:]-lt[:-8], lc[8:]-lc[:-8]),
        ("detrended log-levels", detrend(lt),    detrend(lc)),
    ]:
        e = estimate_lag_gain(x, y, dt=0.25, max_lag_q=40)
        print(f"  {name:20s} tau={e['tau_years']:.2f}yr  peakcorr={e['best_corr']:.3f}  kappa={e['kappa_gain']:.3f}")
    yrs = (df.date.iloc[-1].year - df.date.iloc[0].year) + 0.25
    gt = np.log(df["top"].iloc[-1]/df["top"].iloc[0]) / yrs
    gc = np.log(df["cons"].iloc[-1]/df["cons"].iloc[0]) / yrs
    print(f"\n  divergence = {(gt-gc)*100:.2f} pp/yr  (top {gt*100:.2f}%/yr vs wage {gc*100:.2f}%/yr)")

if __name__ == "__main__":
    main()
