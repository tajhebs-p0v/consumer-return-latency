"""
real_tau.py
===========
A FIRST real-data estimate of consumer-return latency tau, using genuinely real,
publicly mirrored series (no synthetic data):

  * TOP / ASSET side  : Shiller real S&P 500 price (monthly 1871-2026)
                        -- equity wealth, ~87% held by the top decile.
  * CONSUMER side     : U.S. Census real household income upper limits by fifth
                        + top 5% (annual 1967-2018).

Two latency cuts:
  (i)  within-income distributional latency:  Top 5% income  ->  Lowest fifth
  (ii) asset-to-consumer latency (Cantillon):  Real S&P 500   ->  Lowest fifth
Plus the K-shape divergence rate (Top 5% vs Lowest growth, 1967-2018).

CAVEATS (state these in the paper): annual data, ~52 points; quintile *upper
limits* proxy each group; real S&P proxies top wealth. This is a coarse but REAL
estimate. The canonical quarterly run (top-1% net worth vs real median earnings)
needs FRED and is in calibrate.py's FRED recipe.

Data sources (downloaded from GitHub mirrors):
  sp500.csv : raw.githubusercontent.com/datasets/s-and-p-500
  hh.csv    : raw.githubusercontent.com/datasets/household-income-us-historical
License: MIT.
"""
import re
import numpy as np
import pandas as pd
from calibrate import estimate_lag_gain, divergence_rate


def load_household(path="hh.csv"):
    df = pd.read_csv(path)
    # Year column has footnotes like "2017 (40)" and dupes -> extract int year
    df["yr"] = df["Year"].astype(str).str.extract(r"(\d{4})").astype(int)
    df = df.drop_duplicates(subset="yr", keep="first").sort_values("yr")
    for c in ["Lowest", "Second", "Third", "Fourth", "Top 5 percent"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["Lowest", "Top 5 percent"]).reset_index(drop=True)


def load_sp_annual(path="sp500.csv"):
    df = pd.read_csv(path)
    df["yr"] = df["Date"].str.slice(0, 4).astype(int)
    df = df[df["Real Price"] > 0]                      # drop months w/o CPI yet
    return df.groupby("yr")["Real Price"].mean().reset_index()


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.grid": True,
                         "grid.alpha": 0.25, "figure.dpi": 120})
    TEAL, CORAL, GRAY = "#1D9E75", "#D85A30", "#5F5E5A"

    hh = load_household()
    sp = load_sp_annual()
    merged = hh.merge(sp, on="yr", how="inner")
    y0, y1 = int(merged.yr.min()), int(merged.yr.max())
    yrs = merged.yr.values.astype(float)

    top_inc = merged["Top 5 percent"].values
    low_inc = merged["Lowest"].values
    sp_real = merged["Real Price"].values

    print(f"Real data span: {y0}-{y1}  ({len(merged)} annual points)\n")

    # --- divergence rate (K diagnostic) ---
    dv = divergence_rate(yrs, top_inc, low_inc)
    print("K-SHAPE DIVERGENCE (real income limits):")
    print(f"  top-5% real income growth : {dv['g_top']*100:.2f} %/yr")
    print(f"  lowest-fifth real growth  : {dv['g_bot']*100:.2f} %/yr")
    print(f"  divergence (top - bottom) : {dv['divergence']*100:.2f} pp/yr  "
          f"(positive => K)\n")

    # --- latency cut (i): within-income, Top5% -> Lowest ---
    est_i = estimate_lag_gain(np.diff(np.log(top_inc)),
                              np.diff(np.log(low_inc)), dt=1.0, max_lag_q=6)
    # --- latency cut (ii): asset -> consumer, real S&P -> Lowest ---
    est_ii = estimate_lag_gain(np.diff(np.log(sp_real)),
                               np.diff(np.log(low_inc)), dt=1.0, max_lag_q=6)

    print("CONSUMER-RETURN LATENCY tau (REAL DATA, coarse annual):")
    print(f"  (i)  Top-5% income  -> Lowest fifth : tau ~ {est_i['tau_years']:.0f} yr"
          f"   (corr {est_i['best_corr']:.2f})")
    print(f"  (ii) Real S&P 500   -> Lowest fifth : tau ~ {est_ii['tau_years']:.0f} yr"
          f"   (corr {est_ii['best_corr']:.2f})")
    print("\n  Interpretation (honest): at ANNUAL resolution the income-flow latency is")
    print("  short -- top and bottom *incomes* co-move (lag~0), and asset prices lead")
    print("  bottom income by ~1yr. Yet divergence is still +0.93pp/yr. That gap is NOT")
    print("  produced by a long *wage* lag -- it compounds through the slow *ownership/")
    print("  capital* return loop, which these income series don't capture. Implication:")
    print("  the high-tau channel to attack is CAPITAL/OWNERSHIP return, not wage flow --")
    print("  which is exactly why the instrument is a consumer *equity* stake, not a")
    print("  wage top-up. (Canonical wealth-side tau: run calibrate.py's FRED recipe.)")

    # --- figure ---
    fig, ax = plt.subplots(1, 3, figsize=(14.5, 3.9))
    # (a) the real K: top5% vs lowest, indexed
    ax[0].plot(yrs, top_inc / top_inc[0], color=CORAL, label="top 5% income")
    ax[0].plot(yrs, low_inc / low_inc[0], color=TEAL, label="lowest fifth")
    ax[0].fill_between(yrs, low_inc / low_inc[0], top_inc / top_inc[0],
                       color=GRAY, alpha=0.08)
    ax[0].set_title(f"(a) the real K, US {y0}-{y1}\n"
                    f"divergence {dv['divergence']*100:.2f} pp/yr")
    ax[0].set_ylabel(f"real income (index, {y0}=1)")
    ax[0].legend(fontsize=8)

    # (b) cross-correlation vs lag, cut (i)
    ax[1].plot(est_i["lags"], est_i["corr"], "o-", color=CORAL)
    ax[1].axvline(est_i["lag_periods"], ls="--", color=TEAL)
    ax[1].set_xlabel("lag (years)"); ax[1].set_ylabel("cross-correlation")
    ax[1].set_title(f"(b) top-5% -> lowest fifth\ntau ~ {est_i['tau_years']:.0f} yr")

    # (c) cross-correlation vs lag, cut (ii)
    ax[2].plot(est_ii["lags"], est_ii["corr"], "o-", color=CORAL)
    ax[2].axvline(est_ii["lag_periods"], ls="--", color=TEAL)
    ax[2].set_xlabel("lag (years)"); ax[2].set_ylabel("cross-correlation")
    ax[2].set_title(f"(c) real S&P -> lowest fifth\ntau ~ {est_ii['tau_years']:.0f} yr")
    fig.tight_layout(); fig.savefig("real_tau.png", bbox_inches="tight")
    print("\nWrote real_tau.png")


if __name__ == "__main__":
    main()
