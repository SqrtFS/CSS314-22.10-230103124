import math
import multiprocessing as mp
import sys

from harness import run_benchmark, emit_verify_tag

STUDENT_SEED = 230103124
P_PHYS = 8
SERIAL_FRACTION_OF_N = 0.05




def stage_a_serial(n):

    acc = 0.0
    sin = math.sin
    sqrt = math.sqrt
    for i in range(n):
        x = float(i + 1)
        for _ in range(6):
            x = sqrt(abs(sin(x)) + 1.0)
        acc += x
    return acc


def stage_b_kernel(rng):
    start, end = rng
    sin = math.sin
    cos = math.cos
    acc = 0.0
    for i in range(start, end):
        x = (i % 1000) * 1e-3 + 0.5
        for _ in range(35):
            x = x * 1.0000001 + 1e-7
            x = sin(x) + cos(x)
        acc += x
    return acc


def split_ranges(n, p):
    base, extra = divmod(n, p)
    out, s = [], 0
    for t in range(p):
        e = s + base + (1 if t < extra else 0)
        out.append((s, e))
        s = e
    return out


# ---------- helpers ----------

def bench_pipeline(p, n_total, n_serial):
    ranges = split_ranges(n_total, p)
    pool = mp.Pool(processes=p)
    try:
        def job():
            stage_a_serial(n_serial)
            pool.map(stage_b_kernel, ranges, chunksize=1)

        stats = run_benchmark(job, warmup_runs=2, timed_runs=7)
    finally:
        pool.close()
        pool.join()
    return stats.median_ms


def bench_stage_a(n_serial):
    return run_benchmark(lambda: stage_a_serial(n_serial),
                         warmup_runs=2, timed_runs=7).median_ms


def experiment_2a(p_list, n_total):
    n_serial = int(SERIAL_FRACTION_OF_N * n_total)
    t_a1 = bench_stage_a(n_serial)
    rows, t1 = {}, None
    for p in p_list:
        t = bench_pipeline(p, n_total, n_serial)
        if p == 1:
            t1 = t
        sp = t1 / t
        rows[p] = (t, sp, sp / p)
        print(f"  2A p={p}: {t:10.2f} ms  S={sp:5.2f}  E={sp / p:5.2f}", flush=True)
    return rows, t_a1, t1


def experiment_2b(p_list, n0):
    rows, t1 = {}, None
    for p in p_list:
        n_p = n0 * p
        n_serial = int(SERIAL_FRACTION_OF_N * n_p)
        t_a = bench_stage_a(n_serial)
        t = bench_pipeline(p, n_p, n_serial)
        if p == 1:
            t1 = t
        e = t1 / t
        alpha = t_a / t
        s_g = p - alpha * (p - 1)
        rows[p] = (t, e, alpha, s_g)
        print(f"  2B p={p}: {t:10.2f} ms  E={e:5.2f}  alpha={alpha:5.3f}  S_G={s_g:5.2f}",
              flush=True)
    return rows


def main():
    quick = "--quick" in sys.argv
    div = 100 if quick else 1
    n_strong = 1_600_000 // div
    n0 = 250_000 // div

    p_log = mp.cpu_count()
    p_list = list(range(1, p_log + 1))

    print(f"P_phys={P_PHYS}, P_log={p_log}, quick={quick}")
    print("--- Experiment 2A: strong scaling ---", flush=True)
    strong, t_a1, t1_strong = experiment_2a(p_list, n_strong)

    print("--- Experiment 2B: weak scaling ---", flush=True)
    weak = experiment_2b(p_list, n0)

    # ----- tables for the report -----
    print("\n### Strong scaling (N = %d)" % n_strong)
    print("| p | T_p (ms) | S_p | E_p |")
    print("|---|---|---|---|")
    for p in p_list:
        t, sp, ep = strong[p]
        print(f"| {p} | {t:.2f} | {sp:.3f} | {ep:.3f} |")

    print("\n### Weak scaling (N0 = %d per worker)" % n0)
    print("| p | T_p (ms) | E_weak | alpha | S_Gustafson |")
    print("|---|---|---|---|---|")
    for p in p_list:
        t, e, a, sg = weak[p]
        print(f"| {p} | {t:.2f} | {e:.3f} | {a:.4f} | {sg:.3f} |")

    # ----- 3.3 analytics -----
    s = t_a1 / t1_strong
    s_inf = 1.0 / s
    s_amdahl_plog = 1.0 / (s + (1.0 - s) / p_log)
    s_obs = strong[p_log][1]
    print("\n### Amdahl")
    print(f"s = T_StageA(1)/T1 = {t_a1:.2f}/{t1_strong:.2f} = {s:.5f}")
    print(f"S_inf = 1/s = {s_inf:.2f}")
    print(f"S_theory(p={p_log}) = {s_amdahl_plog:.3f}   observed = {s_obs:.3f}")

    print("\n### Marginal speedup per added worker")
    print("| p -> p+1 | dS | change vs previous dS (%) |")
    print("|---|---|---|")
    prev = None
    for p in p_list[:-1]:
        ds = strong[p + 1][1] - strong[p][1]
        chg = "" if prev in (None, 0) else f"{(ds - prev) / prev * 100:+.1f}"
        mark = "  <-- P/E cluster boundary" if p == 4 else ""
        print(f"| {p} -> {p + 1} | {ds:.3f} | {chg} |{mark}")
        prev = ds

    s_strong_plog = strong[p_log][1]
    s_gust_plog = weak[p_log][3]
    print()
    print(emit_verify_tag("PHASE2", STUDENT_SEED, s_strong_plog, s_gust_plog))


if __name__ == "__main__":
    main()