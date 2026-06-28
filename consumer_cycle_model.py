"""
consumer_cycle_model.py
=======================
A minimal dynamical-systems toy model for the "Cyclic Consumer-Company"
hypothesis: that the *latency* with which created value returns to consumers
is the control parameter that decides whether an economy DIVERGES (a "K-shape")
or settles into a BOUNDED RISING OSCILLATION (a "sine-on-a-trend").

This is a pedagogical / illustrative model, not a calibrated forecasting model.
It is meant to let a reader confirm the qualitative claims in the white paper:

    1. A two-state linear core (K = capital/asset value, C = consumer power)
       produces three regimes, fully classified by trace T and determinant D
       of its Jacobian.
    2. Adding a return delay tau reproduces a Hopf-type destabilization:
       small tau -> bounded cycle; large tau -> growing oscillation / divergence.
    3. A bounded (Goodwin/Lotka-Volterra-style) nonlinear version gives the
       "rising bounded cycle" target shape.
    4. A curve-fitting routine recovers the envelope rate sigma and frequency
       omega from a detrended series, so empirical data can be classified.

Run:  python consumer_cycle_model.py
Outputs: regimes.png, latency_bifurcation.png, curve_fit_demo.png
License: MIT (code).  Author credit: <your name>.
"""

import numpy as np
from scipy.optimize import curve_fit

# ----------------------------------------------------------------------
# 1. LINEAR CORE
# ----------------------------------------------------------------------
# Deviations from a balanced-growth path:
#   k_dot = alpha * k  -  beta  * c        (asset value: self-leverage alpha,
#                                            drained by value returned to consumers)
#   c_dot = kappa * k  -  gamma * c        (consumer power: fed by a fraction kappa
#                                            of asset value cycling back; leaks at gamma)
#
# Jacobian  J = [[alpha, -beta], [kappa, -gamma]]
#   trace        T = alpha - gamma
#   determinant  D = beta*kappa - alpha*gamma
#
# Regime map:
#   D < 0                      -> saddle      -> exponential divergence  (K-SHAPE)
#   D > 0, T^2 < 4D, T > 0     -> unstable spiral -> GROWING oscillation (the funnel)
#   D > 0, T^2 < 4D, T = 0     -> center      -> pure neutral cycle (Goodwin sine)
#   D > 0, T^2 < 4D, T < 0     -> stable spiral -> DAMPED/BOUNDED oscillation (target)

def jacobian(alpha, beta, kappa, gamma):
    return np.array([[alpha, -beta], [kappa, -gamma]])

def classify(alpha, beta, kappa, gamma):
    T = alpha - gamma
    D = beta * kappa - alpha * gamma
    disc = T**2 - 4 * D
    if D < 0:
        regime = "saddle / divergence (K-shape)"
    elif disc >= 0:
        regime = "node (monotone), sign set by T"
    else:
        if T > 1e-9:
            regime = "unstable spiral (growing oscillation, the funnel)"
        elif abs(T) <= 1e-9:
            regime = "center (pure neutral cycle, sine)"
        else:
            regime = "stable spiral (bounded oscillation, target)"
    eig = np.linalg.eigvals(jacobian(alpha, beta, kappa, gamma))
    return dict(T=T, D=D, disc=disc, eig=eig, regime=regime)

def simulate_linear(alpha, beta, kappa, gamma, x0=(0.6, -0.4), t_end=60, dt=0.01):
    n = int(t_end / dt)
    t = np.linspace(0, t_end, n)
    x = np.zeros((n, 2)); x[0] = x0
    J = jacobian(alpha, beta, kappa, gamma)
    for i in range(n - 1):
        x[i + 1] = x[i] + dt * (J @ x[i])
    return t, x[:, 0], x[:, 1]

# ----------------------------------------------------------------------
# 2. LATENCY (DELAY) MODEL  ->  Hopf-type destabilization
# ----------------------------------------------------------------------
# c_dot(t) = kappa * k(t - tau) - gamma * c(t)
# Increasing tau (the Cantillon return delay: stimulus -> assets -> ... -> wages,
# or company growth -> 401k -> retirement decades later) destabilizes the loop.

def simulate_delay(alpha, beta, kappa, gamma, tau, x0=(0.3, -0.2),
                   t_end=120, dt=0.01):
    n = int(t_end / dt)
    lag = max(int(tau / dt), 0)
    t = np.linspace(0, t_end, n)
    k = np.zeros(n); c = np.zeros(n)
    k[0], c[0] = x0
    for i in range(n - 1):
        k_delayed = k[i - lag] if i - lag >= 0 else x0[0]
        k[i + 1] = k[i] + dt * (alpha * k[i] - beta * c[i])
        c[i + 1] = c[i] + dt * (kappa * k_delayed - gamma * c[i])
    return t, k, c

