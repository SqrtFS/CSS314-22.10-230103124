import math
import multiprocessing as mp
import time

from config import STUDENT_ID, P_PHYS, QUICK
from harness import emit_verify_tag, save_md

N = 800 if QUICK else 8000
RUNS = 3
CHUNKS = [1, 8, 64, 512]


def work_item(i):
    k = 1 + (i * i) // 1600
    x = 0.001 * i + 0.5
    acc = 0.0
    for _ in range(k):
        x = math.sin(x) + math.cos(x)
        acc += math.sqrt(abs(x) + 1.0)
    return acc


def static_worker(t, p, mode, tw, barrier):
    idx = range(N * t // p, N * (t + 1) // p) if mode == "block" else range(t, N, p)
    barrier.wait(300)
    t0 = time.perf_counter()
    acc = 0.0
    for i in idx:
        acc += work_item(i)
    tw[t] = time.perf_counter() - t0


def dynamic_worker(t, chunk, counter, tw, barrier):
    barrier.wait(300)
    t0 = time.perf_counter()
    acc = 0.0
    while True:
        with counter.get_lock():
            start = counter.value
            counter.value = start + chunk
        if start >= N:
            break
        for i in range(start, min(start + chunk, N)):
            acc += work_item(i)
    tw[t] = time.perf_counter() - t0


def run_config(kind, p, chunk=None):
    tw = mp.Array("d", p)
    barrier = mp.Barrier(p + 1)
    if kind == "dynamic":
        counter = mp.Value("i", 0)
        procs = [mp.Process(target=dynamic_worker, args=(t, chunk, counter, tw, barrier)) for t in range(p)]
    else:
        procs = [mp.Process(target=static_worker, args=(t, p, kind, tw, barrier)) for t in range(p)]
    for pr in procs:
        pr.start()
    barrier.wait(300)
    t0 = time.perf_counter()
    for pr in procs:
        pr.join()
    wall = time.perf_counter() - t0
    times = list(tw)
    lam = max(times) / (sum(times) / p)
    return wall * 1e3, lam, times


def median_run(kind, p, chunk=None):
    runs = sorted((run_config(kind, p, chunk) for _ in range(RUNS)), key=lambda r: r[0])
    return runs[RUNS // 2]


def main():
    p = P_PHYS
    total_items = sum(1 + (i * i) // 1600 for i in range(N))
    out = [f"## Phase 4 - scheduling (N={N}, p={p}, total heavy iterations = {total_items})", "",
           "| strategy | T_wall ms | lambda | min worker s | max worker s |", "|---|---|---|---|---|"]
    results = {}
    configs = [("block", None, "Block static"), ("cyclic", None, "Cyclic static")] + \
              [("dynamic", c, f"Dynamic C={c}") for c in CHUNKS]
    for kind, c, label in configs:
        wall, lam, times = median_run(kind, p, c)
        results[label] = (wall, lam)
        out.append(f"| {label} | {wall:.1f} | {lam:.3f} | {min(times):.3f} | {max(times):.3f} |")
        print(out[-1], flush=True)
    best_label = min((l for l in results if l.startswith("Dynamic")), key=lambda l: results[l][0])
    out += ["", f"C* = {best_label.split('=')[1]} (lowest T_wall among dynamic)", ""]
    print(out[-2], flush=True)
    tag = emit_verify_tag("PHASE4", STUDENT_ID, results["Block static"][0], results[best_label][0])
    out.append(tag)
    print(tag)
    save_md("results_task4.md", out)


if __name__ == "__main__":
    main()
