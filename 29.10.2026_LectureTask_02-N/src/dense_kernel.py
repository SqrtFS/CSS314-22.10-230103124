import json, os, statistics, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from salt import get_student_params

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")

try:
    from numba import njit
    BACKEND = "numba"
except Exception:
    BACKEND = "python"

    def njit(*a, **k):
        if a and callable(a[0]):
            return a[0]
        return lambda f: f


@njit(cache=True, fastmath=False)
def mm_ijk(A, B, C, N, M):
    for i in range(M):
        for j in range(M):
            acc = 0.0
            for k in range(M):
                acc += A[i * N + k] * B[k * N + j]
            C[i * N + j] = acc


@njit(cache=True, fastmath=False)
def mm_ikj(A, B, C, N, M):
    for i in range(M):
        for j in range(M):
            C[i * N + j] = 0.0
        for k in range(M):
            a = A[i * N + k]
            for j in range(M):
                C[i * N + j] += a * B[k * N + j]


def timed(fn, A, B, C, N, M, runs=3):
    times = []
    for _ in range(runs):
        C[:] = 0.0
        t0 = time.perf_counter_ns()
        fn(A, B, C, N, M)
        times.append(time.perf_counter_ns() - t0)
    return statistics.median(times), times


def main():
    sid = "230103124"
    if "--student-id" in sys.argv:
        sid = sys.argv[sys.argv.index("--student-id") + 1]
    p = get_student_params(sid)
    N = p["N"]
    M = N // 2
    rng = np.random.default_rng(p["seed"])
    A = rng.random(N * N)
    B = rng.random(N * N)
    C1 = np.zeros(N * N)
    C2 = np.zeros(N * N)

    if BACKEND == "python":
        M = 128
        A = A.tolist(); B = B.tolist(); C1 = C1.tolist(); C2 = C2.tolist()
    else:
        mm_ijk(A, B, C1, N, 8)
        mm_ikj(A, B, C2, N, 8)

    t_naive, naive_runs = timed(mm_ijk, A, B, C1, N, M)
    t_inter, inter_runs = timed(mm_ikj, A, B, C2, N, M)

    c1 = np.asarray(C1).reshape(N, N)[:M, :M]
    c2 = np.asarray(C2).reshape(N, N)[:M, :M]
    max_abs_diff = float(np.max(np.abs(c1 - c2)))
    ref = np.asarray(A).reshape(N, N)[:M, :M] @ np.asarray(B).reshape(N, N)[:M, :M]
    max_abs_diff_blas = float(np.max(np.abs(c2 - ref)))

    out = {
        "student_id": sid,
        "N": N,
        "block_M": M,
        "backend": BACKEND,
        "runs": 3,
        "t_naive_ijk_ns_median": t_naive,
        "t_interchanged_ikj_ns_median": t_inter,
        "t_naive_ijk_ns_all": naive_runs,
        "t_interchanged_ikj_ns_all": inter_runs,
        "speedup_S": t_naive / t_inter,
        "naive_time_s": t_naive / 1e9,
        "interchanged_time_s": t_inter / 1e9,
        "speedup": t_naive / t_inter,
        "max_abs_diff_ijk_vs_ikj": max_abs_diff,
        "max_abs_diff_vs_numpy_matmul": max_abs_diff_blas,
        "result_digest_6dp_sum": round(float(c2.sum()), 6),
    }
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "loop_interchange.json"), "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()