#!/usr/bin/env python3
"""Driver: runs the weak-scaling benchmark for several thread counts x repetitions -> results.csv

  python3 run_bench.py [--threads 1 2 4 8] [--runs 5] [--k 100000000] [--serial-n 1000000] [--out ../results.csv]

If --threads is omitted: powers of two up to the hardware concurrency (plus the maximum itself).
If that yields fewer than 5 distinct counts (small machines), the list is padded with oversubscribed
counts and the 'oversubscribed' column is set to 1 so the results can be interpreted correctly.
"""
import argparse, csv, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def default_threads(hw, minimum=5):
    t = sorted({2 ** i for i in range(0, 12) if 2 ** i <= hw} | {hw})
    n = 2
    while len(t) < minimum:           # pad with oversubscribed counts
        c = max(t) * 2 if max(t) * 2 > max(t) else max(t) + 1
        t.append(c)
    return t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--threads", type=int, nargs="+")
    ap.add_argument("--runs", type=int, default=5)
    ap.add_argument("--k", type=int, default=100_000_000)
    ap.add_argument("--serial-n", type=int, default=1_000_000)
    ap.add_argument("--out", default=os.path.join(HERE, "..", "results.csv"))
    a = ap.parse_args()
    exe = os.path.join(HERE, "weak_scale_bench")
    if not os.path.exists(exe):
        subprocess.check_call(["make", "-C", HERE])
    hw = os.cpu_count() or 1
    threads = a.threads or default_threads(hw)
    print(f"hardware threads: {hw}; thread counts: {threads}; runs: {a.runs}", file=sys.stderr)
    subprocess.run([exe, "--threads", "1", "--k", str(a.k // 10), "--serial-n", "1000"], capture_output=True)  # warm-up
    with open(a.out, "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["threads", "run", "k", "serial_n", "t_total", "t_serial", "t_parallel", "pi", "hw_threads", "oversubscribed"])
        for run in range(a.runs):                         # interleave to spread drift/thermal effects
            for t in threads:
                out = subprocess.check_output([exe, "--threads", str(t), "--k", str(a.k),
                                               "--serial-n", str(a.serial_n), "--run", str(run)], text=True)
                row = out.strip().split(",")
                w.writerow(row + [hw, int(t > hw)])
                print(f"  P={t:3d} run={run} t={float(row[4]):.4f}s", file=sys.stderr)
    print(f"wrote {a.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
