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


def karp_flatt_scaled(t1, tp, P):
    return (tp / t1 - 1.0) / (P - 1)


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
        names = [v[0] for v in variants]
        cols = ["P"]
        for n in names:
            cols += [f"T_{n}_ns", f"runs_{n}_ns", f"S_{n}"]
        for n in names:
            cols.append(f"e_{n}")
        for n in names:
            cols.append(f"e_{n}_scaled")
        cols += ["expected_count", "count_ok"]
        f.write("\t".join(cols) + "\n")
        for P in PROCS:
            cells = [str(P)]
            for n in names:
                t1 = medians[(n, 1)]
                tp = medians[(n, P)]
                runs = next(r["runs_ns"] for r in rows if r["variant"] == n and r["P"] == P)
                cells += [str(tp), ",".join(str(x) for x in runs), f"{t1 / tp:.4f}"]
            for n in names:
                cells.append(f"{karp_flatt(medians[(n, 1)], medians[(n, P)], P):.6f}" if P > 1 else "NA")
            for n in names:
                cells.append(f"{karp_flatt_scaled(medians[(n, 1)], medians[(n, P)], P):.6f}" if P > 1 else "NA")
            ok = all(r["ok"] for r in rows if r["P"] == P)
            cells += [str(P * K), str(int(ok))]
            f.write("\t".join(cells) + "\n")
    for P in PROCS[1:]:
        for n in names:
            t1 = medians[(n, 1)]
            tp = medians[(n, P)]
            print(f"{n:<11} P={P}  S={t1 / tp:6.3f}  e={karp_flatt(t1, tp, P):8.4f}  e_scaled={karp_flatt_scaled(t1, tp, P):7.4f}")


if __name__ == "__main__":
    mp.set_start_method("spawn")
    main()