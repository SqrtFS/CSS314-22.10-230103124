import os, statistics, sys, time
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS = os.path.join(ROOT, "results")
STRIDES = [1, 2, 4, 8, 16, 32, 64, 128]
WARMUP = 5
RUNS = 5


def read_strided(view):
    return view.sum()


def main():
    os.makedirs(RESULTS, exist_ok=True)
    data = np.ones(16_777_216, dtype=np.float64)
    rows = []
    for s in STRIDES:
        view = data[::s]
        touched = view.shape[0]
        for _ in range(WARMUP):
            read_strided(view)
        times = []
        for _ in range(RUNS):
            t0 = time.perf_counter_ns()
            total = read_strided(view)
            t1 = time.perf_counter_ns()
            times.append(t1 - t0)
        assert total == touched
        med = int(statistics.median(times))
        rows.append((s, touched, med, med / touched, touched * 8 / med))
    base = rows[0][3]
    with open(os.path.join(RESULTS, "stride_results.tsv"), "w") as f:
        f.write("stride\telements_touched\tmedian_time_ns\tlatency_per_element_ns\tuseful_GBps\trelative_to_stride1\n")
        for s, n, t, lat, bw in rows:
            f.write(f"{s}\t{n}\t{t}\t{lat:.4f}\t{bw:.3f}\t{lat / base:.2f}\n")
    for s, n, t, lat, bw in rows:
        print(f"stride {s:>3}  touched {n:>9}  median {t / 1e6:9.3f} ms  {lat:7.3f} ns/elem  {lat / base:6.2f}x")


if __name__ == "__main__":
    main()