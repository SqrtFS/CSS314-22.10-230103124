import ctypes
import multiprocessing as mp
import time
from multiprocessing import shared_memory

from config import STUDENT_ID, P_PHYS, QUICK, CACHE_LINE
from harness import stats_from_samples, emit_verify_tag, p_series, save_md

M = 1_600_000 if QUICK else 16_000_000
WARMUP, RUNS = (0, 3) if QUICK else (1, 5)
STRIDES = [1, 2, 4, 8, 16, 32]


def fs_worker(shm_name, slot_idx, iters, n_slots, barrier):
    shm = shared_memory.SharedMemory(name=shm_name)
    arr = (ctypes.c_uint64 * n_slots).from_buffer(shm.buf)
    acc = arr[slot_idx]
    barrier.wait(120)
    for i in range(iters):
        acc = (acc * 6364136223846793005 + (i | 1)) & 0xFFFFFFFFFFFFFFFF
        arr[slot_idx] = acc
    del arr
    shm.close()


def run_once(p, stride):
    n_slots = max(512, p * stride)
    shm = shared_memory.SharedMemory(create=True, size=n_slots * 8)
    try:
        barrier = mp.Barrier(p + 1)
        iters = M // p
        procs = [
            mp.Process(target=fs_worker,
                       args=(shm.name, t * stride, iters, n_slots, barrier))
            for t in range(p)
        ]
        for pr in procs:
            pr.start()
        barrier.wait(120)
        t0 = time.perf_counter_ns()
        for pr in procs:
            pr.join()
        return (time.perf_counter_ns() - t0) / 1e6
    finally:
        shm.close()
        shm.unlink()


def measure(p, stride):
    for _ in range(WARMUP):
        run_once(p, stride)
    return stats_from_samples([run_once(p, stride) for _ in range(RUNS)])


def karp_flatt(sp, p):
    return (1.0 / sp - 1.0 / p) / (1.0 - 1.0 / p)


def main():
    plog = mp.cpu_count()
    out = [f"## Phase 1 - false sharing (M={M}, P_phys={P_PHYS}, P_log={plog})", ""]

    out += [f"### Stride sweep, p = {P_PHYS}", "",
            "| stride | bytes | median ms | IQR ms | Mops/s |",
            "|---|---|---|---|---|"]
    sweep = {}
    for st in STRIDES:
        s = measure(P_PHYS, st)
        sweep[st] = s
        mops = M / (s.median_ms * 1e3)
        out.append(f"| {st} | {st * 8} | {s.median_ms:.1f} | {s.iqr_ms:.1f} | {mops:.2f} |")
        print(out[-1], flush=True)
    drops = [(STRIDES[i], STRIDES[i + 1], sweep[STRIDES[i]].median_ms / sweep[STRIDES[i + 1]].median_ms)
             for i in range(len(STRIDES) - 1)]
    a, b, r = max(drops, key=lambda x: x[2])
    out += ["", f"Largest drop in time: stride {a} ({a * 8} B) -> stride {b} ({b * 8} B), x{r:.2f} faster. "
                f"Cache line = {CACHE_LINE} B (stride {CACHE_LINE // 8}).", ""]
    print(out[-2], flush=True)

    ps = p_series(plog)
    t1 = {}
    for st in (1, 16):
        out += [f"### Process scaling, stride = {st}", "",
                "| p | median ms | IQR ms | S_p | E_p | Karp-Flatt e(p) |",
                "|---|---|---|---|---|---|"]
        for p in ps:
            s = measure(p, st)
            if p == 1:
                t1[st] = s.median_ms
            sp = t1[st] / s.median_ms
            ep = sp / p
            e = f"{karp_flatt(sp, p):.4f}" if p >= 2 else "-"
            out.append(f"| {p} | {s.median_ms:.1f} | {s.iqr_ms:.1f} | {sp:.2f} | {ep:.2f} | {e} |")
            print(out[-1], flush=True)
        out.append("")

    tag = emit_verify_tag("PHASE1", STUDENT_ID, sweep[1].median_ms, sweep[16].median_ms)
    out += [tag]
    print(tag)
    save_md("results_task1.md", out)


if __name__ == "__main__":
    main()
