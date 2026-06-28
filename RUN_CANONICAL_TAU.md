# Running the canonical τ (consumer-return latency) on real FRED data

This measures the **wealth-side** latency — how long a move in top-tier net worth
takes to show up in broad consumer purchasing power. It needs the Federal Reserve
(FRED), which a locked-down sandbox can't reach, so run it locally. ~2 minutes.

---

## Step 1 — Get a free FRED API key
1. Go to https://fred.stlouisfed.org/ → create a free account.
2. Open **My Account → API Keys → Request API Key**.
3. Copy the 32-character key.

## Step 2 — Install dependencies
```bash
pip install fredapi pandas numpy matplotlib scipy
```

## Step 3 — Put `calibrate.py` next to this file
You already have it in the repo. The script below imports its estimator.

## Step 4 — Save this as `run_canonical_tau.py`
```python
import numpy as np, pandas as pd
from fredapi import Fred
from calibrate import estimate_lag_gain

fred = Fred(api_key="PASTE_YOUR_KEY_HERE")

# --- choose a TOP-side driver and a CONSUMER-side response ---
# Top-side (wealth/ownership) candidates (pick one):
#   WFRBLT01026  Net worth held by the Top 1% (Fed DFA, levels, quarterly)
#   WFRBLB50107  Net worth held by the Bottom 50% (for the divergence diagnostic)
#   M2V          Velocity of M2 (inverse circulation-speed proxy)
# Consumer-side response candidates (pick one):
#   LES1252881600Q  Real median usual weekly earnings (quarterly)
#   MEPAINUSA672N   Real median personal income (annual)
#   PCEC96          Real personal consumption expenditures (quarterly)

TOP_ID, CONS_ID = "WFRBLT01026", "LES1252881600Q"

top  = fred.get_series(TOP_ID).resample("Q").last().dropna()
cons = fred.get_series(CONS_ID).resample("Q").last().dropna()

# align on overlapping quarters
df = pd.concat([top.rename("top"), cons.rename("cons")], axis=1).dropna()
print(f"Overlap: {df.index.min().date()} .. {df.index.max().date()}  ({len(df)} quarters)")

# work in log-growth (stationary), then estimate the lead-lag
g_top  = np.diff(np.log(df["top"].values))
g_cons = np.diff(np.log(df["cons"].values))

est = estimate_lag_gain(g_top, g_cons, dt=0.25, max_lag_q=40)  # search up to 10 yrs
print(f"\nCANONICAL tau = {est['tau_years']:.2f} years "
      f"({est['lag_periods']} quarters)   corr={est['best_corr']:.2f}")
print(f"transmission gain kappa = {est['kappa_gain']:.3f}")
```

## Step 5 — Run it
```bash
python run_canonical_tau.py
```

## Step 6 — Paste the result into the white paper
Drop `tau`, `kappa`, and the correlation into the **⟦ CANONICAL τ — slot to fill ⟧**
box in §7.5, then re-deposit.

---

### Notes & troubleshooting
- **If a series ID 404s**, FRED occasionally renames DFA series. Search the FRED site
  for "Net worth held by the Top 1%" and copy the current ID into `TOP_ID`.
- **Expect a longer τ here than in `real_tau.py`.** That file measured the *income-flow*
  latency (~1 yr) and found it short; this measures the *ownership/wealth* channel,
  which the paper argues is the slow one (years, not quarters). A τ materially larger
  than the income-flow τ is itself evidence for the thesis.
- **Robustness:** rerun with a couple of different (TOP_ID, CONS_ID) pairs and report
  the range. If the peak correlation is weak (<~0.2), say so — honesty about signal
  strength is part of the contribution.
- **Divergence cross-check:** with `top`=Top-1% and a `bottom`=Bottom-50% net worth
  series, call `divergence_rate(years, top, bottom)` from `calibrate.py` for the
  wealth-side K rate to sit alongside the 1967–2018 income-side +0.93 pp/yr.
