"""
calibrate.py
============
Empirical calibration tools for the Consumer-Return Latency (CRL) framework.

The spine of the white paper is one measurable number: tau, the latency with which
value created at the top returns as spendable consumer purchasing power. This file:

  1. estimate_lag_gain()  -- recovers (tau, kappa) from two aligned time series via
                             cross-correlation; VALIDATED here by recovering a known
                             injected lag from synthetic data.
  2. divergence_rate()    -- the K-shape diagnostic: growth-rate gap between a top
                             series and a bottom series.
  3. A REAL-DATA cut using sourced Federal Reserve / Moody's figures (2025-26).
  4. FRED series IDs + a one-command recipe for the full tau estimation on real
     quarterly series (the sandbox here cannot reach FRED; run locally).

Run:  python calibrate.py
Outputs: calibration.png  + a console report.
License: MIT.
"""

import numpy as np
from numpy.fft import rfft, irfft

# ----------------------------------------------------------------------
# 1. LATENCY + GAIN ESTIMATOR  (the core empirical object)
# ----------------------------------------------------------------------
def estimate_lag_gain(top, cons, dt=0.25, max_lag_q=24):
    """
    Estimate consumer-return latency tau and gain kappa from two series.

    top   : top-side driver (e.g. top-decile equity wealth, M2, new credit), array
    cons  : broad-consumer response (e.g. real median earnings, bottom-half income)
    dt    : sampling step in YEARS (0.25 = quarterly)
    max_lag_q : maximum lag to search, in periods (quarters)

    Returns dict(tau_years, lag_periods, kappa_gain, corr).
    tau = the lag (in years) at which 'top' best predicts a later 'cons' move;
    kappa = OLS slope of cons_t on top_{t-lag} at that lag (transmission gain).
    """
    x = (np.asarray(top, float) - np.mean(top)) / (np.std(top) + 1e-12)
    y = (np.asarray(cons, float) - np.mean(cons)) / (np.std(cons) + 1e-12)
    n = len(x)
    lags = np.arange(0, max_lag_q + 1)
    corr = []
    for L in lags:
        if L >= n:
            corr.append(np.nan); continue
        a = x[:n - L]; b = y[L:]
        corr.append(np.corrcoef(a, b)[0, 1])
    corr = np.array(corr)
    best = int(np.nanargmax(corr))
    L = lags[best]
    # transmission gain in raw units (not normalized): OLS cons_t = a + kappa*top_{t-L}
    raw_top = np.asarray(top, float)[:n - L]
    raw_cons = np.asarray(cons, float)[L:]
    kappa = np.polyfit(raw_top, raw_cons, 1)[0]
    return dict(tau_years=L * dt, lag_periods=int(L),
                kappa_gain=float(kappa), corr=corr, lags=lags, best_corr=float(corr[best]))

# ----------------------------------------------------------------------
# 2. K-SHAPE DIVERGENCE DIAGNOSTIC
# ----------------------------------------------------------------------
def divergence_rate(years, top_level, bottom_level):
    """Fit log-levels to lines; return annual growth rates and their gap g_top - g_bot."""
    g_top = np.polyfit(years, np.log(np.clip(top_level, 1e-9, None)), 1)[0]
    g_bot = np.polyfit(years, np.log(np.clip(bottom_level, 1e-9, None)), 1)[0]
    return dict(g_top=g_top, g_bot=g_bot, divergence=g_top - g_bot)

# ----------------------------------------------------------------------
# 3a. VALIDATION: recover a KNOWN lag from synthetic data
# ----------------------------------------------------------------------
def validate_estimator(true_lag_q=6, dt=0.25, seed=1):
    rng = np.random.default_rng(seed)
    n = 120
    t = np.arange(n) * dt
    # top-side driver: trend + cycle + noise
    top = 100 * np.exp(0.04 * t) * (1 + 0.15 * np.sin(0.8 * t)) + rng.normal(0, 2, n)
    # consumer = delayed, attenuated echo of the driver's deviations + own noise
    dev = np.r_[np.zeros(true_lag_q), (top - 100 * np.exp(0.04 * t))[:-true_lag_q]]
    cons = 50 + 0.35 * dev + rng.normal(0, 1.0, n)
    est = estimate_lag_gain(top, cons, dt=dt)
    return true_lag_q, est