def envelope_growth(t, y, tail=0.4):
    """Estimate the oscillation envelope growth rate sigma from peaks (tail only)."""
    i0 = int(len(t) * (1 - tail))
    tt, yy = t[i0:], np.abs(y[i0:])
    # peak detection
    pk = [(tt[j], yy[j]) for j in range(1, len(yy) - 1)
          if yy[j] > yy[j - 1] and yy[j] > yy[j + 1] and yy[j] > 1e-6]
    if len(pk) < 2:
        return np.nan
    pt = np.array([p[0] for p in pk]); pv = np.array([p[1] for p in pk])
    # slope of log-amplitude vs time = sigma
    A = np.polyfit(pt, np.log(pv), 1)
    return A[0]

# ----------------------------------------------------------------------
# 3. NONLINEAR BOUNDED CYCLE  (Goodwin/Lotka-Volterra flavour) ON A TREND
# ----------------------------------------------------------------------
# u = consumer value-share in (0,1), v = company "employment/utilization" proxy.
# Closed orbits (bounded), then ride them on a common growth trend g to get the
# "rising bounded cycle" the proposal targets.

def simulate_goodwin(g=0.02, a=0.7, b=0.9, c_=0.8, d=0.6,
                     u0=0.55, v0=0.55, t_end=120, dt=0.01):
    n = int(t_end / dt)
    t = np.linspace(0, t_end, n)
    u = np.zeros(n); v = np.zeros(n); u[0], v[0] = u0, v0
    for i in range(n - 1):
        du = u[i] * (a - b * v[i])      # consumer share rises when utilization low
        dv = v[i] * (-c_ + d * u[i])    # utilization rises when consumer share high
        u[i + 1] = u[i] + dt * du
        v[i + 1] = v[i] + dt * dv
    trend = np.exp(g * t)
    company = trend * v                 # rising, bounded oscillation
    consumer = trend * u                # rising, bounded oscillation
    return t, consumer, company, u, v

# ----------------------------------------------------------------------
# 4. CURVE FITTING  ->  classify an empirical series
# ----------------------------------------------------------------------
def damped_sine(t, A, sigma, omega, phi, off):
    return off + A * np.exp(sigma * t) * np.sin(omega * t + phi)

def fit_series(t, y, p0=None):
    """Fit y(t) = off + A e^{sigma t} sin(omega t + phi). Returns params + label."""
    if p0 is None:
        p0 = [np.std(y), 0.0, 2 * np.pi / (0.3 * (t[-1] - t[0])), 0.0, np.mean(y)]
    popt, _ = curve_fit(damped_sine, t, y, p0=p0, maxfev=20000)
    A, sigma, omega, phi, off = popt
    if sigma > 0.01:
        label = "DIVERGENT envelope (K-shape / funnel)  sigma>0"
    elif sigma < -0.01:
        label = "CONVERGENT/bounded cycle  sigma<0"
    else:
        label = "NEUTRAL cycle (sine)  sigma~0"
    return dict(A=A, sigma=sigma, omega=omega, phi=phi, off=off, label=label)

def divergence_rate(t, top, bottom):
    """K-shape diagnostic: fit two shares to exponentials, return gap in growth rates."""
    g_top = np.polyfit(t, np.log(np.clip(top, 1e-9, None)), 1)[0]
    g_bot = np.polyfit(t, np.log(np.clip(bottom, 1e-9, None)), 1)[0]
    return g_top, g_bot, g_top - g_bot

