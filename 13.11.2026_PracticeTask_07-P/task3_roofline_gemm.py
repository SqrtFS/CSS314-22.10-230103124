import multiprocessing as mp
import random
from multiprocessing import shared_memory

from config import STUDENT_ID, P_PHYS, QUICK, L1D_BYTES, L2_BYTES
from harness import run_benchmark, emit_verify_tag, save_md

BUF = 8 * 10 ** 6 if QUICK else 64 * 10 ** 6
FMA_FLOPS = 6.0e6 if QUICK else 6.0e7
GN = 64 if QUICK else 256
WARM_BW, RUNS_BW = (1, 5)
WARM_G, RUNS_G = (0, 3) if QUICK else (1, 3)
BS_LIST = [8, 16, 32, 64, 96, 128]

_mv_a = _mv_b = _keep = None


def init_copy(na, nb):
    global _mv_a, _mv_b, _keep
    sa = shared_memory.SharedMemory(name=na)
    sb = shared_memory.SharedMemory(name=nb)
    _keep = (sa, sb)
    _mv_a, _mv_b = sa.buf, sb.buf


def copy_worker(se):
    s, e = se
    _mv_a[s:e] = _mv_b[s:e]
    return 0


def fma_worker(iters):
    b, c = 1.0000001, 1e-9
    a0 = a1 = a2 = a3 = a4 = a5 = a6 = a7 = 1.0
    a8 = a9 = a10 = a11 = a12 = a13 = a14 = a15 = 1.1
    for _ in range(iters):
        a0 = a0 * b + c
        a1 = a1 * b + c
        a2 = a2 * b + c
        a3 = a3 * b + c
        a4 = a4 * b + c
        a5 = a5 * b + c
        a6 = a6 * b + c
        a7 = a7 * b + c
        a8 = a8 * b + c
        a9 = a9 * b + c
        a10 = a10 * b + c
        a11 = a11 * b + c
        a12 = a12 * b + c
        a13 = a13 * b + c
        a14 = a14 * b + c
        a15 = a15 * b + c
    return a0 + a1 + a2 + a3 + a4 + a5 + a6 + a7 + a8 + a9 + a10 + a11 + a12 + a13 + a14 + a15


_A = _B = _C = _shms = None


def init_gemm(na, nb, nc, n):
    global _A, _B, _C, _shms
    _shms = [shared_memory.SharedMemory(name=x) for x in (na, nb, nc)]
    _A, _B, _C = [s.buf[: n * n * 8].cast("d") for s in _shms]


def gemm_worker(task):
    v, bs, r0, r1, N = task
    A, B, C = _A, _B, _C
    if v == 1:
        for i in range(r0, r1):
            ia = i * N
            for j in range(N):
                s = 0.0
                for k in range(N):
                    s += A[ia + k] * B[k * N + j]
                C[ia + j] = s
    elif v == 2:
        for i in range(r0, r1):
            ia = i * N
            for j in range(N):
                C[ia + j] = 0.0
            for k in range(N):
                a_ik = A[ia + k]
                kb = k * N
                for j in range(N):
                    C[ia + j] += a_ik * B[kb + j]
    else:
        for i in range(r0, r1):
            for j in range(N):
                C[i * N + j] = 0.0
        for ii in range(r0, r1, bs):
            imax = min(ii + bs, r1)
            for jj in range(0, N, bs):
                jmax = min(jj + bs, N)
                for kk in range(0, N, bs):
                    kmax = min(kk + bs, N)
                    for i in range(ii, imax):
                        ia = i * N
                        for k in range(kk, kmax):
                            a_ik = A[ia + k]
                            kb = k * N
                            for j in range(jj, jmax):
                                C[ia + j] += a_ik * B[kb + j]
    return 0


