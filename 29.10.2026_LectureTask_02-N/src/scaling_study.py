import hashlib, json, math, multiprocessing as mp, os, statistics, sys, time
from multiprocessing import shared_memory
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from salt import get_student_params

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
STEPS = 20
REPEATS = 5
FLOPS_PER_CELL = 5
BYTES_PER_CELL_IDEAL = 16


def stencil_rows(src, dst, r0, r1):
    n = src.shape[1]
    lo = max(r0, 1)
    hi = min(r1, src.shape[0] - 1)
    if hi <= lo:
        return
    dst[lo:hi, 1:n - 1] = 0.2 * (
        src[lo:hi, 1:n - 1]
        + src[lo - 1:hi - 1, 1:n - 1]
        + src[lo + 1:hi + 1, 1:n - 1]
        + src[lo:hi, 0:n - 2]
        + src[lo:hi, 2:n]
    )


def worker(args):
    name_a, name_b, n, src_is_a, r0, r1 = args
    sa = shared_memory.SharedMemory(name=name_a)
    sb = shared_memory.SharedMemory(name=name_b)
    a = np.ndarray((n, n), dtype=np.float64, buffer=sa.buf)
    b = np.ndarray((n, n), dtype=np.float64, buffer=sb.buf)
    if src_is_a:
        stencil_rows(a, b, r0, r1)
    else:
        stencil_rows(b, a, r0, r1)
    sa.close()
    sb.close()
    return None


def chunks(n, P):
    edges = [round(i * n / P) for i in range(P + 1)]
    return [(edges[i], edges[i + 1]) for i in range(P)]


def init_grid(n, seed):
    rng = np.random.default_rng(seed)
    return rng.random((n, n))


def reference(n, seed):
    a = init_grid(n, seed)
    b = a.copy()
    src, dst = a, b
    for _ in range(STEPS):
        stencil_rows(src, dst, 0, n)
        src, dst = dst, src
    return src


def checksum(grid):
    return hashlib.sha256(np.round(grid, 6).tobytes()).hexdigest()


def run_parallel(pool, n, P, seed):
    shm_a = shared_memory.SharedMemory(create=True, size=n * n * 8)
    shm_b = shared_memory.SharedMemory(create=True, size=n * n * 8)
    try:
        a = np.ndarray((n, n), dtype=np.float64, buffer=shm_a.buf)
        b = np.ndarray((n, n), dtype=np.float64, buffer=shm_b.buf)
        a[:] = init_grid(n, seed)
        b[:] = a
        parts = chunks(n, P)
        t0 = time.perf_counter_ns()
        src_is_a = True
        for _ in range(STEPS):
            if P == 1:
                stencil_rows(a if src_is_a else b, b if src_is_a else a, 0, n)
            else:
                pool.map(worker, [(shm_a.name, shm_b.name, n, src_is_a, r0, r1) for r0, r1 in parts], chunksize=1)
            src_is_a = not src_is_a
        elapsed = time.perf_counter_ns() - t0
        final = (a if src_is_a else b).copy()
        return elapsed, final
    finally:
        shm_a.close(); shm_a.unlink()
        shm_b.close(); shm_b.unlink()


def measure(n, P, seed):
    pool = mp.Pool(P) if P > 1 else None
    try:
        if pool:
            run_parallel(pool, min(n, 256), P, seed)
        times = []
        final = None
        for _ in range(REPEATS):
            t, final = run_parallel(pool, n, P, seed)
            times.append(t)
        return int(statistics.median(times)), final
    finally:
        if pool:
            pool.close(); pool.join()


def amdahl_fit(points):
    num = den = 0.0
    for P, S in points:
        if P < 2:
            continue
        x = 1.0 / P
        y = 1.0 / S
        num += (y - x) * (1 - x)
        den += (1 - x) ** 2
    return num / den if den else float("nan")


def sysctl_int(key):
    try:
        import subprocess
        v = subprocess.check_output(["sysctl", "-n", key], text=True, stderr=subprocess.DEVNULL).strip()
        return int(v) if v.isdigit() else None
    except Exception:
        return None


def physical_cores():
    try:
        with open(os.path.join(RESULTS, "host_profile.json")) as f:
            v = json.load(f)["cores"]["physical"]
        if v:
            return int(v)
    except Exception:
        pass
    return os.cpu_count() or 1


def proc_list(maxp):
    out, p = [], 1
    while p <= maxp:
        out.append(p)
        p *= 2
    if out[-1] != maxp:
        out.append(maxp)
    return out


