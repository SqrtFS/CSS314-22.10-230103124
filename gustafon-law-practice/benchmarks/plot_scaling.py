#!/usr/bin/env python3
"""Task 24 - Publication-quality plot: ideal, Gustafson fit, measured (SEM bars), Amdahl (same fraction)."""
import json, os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

here = os.path.dirname(os.path.abspath(__file__))
fit = json.load(open(os.path.join(here, "fit_results.json")))
P = np.array(fit["P"], float); S = np.array(fit["speedup"]); sS = np.array(fit["speedup_err"])
alpha = min(max(fit["alpha_ols"], 0.0), 1.0)
hw = fit.get("hw_threads", 0)
Pc = np.linspace(1, P.max() * 1.05, 400)

plt.rcParams.update({"font.size": 11, "axes.grid": True, "grid.alpha": .3, "font.family": "serif"})
fig, ax = plt.subplots(1, 2, figsize=(12.5, 4.8))
for a_, ylab, ttl in ((ax[0], "Scaled speedup $S(P)=P\\,T_1/T_P$", "Speedup"),
                      (ax[1], "Parallel efficiency $S/P$", "Efficiency")):
    f = 1.0 if a_ is ax[0] else 1.0 / Pc
    ideal = Pc
    g = Pc - alpha * (Pc - 1)
    am = 1.0 / (alpha + (1 - alpha) / Pc)
    if a_ is ax[0]:
        a_.plot(Pc, ideal, "k:", lw=1.6, label="(1) Ideal $S=P$")
        a_.plot(Pc, g, "-", color="tab:blue", lw=2, label=f"(2) Gustafson fit, $\\alpha$={alpha:.3f}")
        a_.plot(Pc, am, "--", color="tab:red", lw=2, label=f"(4) Amdahl, same $s$={alpha:.3f}")
        a_.errorbar(P, S, yerr=sS, fmt="o", color="k", capsize=4, ms=6, label="(3) Measured (±SEM)")
    else:
        a_.plot(Pc, ideal / Pc, "k:", lw=1.6)
        a_.plot(Pc, g / Pc, "-", color="tab:blue", lw=2)
        a_.plot(Pc, am / Pc, "--", color="tab:red", lw=2)
        a_.errorbar(P, S / P, yerr=sS / P, fmt="o", color="k", capsize=4, ms=6)
        a_.set_ylim(0, 1.05)
    if hw and P.max() > hw:
        a_.axvline(hw, color="gray", ls="-.", lw=1, label=f"Hardware threads = {hw} (right of line: oversubscribed)")
    a_.set(xlabel="Threads $P$", ylabel=ylab, title=ttl)
ax[0].legend(loc="center right", fontsize=8)
fig.suptitle("Weak-scaling benchmark vs. Gustafson and Amdahl models", y=1.0)
fig.tight_layout()
outdir = os.path.join(here, "..", "plots"); os.makedirs(outdir, exist_ok=True)
for ext in ("png", "pdf"):
    fig.savefig(os.path.join(outdir, f"scaling_comparison.{ext}"), dpi=300)
print("saved plots/scaling_comparison.(png|pdf)")