# ----------------------------------------------------------------------
# 3b. REAL-DATA CUT  (sourced figures; see comments for provenance)
# ----------------------------------------------------------------------
# Sources (retrieved 2025-26):
#  - Top-10% corporate equity & mutual-fund holdings: ~$39T -> ~$44T over 12 months
#    (CNBC/Inside Wealth, Oct 2025, Federal Reserve data)         => ~ +12.8%/yr
#  - Bottom-50% net worth: +6% over 12 months (Federal Reserve)   => ~ +6.0%/yr
#  - Top-1% wealth share: 30.5% (2019Q4) -> 31.7% (2025Q3), record (Fed DFA / CBS)
#  - Wage growth Dec 2025: high-income ~3.0%, low-income ~1.1% (Bank of America)
REAL = {
    "wealth_growth_top10_pct_yr": 12.8,
    "wealth_growth_bottom50_pct_yr": 6.0,
    "top1_share_2019Q4": 30.5,
    "top1_share_2025Q3": 31.7,
    "wage_growth_high_pct_yr": 3.0,
    "wage_growth_low_pct_yr": 1.1,
}

def real_divergence_report():
    wealth_gap = REAL["wealth_growth_top10_pct_yr"] - REAL["wealth_growth_bottom50_pct_yr"]
    wage_gap = REAL["wage_growth_high_pct_yr"] - REAL["wage_growth_low_pct_yr"]
    share_drift_pct_yr = (REAL["top1_share_2025Q3"] - REAL["top1_share_2019Q4"]) / 5.75
    return dict(wealth_divergence_pp_yr=wealth_gap,
                wage_divergence_pp_yr=wage_gap,
                top1_share_drift_pp_yr=share_drift_pct_yr)

# ----------------------------------------------------------------------
# 3c. COVID NATURAL EXPERIMENT  (exogenous, temporary latency collapse)
# ----------------------------------------------------------------------
# The cleanest available anchor: tau fell to ~0 for many households via direct
# transfers (EIPs, enhanced UI, expanded CTC), then was removed.
# Sources (retrieved 2025-26):
#   - Post-tax income inequality fell to a 14-yr low in 2020; bottom-quintile
#     after-tax income +~15% vs 2019 (CBO / Tax Foundation).
#   - Child poverty (disposable income): -41% in 2021, then +85% in 2022 when
#     the expanded Child Tax Credit expired (CEPR/AEI, Han-Meyer-Sullivan).
#   - Post-tax top/bottom income ratio +~8% from 2021 to 2022 (US Census).
#   - KEY: pre-tax (market) inequality kept rising on trend throughout
#     (Meyer, Review of Income and Wealth 2025) -> the K-engine never paused;
#     the short-tau channel only masked it.
COVID = {
    "child_poverty_change_2021_pct": -41,   # fast channel ON
    "child_poverty_change_2022_pct": +85,   # fast channel OFF
    "posttax_ratio_change_2021_2022_pct": +8,
    "bottom_quintile_income_2020_vs_2019_pct": +15,
}

def covid_report():
    return COVID

# ----------------------------------------------------------------------
# FRED RECIPE for the full tau run (run locally; sandbox can't reach FRED)
# ----------------------------------------------------------------------
FRED_RECIPE = """
Full tau estimation on real quarterly series (run locally):

    pip install fredapi pandas
    from fredapi import Fred
    fred = Fred(api_key="YOUR_KEY")

    # TOP-SIDE driver candidates:
    #   WFRBLT01026  Top 1% net worth (Fed DFA, levels)        [or top-10% equity series]
    #   M2V          Velocity of M2 (inverse proxy for circulation speed)
    #   BOGZ1FL... corporate equities held by households (DFA)
    # CONSUMER-SIDE response candidates:
    #   LES1252881600Q  Real median weekly earnings
    #   MEPAINUSA672N   Real median personal income (annual)
    #   PCEC96          Real personal consumption expenditures
    # GOODWIN phase-plot inputs:
    #   PRS85006173     Nonfarm business labor share
    #   EMRATIO / LNS12300060  Employment-population ratio

    top  = fred.get_series('WFRBLT01026').resample('Q').last().dropna()
    cons = fred.get_series('LES1252881600Q').resample('Q').last().dropna()
    # align, log, detrend, then:
    from calibrate import estimate_lag_gain
    print(estimate_lag_gain(top.values, cons.values, dt=0.25))
"""

