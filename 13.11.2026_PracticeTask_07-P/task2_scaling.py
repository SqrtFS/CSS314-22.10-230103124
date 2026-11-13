import math
import multiprocessing as mp

from config import STUDENT_ID, P_PHYS, P_BOUNDARY, QUICK
from harness import run_benchmark, emit_verify_tag, save_md

N_STRONG = 120_000 if QUICK else 1_200_000
N0 = 20_000 if QUICK else 200_000
WARMUP, RUNS = (0, 3) if QUICK else (1, 5)


def stage_a(n):
    acc = 0.0
    for i in range(int(0.05 * n)):
        x = i * 1e-6 + 0.1
        for _ in range(5):
            x = math.sqrt(math.sin(x) + 2.0)
        acc += x
    return acc


def stage_b_chunk(se):
    s, e = se
    acc = 0.0
    for i in range(s, e):
        x = i * 1e-6 + 0.1
        for _ in range(10):
            x = x * 1.0000001 + 0.5
            x = math.sin(x) + math.cos(x)
        acc += x
    return acc


def pool_warm(_):
    return 0


def trial(pool, n, p):
    stage_a(n)
    chunks = [(n * t // p, n * (t + 1) // p) for t in range(p)]
    return sum(pool.map(stage_b_chunk, chunks, chunksize=1))


def bench_trial(n, p):
    with mp.Pool(processes=p) as pool:
        pool.map(pool_warm, range(2 * p))
        return run_benchmark(lambda: trial(pool, n, p), WARMUP, RUNS).median_ms


def inflection(S, plog, name, out):
    b = P_BOUNDARY
    if b >= plog:
        out.append(f"{name}: boundary {b} >= P_log, no inflection.")
        return
    before = S[b] - S.get(b - 1, 0.0)
    after = S[b + 1] - S[b]
    out.append(f"{name}: dS({b - 1}->{b}) = {before:.3f}, dS({b}->{b + 1}) = {after:.3f}, "
               f"marginal gain changes by {100 * (after / before - 1):+.1f}% across the P-core/E-core boundary (p={b}->{b + 1}).")
    print(out[-1], flush=True)


def main():
    plog = mp.cpu_count()
    out = [f"## Phase 2 - scaling (P_phys={P_PHYS}, P_log={plog})", ""]

    ta1 = run_benchmark(lambda: stage_a(N_STRONG), WARMUP, RUNS).median_ms
    T, S = {}, {}
    out += [f"### Strong scaling, N = {N_STRONG}", "",
            "| p | T ms | S_p | E_p | dS vs p-1 |", "|---|---|---|---|---|"]
    for p in range(1, plog + 1):
        T[p] = bench_trial(N_STRONG, p)
        S[p] = T[1] / T[p]
        d = f"{S[p] - S[p - 1]:.3f}" if p > 1 else "-"
        out.append(f"| {p} | {T[p]:.1f} | {S[p]:.2f} | {S[p] / p:.2f} | {d} |")
        print(out[-1], flush=True)
    s_frac = ta1 / T[1]
    out += ["", f"T_StageA(1) = {ta1:.1f} ms, s = {s_frac:.4f}, Amdahl cap S_inf = 1/s = {1 / s_frac:.1f}; "
                f"observed S_{plog} = {S[plog]:.2f}", ""]
    print(out[-2], flush=True)
    inflection(S, plog, "Strong", out)
    out.append("")

    Tw, Sg = {}, {}
    out += [f"### Weak scaling, N0 = {N0}", "",
            "| p | N(p) | T ms | E_weak | T_StageA(p) ms | alpha | S_Gustafson |", "|---|---|---|---|---|---|---|"]
    for p in range(1, plog + 1):
        n = p * N0
        Tw[p] = bench_trial(n, p)
        tap = run_benchmark(lambda: stage_a(n), WARMUP, RUNS).median_ms
        alpha = tap / Tw[p]
        Sg[p] = p - alpha * (p - 1)
        out.append(f"| {p} | {n} | {Tw[p]:.1f} | {Tw[1] / Tw[p]:.2f} | {tap:.1f} | {alpha:.4f} | {Sg[p]:.2f} |")
        print(out[-1], flush=True)
    out.append("")
    inflection({p: Tw[1] / Tw[p] * p for p in Tw}, plog, "Weak (scaled throughput)", out)
    out.append("")

    tag = emit_verify_tag("PHASE2", STUDENT_ID, S[plog], Sg[plog])
    out.append(tag)
    print(tag)
    save_md("results_task2.md", out)


if __name__ == "__main__":
    main()