# ----------------------------------------------------------------------
# DEMO / FIGURES
# ----------------------------------------------------------------------
def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    plt.rcParams.update({"font.size": 10, "axes.grid": True,
                         "grid.alpha": 0.25, "figure.dpi": 120})

    TEAL, CORAL, GRAY = "#1D9E75", "#D85A30", "#5F5E5A"

    # --- Figure 1: the three regimes (illustrative shapes; the underlying
    #     regime math is proved in the console output via classify()) --------
    fig, ax = plt.subplots(1, 3, figsize=(13, 3.8))
    t = np.linspace(0, 40, 400)

    # (a) K-shape: the two groups fork apart (gap WIDENS) -> divergence
    top = np.exp(0.045 * t)
    bot = np.exp(-0.004 * t)
    ax[0].plot(t, top, color=CORAL, label="capital / assets (top)")
    ax[0].plot(t, bot, color=TEAL, label="consumer base (bottom)")
    ax[0].fill_between(t, bot, top, color=GRAY, alpha=0.08)
    ax[0].set_title("(a) K-shape  [saddle, D<0]\nweak/slow consumer return: gap widens")
    ax[0].legend(fontsize=8); ax[0].set_xlabel("time"); ax[0].set_ylabel("value")

    # (b) the funnel: oscillation whose AMPLITUDE grows (envelope widens)
    env = np.exp(0.05 * t)
    trend = 1 + 0.05 * t
    ax[1].plot(t, trend + env * np.sin(0.9 * t), color=CORAL, label="company")
    ax[1].plot(t, trend + env * np.sin(0.9 * t - 1.4), color=TEAL, label="consumer")
    ax[1].plot(t, trend + env, color=GRAY, ls=":", lw=1)
    ax[1].plot(t, trend - env, color=GRAY, ls=":", lw=1, label="growing envelope")
    ax[1].set_title("(b) the funnel  [unstable spiral, sigma>0]\nsame cycle, amplitude explodes")
    ax[1].legend(fontsize=8); ax[1].set_xlabel("time")

    # (c) target: both rise together, oscillation BOUNDED, gap bounded
    damp = 0.6 + 0.9 * np.exp(-0.06 * t)   # settling envelope
    comp = 1.2 + 0.085 * t + damp * np.sin(0.9 * t)
    cons = 1.0 + 0.080 * t + damp * np.sin(0.9 * t - 0.5)
    ax[2].plot(t, comp, color=CORAL, label="company (rising)")
    ax[2].plot(t, cons, color=TEAL, label="consumer (rising)")
    ax[2].fill_between(t, cons, comp, color=GRAY, alpha=0.08)
    ax[2].set_title("(c) target  [stable spiral on trend]\nfast consumer return: gap bounded")
    ax[2].legend(fontsize=8); ax[2].set_xlabel("time")
    fig.tight_layout(); fig.savefig("regimes.png", bbox_inches="tight")

    # --- Figure 2: latency bifurcation ---------------------------------
    taus = np.linspace(0.0, 10.0, 41)
    sigmas = []
    for tau in taus:
        t, k, c = simulate_delay(alpha=0.04, beta=0.8, kappa=0.5,
                                 gamma=0.45, tau=tau, t_end=200)
        sigmas.append(envelope_growth(t, k))
    sigmas = np.array(sigmas)
    fig2, ax2 = plt.subplots(1, 2, figsize=(11, 3.8))
    ax2[0].axhline(0, color=GRAY, lw=1)
    ax2[0].plot(taus, sigmas, "o-", color=CORAL)
    # critical tau where sigma crosses 0
    cross = np.where(np.diff(np.sign(np.nan_to_num(sigmas))) > 0)[0]
    tau_star = taus[cross[0]] if len(cross) else np.nan
    if not np.isnan(tau_star):
        ax2[0].axvline(tau_star, ls="--", color=TEAL)
        ax2[0].text(tau_star + 0.15, ax2[0].get_ylim()[1]*0.6,
                    f"  tau* ~ {tau_star:.1f}\n  (Hopf threshold)", color=TEAL, fontsize=8)
    ax2[0].set_xlabel("consumer-return latency  tau")
    ax2[0].set_ylabel("envelope growth  sigma")
    ax2[0].set_title("(a) latency is the bifurcation parameter")

    for tau, col, lab in [(0.5, TEAL, "low latency -> bounded"),
                          (2.0, CORAL, "high latency -> diverging")]:
        t, k, c = simulate_delay(alpha=0.04, beta=0.8, kappa=0.5,
                                 gamma=0.45, tau=tau, t_end=100)
        ax2[1].plot(t, k, color=col, label=f"tau={tau}: {lab}")
    ax2[1].set_xlabel("time"); ax2[1].set_ylabel("capital deviation")
    ax2[1].set_title("(b) same system, two latencies"); ax2[1].legend(fontsize=8)
    fig2.tight_layout(); fig2.savefig("latency_bifurcation.png", bbox_inches="tight")

    # --- Figure 3: curve-fit demo --------------------------------------
    rng = np.random.default_rng(0)
    t = np.linspace(0, 40, 300)
    truth = damped_sine(t, 1.0, 0.045, 0.7, 0.3, 0.0) + rng.normal(0, 0.08, t.size)
    res = fit_series(t, truth)
    fig3, ax3 = plt.subplots(figsize=(7, 3.8))
    ax3.plot(t, truth, ".", color=GRAY, ms=3, label="detrended data")
    ax3.plot(t, damped_sine(t, res["A"], res["sigma"], res["omega"],
                            res["phi"], res["off"]), color=CORAL, lw=2,
             label=f"fit: sigma={res['sigma']:.3f}, omega={res['omega']:.2f}")
    ax3.set_title("(d) classify a series via fitted envelope sigma\n" + res["label"])
    ax3.legend(fontsize=8); ax3.set_xlabel("time")
    fig3.tight_layout(); fig3.savefig("curve_fit_demo.png", bbox_inches="tight")

    # --- console summary -----------------------------------------------
    print("REGIME CLASSIFICATION (trace T, determinant D):")
    for name, p in [
        ("K-shape (weak return)", dict(alpha=0.14, beta=0.5, kappa=0.015, gamma=0.10)),
        ("funnel (growing osc.)", dict(alpha=0.16, beta=0.9, kappa=0.7,  gamma=0.10)),
        ("bounded target",        dict(alpha=0.06, beta=0.9, kappa=0.8,  gamma=0.12)),
    ]:
        info = classify(**p)
        print(f"  {name:24s}  T={info['T']:+.3f}  D={info['D']:+.3f}"
              f"  eig={np.round(info['eig'],3)}  -> {info['regime']}")
    print(f"\nLatency bifurcation: Hopf threshold tau* ~ {tau_star:.2f}")
    print(f"Curve-fit recovered sigma = {res['sigma']:.4f} (true 0.045) -> {res['label']}")

if __name__ == "__main__":
    main()
