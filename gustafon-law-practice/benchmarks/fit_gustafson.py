#!/usr/bin/env python3
"""
Task 23 - Statistics + least-squares extraction of the empirical serial fraction.

Scaled speedup for weak scaling (per-thread work constant):   S(P) = P * T(1) / T(P)
Gustafson:  S(P) = P - alpha (P-1)   =>   y_i := P_i - S_i = alpha * x_i,  x_i := P_i - 1
Least squares through the origin:  alpha = sum(w x y) / sum(w x^2),  Var(alpha) = 1 / sum(w x^2)
(w = 1/sigma_y^2 for the weighted fit, w = 1 for the ordinary fit.)

Usage:  python3 fit_gustafson.py [results.csv] [--json fit_results.json]
"""
import argparse, csv, json, math, os
from collections import defaultdict

import numpy as np


def load(path):
    d = defaultdict(list)
    meta = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            d[int(r["threads"])].append(float(r["t_total"]))
            meta["hw_threads"] = int(r.get("hw_threads", 0) or 0)
    return d, meta


def analyse(d):
    Ps = np.array(sorted(d))
    n = np.array([len(d[p]) for p in Ps])
    mean = np.array([np.mean(d[p]) for p in Ps])
    std = np.array([np.std(d[p], ddof=1) if len(d[p]) > 1 else 0.0 for p in Ps])
    sem = std / np.sqrt(n)
    t1, s1 = mean[Ps == 1][0], sem[Ps == 1][0]
    S = Ps * t1 / mean
    # first-order error propagation, S = P t1 / tP
    sS = S * np.sqrt((s1 / t1) ** 2 + (sem / mean) ** 2)
    return Ps, n, mean, std, sem, S, sS


def fit(Ps, S, sS, weighted):
    x = Ps - 1.0
    y = Ps - S
    m = x > 0
    w = 1.0 / np.maximum(sS[m], 1e-12) ** 2 if weighted else np.ones(m.sum())
    sxx = np.sum(w * x[m] ** 2)
    alpha = np.sum(w * x[m] * y[m]) / sxx
    res = y[m] - alpha * x[m]
    dof = max(1, m.sum() - 1)
    if weighted:
        chi2 = np.sum(w * res ** 2)
        se = math.sqrt(1.0 / sxx) * math.sqrt(max(1.0, chi2 / dof))
    else:
        se = math.sqrt(np.sum(res ** 2) / dof / sxx)
    ss_res = np.sum((S[m] - (Ps[m] - alpha * x[m])) ** 2)
    ss_tot = np.sum((S[m] - np.mean(S[m])) ** 2)
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return float(alpha), float(se), float(r2)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", nargs="?", default=os.path.join(here, "results.csv"))
    ap.add_argument("--json", default=os.path.join(here, "fit_results.json"))
    a = ap.parse_args()
    d, meta = load(a.csv)
    Ps, n, mean, std, sem, S, sS = analyse(d)
    print(f"{'P':>4} {'runs':>4} {'mean T [s]':>11} {'std [s]':>9} {'S(P)':>8} {'+/-':>7} {'E':>7}")
    for i, P in enumerate(Ps):
        print(f"{P:4d} {n[i]:4d} {mean[i]:11.5f} {std[i]:9.5f} {S[i]:8.3f} {sS[i]:7.3f} {S[i]/P:7.3f}")
    al_u, se_u, r2_u = fit(Ps, S, sS, False)
    al_w, se_w, r2_w = fit(Ps, S, sS, True)
    print(f"\nalpha_observed (OLS)      = {al_u:.4f} +/- {se_u:.4f}   R^2 = {r2_u:.4f}")
    print(f"alpha_observed (weighted) = {al_w:.4f} +/- {se_w:.4f}   R^2 = {r2_w:.4f}")
    hw = meta.get("hw_threads", 0)
    if hw and Ps.max() > hw:
        print(f"\nNOTE: thread counts exceed the {hw} hardware thread(s): oversubscribed runs share cores, "
              "so alpha_observed mostly reflects CPU contention, not algorithmic serial work.")
    out = dict(P=Ps.tolist(), runs=n.tolist(), mean_time=mean.tolist(), std_time=std.tolist(),
               sem_time=sem.tolist(), speedup=S.tolist(), speedup_err=sS.tolist(),
               alpha_ols=al_u, alpha_ols_se=se_u, r2_ols=r2_u,
               alpha_weighted=al_w, alpha_weighted_se=se_w, r2_weighted=r2_w, hw_threads=hw)
    with open(a.json, "w") as f:
        json.dump(out, f, indent=2)
    print(f"saved {a.json}")


if __name__ == "__main__":
    main()