def main():
    p = P_PHYS
    out = [f"## Phase 3 - Roofline and GEMM (p = P_phys = {p}, buffers {BUF / 1e6:.0f} MB x2, GEMM N={GN})", ""]

    sa = shared_memory.SharedMemory(create=True, size=BUF)
    sb = shared_memory.SharedMemory(create=True, size=BUF)
    sb.buf[:BUF] = b"\x01" * BUF
    sa.buf[:BUF] = b"\x00" * BUF
    try:
        ranges = [(BUF * t // p, BUF * (t + 1) // p) for t in range(p)]
        with mp.Pool(p, initializer=init_copy, initargs=(sa.name, sb.name)) as pool:
            st = run_benchmark(lambda: pool.map(copy_worker, ranges, chunksize=1), WARM_BW, RUNS_BW)
    finally:
        sa.close()
        sb.close()
        sa.unlink()
        sb.unlink()
    bw = 2 * BUF / ((st.median_ms / 1e3) * 1e9)
    out += ["### 3A - sustained DRAM bandwidth",
            f"- median {st.median_ms:.2f} ms (IQR {st.iqr_ms:.2f}) -> BW_sustained = {bw:.2f} GB/s", ""]
    print(out[-2], flush=True)

    iters = int(FMA_FLOPS / 32)
    with mp.Pool(p) as pool:
        st = run_benchmark(lambda: pool.map(fma_worker, [iters] * p, chunksize=1), 1, 3)
    psus = p * iters * 32 / ((st.median_ms / 1e3) * 1e9)
    ridge = psus / bw
    out += ["### 3A - compute ceiling",
            f"- median {st.median_ms:.1f} ms -> P_sustained = {psus:.4f} GFLOP/s (aggregate over {p} procs)",
            f"- Ridge point I* = P/BW = {ridge:.5f} FLOP/byte", ""]
    print(out[-3], flush=True)

    N = GN
    nbytes = N * N * 8
    shm = [shared_memory.SharedMemory(create=True, size=nbytes) for _ in range(3)]
    memA, memB, memC = [s.buf[:nbytes].cast("d") for s in shm]
    rng = random.Random(STUDENT_ID)
    for i in range(N * N):
        memA[i] = rng.uniform(-1, 1)
        memB[i] = rng.uniform(-1, 1)
    rows = [(N * t // p, N * (t + 1) // p) for t in range(p)]

    def run_variant(pool, v, bs):
        return run_benchmark(
            lambda: pool.map(gemm_worker, [(v, bs, r0, r1, N) for r0, r1 in rows], chunksize=1),
            WARM_G, RUNS_G)

    def gflops(ms):
        return 2 * N ** 3 / (ms * 1e6)

    res = {}
    try:
        with mp.Pool(p, initializer=init_gemm, initargs=(shm[0].name, shm[1].name, shm[2].name, N)) as pool:
            st1 = run_variant(pool, 1, 0)
            C1 = memC.tolist()
            st2 = run_variant(pool, 2, 0)
            C2 = memC.tolist()
            res["v1"], res["v2"] = st1, st2
            d12 = max(abs(x - y) for x, y in zip(C1, C2))
            out += ["### 3B - variants (N=%d)" % N, "",
                    "| variant | median ms | IQR ms | GFLOP/s | I_eff = GFLOP/s / BW |", "|---|---|---|---|---|",
                    f"| 1 naive i-j-k | {st1.median_ms:.1f} | {st1.iqr_ms:.1f} | {gflops(st1.median_ms):.4f} | {gflops(st1.median_ms) / bw:.5f} |",
                    f"| 2 i-k-j | {st2.median_ms:.1f} | {st2.iqr_ms:.1f} | {gflops(st2.median_ms):.4f} | {gflops(st2.median_ms) / bw:.5f} |",
                    "", f"max|C1-C2| = {d12:.3e}", "",
                    "### 3B - tile sweep (Variant 3)", "",
                    "| BS | W_tile KiB | fits | median ms | IQR ms | GFLOP/s | max|C3-C2| | I_tiled=BS/12 | roof=min(P,I*BW) |",
                    "|---|---|---|---|---|---|---|---|---|"]
            print("\n".join(out[-9:]), flush=True)
            sweep = {}
            for bs in BS_LIST:
                st3 = run_variant(pool, 3, bs)
                d = max(abs(x - y) for x, y in zip(memC.tolist(), C2))
                w = 3 * bs * bs * 8
                fit = "L1d" if w <= L1D_BYTES else ("L2" if w <= L2_BYTES else ">L2")
                it = bs / 12
                roof = min(psus, it * bw)
                ok = "OK" if d < 1e-9 else "FAIL"
                sweep[bs] = st3
                out.append(f"| {bs} | {w / 1024:.1f} | {fit} | {st3.median_ms:.1f} | {st3.iqr_ms:.1f} | "
                           f"{gflops(st3.median_ms):.4f} | {d:.1e} {ok} | {it:.2f} | {roof:.4f} |")
                print(out[-1], flush=True)
    finally:
        for m in (memA, memB, memC):
            m.release()
        for s in shm:
            try:
                s.close()
            except BufferError:
                pass
            s.unlink()

    best = min(sweep, key=lambda b: sweep[b].median_ms)
    g1, g3 = gflops(res["v1"].median_ms), gflops(sweep[best].median_ms)
    out += ["", f"BS* = {best} (W_tile = {3 * best * best * 8 / 1024:.1f} KiB; "
                f"L1d = {L1D_BYTES // 1024} KiB, L2 = {L2_BYTES // 1024} KiB)",
            f"Variant 1 = {g1:.4f} GFLOP/s, Variant 3 (BS*) = {g3:.4f} GFLOP/s, speedup x{g3 / g1:.2f}", ""]
    print(out[-3], flush=True)
    print(out[-2], flush=True)
    tag = emit_verify_tag("PHASE3", STUDENT_ID, g1, g3)
    out.append(tag)
    print(tag)
    save_md("results_task3.md", out)


if __name__ == "__main__":
    main()
