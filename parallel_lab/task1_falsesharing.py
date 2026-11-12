import multiprocessing as mp
from multiprocessing import shared_memory
import ctypes
import time
from harness import run_benchmark, emit_verify_tag


def fs_worker(shm_name, slot_idx, iters):
    shm = shared_memory.SharedMemory(name=shm_name)
    arr = (ctypes.c_uint64 * 512).from_buffer(shm.buf)
    acc = arr[slot_idx]
    mask = 0xFFFFFFFFFFFFFFFF
    mult = 6364136223846793005
    for i in range(iters):
        acc = (acc * mult + (i + 1)) & mask
    arr[slot_idx] = acc
    del arr
    shm.close()


def run_experiment(p, stride, total_iters=24_000_000):
    iters_per_worker = total_iters // p
    shm = shared_memory.SharedMemory(create=True, size=4096)
    try:
        arr = (ctypes.c_uint64 * 512).from_buffer(shm.buf)
        for i in range(512):
            arr[i] = 0
        del arr

        def job():
            processes = []
            for t in range(p):
                slot_idx = t * stride
                p_proc = mp.Process(target=fs_worker, args=(shm.name, slot_idx, iters_per_worker))
                processes.append(p_proc)
                p_proc.start()
            for p_proc in processes:
                p_proc.join()

        stats = run_benchmark(job, warmup_runs=2, timed_runs=7)
        return stats
    finally:
        shm.close()
        shm.unlink()


if __name__ == "__main__":
    student_seed = 230103124
    p_phys = 8

    print("--- Table 1A: Stride Sweep at p = 8 ---")
    strides = [1, 2, 4, 8, 16, 32]
    table1a_results = {}
    for s in strides:
        stats = run_experiment(p=p_phys, stride=s)
        throughput = 24.0 / (stats.median_ms / 1000.0)
        table1a_results[s] = stats.median_ms
        print(
            f"Stride: {s:2d} (Bytes: {s * 8:3d}) | Median: {stats.median_ms:8.2f} ms | Throughput: {throughput:6.2f} Mops/s")

    print("\n--- Table 1B: Process Scaling Sweep (Stride = 1 vs Stride = 16) ---")
    p_list = [1, 2, 4, 8]

    print("\n[Stride = 1]")
    t1_stride1 = None
    for p in p_list:
        stats = run_experiment(p=p, stride=1)
        if p == 1:
            t1_stride1 = stats.median_ms
        sp = t1_stride1 / stats.median_ms
        ep = sp / p
        kf = (1.0 / ep - 1.0) / (p - 1.0) if p > 1 else 0.0
        print(f"p={p} | Median: {stats.median_ms:8.2f} ms | Sp: {sp:5.2f} | Ep: {ep:5.2f} | Karp-Flatt e(p): {kf:6.4f}")

    print("\n[Stride = 16]")
    t1_stride16 = None
    for p in p_list:
        stats = run_experiment(p=p, stride=16)
        if p == 1:
            t1_stride16 = stats.median_ms
        sp = t1_stride16 / stats.median_ms
        ep = sp / p
        kf = (1.0 / ep - 1.0) / (p - 1.0) if p > 1 else 0.0
        print(f"p={p} | Median: {stats.median_ms:8.2f} ms | Sp: {sp:5.2f} | Ep: {ep:5.2f} | Karp-Flatt e(p): {kf:6.4f}")

    med_s1 = table1a_results[1]
    med_s16 = table1a_results[16]
    verify_tag = emit_verify_tag("PHASE1", student_seed, med_s1, med_s16)
    print("\n" + verify_tag)