import ctypes, json, multiprocessing as mp, os, statistics, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
K = 5_000_000
PROCS = [1, 2, 4, 8]
REPEATS = 3


def detect_line():
    try:
        with open(os.path.join(RESULTS, "host_profile.json")) as f:
            v = json.load(f)["cache"]["line_size_bytes"]
        if v and v % 8 == 0:
            return int(v)
    except Exception:
        pass
    return 64


LINE = detect_line()
SLOTS = LINE // 8


def aligned_base(arr):
    addr = ctypes.addressof(arr)
    return ((-addr) % LINE) // 8


def worker_unpadded(arr, base, wid, iterations, barrier):
    barrier.wait()
    idx = base + wid
    for _ in range(iterations):
        arr[idx] += 1


def worker_padded(arr, base, wid, iterations, barrier):
    barrier.wait()
    idx = base + wid * SLOTS
    for _ in range(iterations):
        arr[idx] += 1


def worker_privatized(arr, base, wid, iterations, barrier):
    barrier.wait()
    local = 0
    for _ in range(iterations):
        local += 1
    arr[base + wid * SLOTS] = local


def run_variant(target, stride_slots, P):
    arr = mp.RawArray(ctypes.c_int64, 10 * SLOTS)
    base = aligned_base(arr)
    barrier = mp.Barrier(P + 1)
    procs = [mp.Process(target=target, args=(arr, base, p, K, barrier)) for p in range(P)]
    for pr in procs:
        pr.start()
    barrier.wait()
    t0 = time.perf_counter_ns()
    for pr in procs:
        pr.join()
    elapsed = time.perf_counter_ns() - t0
    total = sum(arr[base + p * stride_slots] for p in range(P))
    return elapsed, total


def karp_flatt(t1, tp, P):
    return ((P * tp / t1) - 1.0) / (P - 1)


def main():
    os.makedirs(RESULTS, exist_ok=True)
    print(f"cache line = {LINE} bytes, padding stride = {SLOTS} int64")
    variants = [
        ("unpadded", worker_unpadded, 1),
        ("padded", worker_padded, SLOTS),
        ("privatized", worker_privatized, SLOTS),
    ]
    medians = {}
    rows = []
    for name, target, stride in variants:
        for P in PROCS:
            times, totals = [], []
            for _ in range(REPEATS):
                t, tot = run_variant(target, stride, P)
                times.append(t)
                totals.append(tot)
            med = int(statistics.median(times))
            medians[(name, P)] = med
            ok = all(t == P * K for t in totals)
            rows.append({"variant": name, "P": P, "median_ns": med, "runs_ns": times, "total": totals[0], "expected": P * K, "ok": ok})
            print(f"{name:<11} P={P}  median {med / 1e9:7.3f} s  total {totals[0]} {'OK' if ok else 'MISMATCH'}")

    with open(os.path.join(RESULTS, "false_sharing_karp_flatt.tsv"), "w") as f:
        f.write("variant\tP\tmedian_time_ns\trun1_ns\trun2_ns\trun3_ns\tspeedup\tefficiency\tkarp_flatt_e\ttotal_count\texpected_count\tcount_ok\n")
        for r in rows:
            name, P = r["variant"], r["P"]
            t1 = medians[(name, 1)]
            tp = r["median_ns"]
            sp = t1 / tp
            eff = sp / P
            e = karp_flatt(t1, tp, P) if P > 1 else float("nan")
            es = f"{e:.6f}" if P > 1 else "NA"
            f.write(f"{name}\t{P}\t{tp}\t{r['runs_ns'][0]}\t{r['runs_ns'][1]}\t{r['runs_ns'][2]}\t{sp:.4f}\t{eff:.4f}\t{es}\t{r['total']}\t{r['expected']}\t{int(r['ok'])}\n")
            if P > 1:
                print(f"{name:<11} P={P}  S={sp:6.3f}  e={e:8.4f}")


if __name__ == "__main__":
    mp.set_start_method("spawn")
    main()