#!/usr/bin/env python3
"""
Task 21 - Parametric speedup simulator: Amdahl (strong scaling) vs Gustafson (weak scaling).

Valid domain:  1 <= P <= 65,536   and   0.001 <= alpha <= 0.20

Usage examples
--------------
  python3 simulator.py                                  # defaults: powers of two, 5 serial fractions
  python3 simulator.py --alphas 0.04 --P 16 64 256 1024 4096 16384
  python3 simulator.py --alpha-grid 0.001 0.2 12        # 12 log-spaced alphas
  python3 simulator.py --csv out.csv --plot-dir ../plots

Output
------
  CSV columns: alpha, P, ideal, amdahl_speedup, gustafson_speedup,
               amdahl_efficiency, gustafson_efficiency, ratio_G_over_A
  Plots: overlay of strong (Amdahl) vs weak (Gustafson) curves, speedup and efficiency.
"""
import argparse, csv, os, sys
import numpy as np

P_MIN, P_MAX = 1, 65536
A_MIN, A_MAX = 0.001, 0.20


def amdahl(P, s):
    return 1.0 / (s + (1.0 - s) / P)


def gustafson(P, a):
    return P - a * (P - 1.0)


def default_P():
    return [2 ** k for k in range(0, 17)]  # 1 ... 65536


def validate(P, alphas):
    if min(P) < P_MIN or max(P) > P_MAX:
        sys.exit(f"P must lie in [{P_MIN}, {P_MAX}]")
    if min(alphas) < A_MIN - 1e-12 or max(alphas) > A_MAX + 1e-12:
        sys.exit(f"alpha must lie in [{A_MIN}, {A_MAX}]")


def simulate(P_list, alphas):
    rows = []
    for a in alphas:
        for P in P_list:
            sa, sg = amdahl(P, a), gustafson(P, a)
            rows.append(dict(alpha=a, P=P, ideal=P,
                             amdahl_speedup=sa, gustafson_speedup=sg,
                             amdahl_efficiency=sa / P, gustafson_efficiency=sg / P,
                             ratio_G_over_A=sg / sa))
    return rows


def write_csv(rows, path):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({k: (f"{v:.10g}" if isinstance(v, float) else v) for k, v in r.items()})


def plot(rows, alphas, outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    os.makedirs(outdir, exist_ok=True)
    cmap = plt.get_cmap("viridis")
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.2))
    Ps = sorted({r["P"] for r in rows})
    ax[0].loglog(Ps, Ps, "k:", lw=1.5, label="Ideal $S=P$")
    for i, a in enumerate(alphas):
        c = cmap(i / max(1, len(alphas) - 1))
        sub = [r for r in rows if r["alpha"] == a]
        ax[0].loglog([r["P"] for r in sub], [r["gustafson_speedup"] for r in sub], "-", color=c, lw=2,
                     label=f"Gustafson $\\alpha$={a:g}")
        ax[0].loglog([r["P"] for r in sub], [r["amdahl_speedup"] for r in sub], "--", color=c, lw=2,
                     label=f"Amdahl $s$={a:g}")
        ax[1].semilogx([r["P"] for r in sub], [r["gustafson_efficiency"] for r in sub], "-", color=c, lw=2)
        ax[1].semilogx([r["P"] for r in sub], [r["amdahl_efficiency"] for r in sub], "--", color=c, lw=2)
    ax[0].set(xlabel="Processors P", ylabel="Speedup", title="Speedup: weak (solid) vs strong (dashed) scaling")
    ax[0].grid(True, which="both", alpha=.3)
    ax[0].legend(fontsize=7, ncol=2)
    ax[1].set(xlabel="Processors P", ylabel="Parallel efficiency S/P", ylim=(0, 1.02),
              title="Efficiency: Gustafson $\\to 1-\\alpha$, Amdahl $\\to 0$")
    ax[1].grid(True, which="both", alpha=.3)
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(outdir, f"simulator_overlay.{ext}"), dpi=200)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--P", type=int, nargs="+", default=default_P(), help="core counts")
    ap.add_argument("--alphas", type=float, nargs="+", default=[0.001, 0.01, 0.04, 0.08, 0.20])
    ap.add_argument("--alpha-grid", type=float, nargs=3, metavar=("LO", "HI", "N"),
                    help="log-spaced alpha grid (overrides --alphas)")
    ap.add_argument("--csv", default="simulator_output.csv")
    ap.add_argument("--plot-dir", default="../plots")
    ap.add_argument("--no-plot", action="store_true")
    a = ap.parse_args()
    alphas = list(np.geomspace(a.alpha_grid[0], a.alpha_grid[1], int(a.alpha_grid[2]))) if a.alpha_grid else a.alphas
    validate(a.P, alphas)
    rows = simulate(sorted(a.P), alphas)
    write_csv(rows, a.csv)
    print(f"wrote {len(rows)} rows -> {a.csv}")
    if not a.no_plot:
        plot(rows, alphas, a.plot_dir)
        print(f"plots  -> {a.plot_dir}/simulator_overlay.(png|pdf)")


if __name__ == "__main__":
    main()