# ----------------------------------------------------------------------
def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.grid": True,
                         "grid.alpha": 0.25, "figure.dpi": 120})
    TEAL, CORAL, GRAY = "#1D9E75", "#D85A30", "#5F5E5A"

    # --- validate the latency estimator ---
    true_lag, est = validate_estimator(true_lag_q=6)
    print("=" * 64)
    print("1. LATENCY ESTIMATOR VALIDATION (synthetic, known lag)")
    print(f"   true lag      = {true_lag} quarters ({true_lag*0.25:.2f} yr)")
    print(f"   recovered tau = {est['lag_periods']} quarters "
          f"({est['tau_years']:.2f} yr)   corr={est['best_corr']:.2f}")
    print(f"   gain kappa    = {est['kappa_gain']:.3f}")

    # --- real divergence cut ---
    rd = real_divergence_report()
    print("\n2. REAL-DATA DIVERGENCE (sourced Fed / Moody's, 2025-26)")
    print(f"   wealth growth gap  (top10 - bottom50): {rd['wealth_divergence_pp_yr']:.1f} pp/yr")
    print(f"   wage growth gap    (high - low)      : {rd['wage_divergence_pp_yr']:.1f} pp/yr")
    print(f"   top-1% share drift                   : {rd['top1_share_drift_pp_yr']:.2f} pp/yr")
    print("   -> all positive: the empirical system is in the DIVERGENT (K) regime.")

    print("\n3. COVID-19 NATURAL EXPERIMENT (exogenous latency collapse, then removal)")
    cv = covid_report()
    print(f"   child poverty 2021 (fast channel ON) : {cv['child_poverty_change_2021_pct']}%")
    print(f"   child poverty 2022 (channel removed) : +{cv['child_poverty_change_2022_pct']}%")
    print(f"   post-tax top/bottom ratio 2021->2022 : +{cv['posttax_ratio_change_2021_2022_pct']}%")
    print("   KEY: pre-tax (market) inequality kept rising throughout -> lever, not engine.")

    print("\n4. FRED RECIPE for full tau run:")
    print(FRED_RECIPE)

    # --- figure ---
    fig, ax = plt.subplots(1, 3, figsize=(14.5, 3.8))
    ax[0].plot(est["lags"] * 0.25, est["corr"], "o-", color=CORAL)
    ax[0].axvline(est["tau_years"], ls="--", color=TEAL)
    ax[0].axvline(true_lag * 0.25, ls=":", color=GRAY)
    ax[0].set_xlabel("candidate latency tau (years)")
    ax[0].set_ylabel("cross-correlation")
    ax[0].set_title(f"(a) estimator recovers tau\n(true {true_lag*0.25:.2f}yr, "
                    f"found {est['tau_years']:.2f}yr)")

    labels = ["wealth\n(top10-bot50)", "wages\n(high-low)", "top-1% share\ndrift"]
    vals = [rd["wealth_divergence_pp_yr"], rd["wage_divergence_pp_yr"],
            rd["top1_share_drift_pp_yr"]]
    ax[1].bar(labels, vals, color=[CORAL, CORAL, GRAY])
    ax[1].axhline(0, color="k", lw=1)
    ax[1].set_ylabel("divergence (pp / yr)")
    ax[1].set_title("(b) real divergence rates (all > 0 = K regime)")

    # COVID natural experiment: child poverty ON vs OFF
    cyears = ["2021\nchannel ON", "2022\nchannel OFF"]
    cvals = [cv["child_poverty_change_2021_pct"], cv["child_poverty_change_2022_pct"]]
    ax[2].bar(cyears, cvals, color=[TEAL, CORAL])
    ax[2].axhline(0, color="k", lw=1)
    ax[2].set_ylabel("child poverty change (%)")
    ax[2].set_title("(c) COVID latency shock\nfast channel on -> off")
    fig.tight_layout(); fig.savefig("calibration.png", bbox_inches="tight")
    print("Wrote calibration.png")

if __name__ == "__main__":
    main()