def main():
    sid = "230103124"
    if "--student-id" in sys.argv:
        sid = sys.argv[sys.argv.index("--student-id") + 1]
    p = get_student_params(sid)
    N, seed = p["N"], p["seed"]
    maxp = physical_cores()
    if "--max-procs" in sys.argv:
        maxp = int(sys.argv[sys.argv.index("--max-procs") + 1])
    plist = proc_list(maxp)
    os.makedirs(RESULTS, exist_ok=True)

    ref = reference(N, seed)
    ref_sum = checksum(ref)

    strong = []
    for P in plist:
        t, final = measure(N, P, seed)
        ok = checksum(final) == ref_sum
        strong.append((P, t, ok))
        print(f"strong P={P} N={N} t={t / 1e9:.3f}s ok={ok}")
    t1 = strong[0][1]
    strong_rows = []
    for P, t, ok in strong:
        S = t1 / t
        strong_rows.append((P, t, S, S / P * 100, ok))
    s_fit = amdahl_fit([(P, S) for P, _, S, _, _ in strong_rows])
    smax = 1.0 / s_fit if s_fit > 0 else float("inf")

    weak = []
    for P in plist:
        nP = math.ceil(N * math.sqrt(P))
        t, final = measure(nP, P, seed)
        refP = reference(nP, seed) if P > 1 else ref
        ok = checksum(final) == checksum(refP)
        weak.append((P, nP, t, ok))
        print(f"weak   P={P} N={nP} t={t / 1e9:.3f}s ok={ok}")
    w1 = weak[0][2]
    work1 = N * N * STEPS

    with open(os.path.join(RESULTS, "scaling_metrics.tsv"), "w") as f:
        f.write("mode\tP\tN\ttime_ns\tspeedup\tefficiency_pct\tscaled_speedup\tweak_efficiency_pct\tamdahl_s_point\tchecksum_ok\n")
        for P, t, S, E, ok in strong_rows:
            sp = ((1 / S) - (1 / P)) / (1 - 1 / P) if P > 1 else float("nan")
            sps = f"{sp:.6f}" if P > 1 else "NA"
            f.write(f"strong\t{P}\t{N}\t{t}\t{S:.4f}\t{E:.2f}\tNA\tNA\t{sps}\t{int(ok)}\n")
        for P, nP, t, ok in weak:
            workP = nP * nP * STEPS
            scaled = P * work1 * w1 / (workP * t)
            f.write(f"weak\t{P}\t{nP}\t{t}\tNA\tNA\t{scaled:.4f}\t{scaled / P * 100:.2f}\tNA\t{int(ok)}\n")
        f.write(f"amdahl_fit\t-\t{N}\t-\t{smax:.4f}\t-\t-\t-\t{s_fit:.6f}\t-\n")

    bw_bytes_per_s = None
    try:
        with open(os.path.join(RESULTS, "stride_results.tsv")) as f:
            next(f)
            first = next(f).split("\t")
            bw_bytes_per_s = float(first[4]) * 1e9
    except Exception:
        pass

    host = {}
    try:
        with open(os.path.join(RESULTS, "host_profile.json")) as f:
            host = json.load(f)
    except Exception:
        pass
    cpu = host.get("cpu", {})
    simd = cpu.get("simd", [])
    model = cpu.get("model_name", "")
    is_apple = host.get("os", {}).get("system") == "Darwin" and host.get("os", {}).get("machine") == "arm64"
    if is_apple:
        freq_mhz = cpu.get("base_frequency_mhz") or 3200.0
        dp_flops_per_cycle = 16
        v = sysctl_int("hw.perflevel0.physicalcpu")
        fast_cores = min(v, maxp) if v else maxp
    else:
        freq_mhz = cpu.get("base_frequency_mhz") or 3000.0
        dp_flops_per_cycle = 32 if "avx512f" in simd else 16 if "avx2" in simd else 8
        fast_cores = maxp
    peak_gflops = freq_mhz / 1000.0 * dp_flops_per_cycle * fast_cores
    spec_bw = {"Apple M1": 68.25}.get(model)
    bw_used = spec_bw * 1e9 if spec_bw else bw_bytes_per_s
    ai_ideal = FLOPS_PER_CELL / BYTES_PER_CELL_IDEAL
    ai_wa = FLOPS_PER_CELL / 24
    ridge = (peak_gflops * 1e9) / bw_used if bw_used else None
    attain = min(peak_gflops, ai_ideal * bw_used / 1e9) if bw_used else None
    working_set = 2 * N * N * 8
    cache = host.get("cache", {})
    fits = None
    for lvl in ("L1d_bytes", "L2_bytes", "L3_bytes"):
        if cache.get(lvl) and working_set <= cache[lvl]:
            fits = lvl
            break
    regime = "memory-bandwidth bound" if (ridge and ai_ideal < ridge) else "compute bound"
    roof = {
        "kernel": "5-point Jacobi stencil, double precision, ping-pong buffers",
        "N": N,
        "steps": STEPS,
        "flops_per_cell": FLOPS_PER_CELL,
        "dram_bytes_per_cell_ideal": BYTES_PER_CELL_IDEAL,
        "dram_bytes_per_cell_with_write_allocate": 24,
        "arithmetic_intensity": ai_ideal,
        "arithmetic_intensity_flop_per_byte_ideal": ai_ideal,
        "arithmetic_intensity_flop_per_byte_write_allocate": ai_wa,
        "working_set_bytes": working_set,
        "smallest_cache_level_holding_working_set": fits,
        "cache_bytes": cache,
        "peak_gflops_estimate": peak_gflops,
        "peak_flops_assumption": f"{freq_mhz} MHz x {dp_flops_per_cycle} DP FLOP/cycle/core x {fast_cores} fast cores",
        "memory_bandwidth_gbps_used": bw_used / 1e9 if bw_used else None,
        "memory_bandwidth_measured_single_core_gbps": bw_bytes_per_s / 1e9 if bw_bytes_per_s else None,
        "memory_bandwidth_source": "vendor spec peak" if spec_bw else "measured stride-1 read throughput (stride_results.tsv)",
        "ridge_point_flop_per_byte": ridge,
        "roofline_attainable_gflops": attain,
        "regime": regime,
        "amdahl_serial_fraction": s_fit,
        "amdahl_max_speedup": smax,
    }
    with open(os.path.join(RESULTS, "roofline_summary.json"), "w") as f:
        json.dump(roof, f, indent=2)
    print(f"Amdahl s={s_fit:.5f}  Smax={smax:.2f}  regime={regime}")


if __name__ == "__main__":
    mp.set_start_method("spawn")
    main()