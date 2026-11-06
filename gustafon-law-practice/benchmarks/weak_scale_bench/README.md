# Weak-scaling benchmark (Task 22)

Synthetic numerical workload: midpoint-rule integration of `4/(1+x²)` on `[0,1]`.
Every thread integrates its own sub-interval with a **constant** `k` steps, so total work = `k × threads`.
A fixed-size single-threaded initialisation (`--serial-n`) supplies a known serial fraction.

## Build
```bash
make            # g++ -O2 -fopenmp -std=c++17
# or: g++ -O2 -fopenmp -std=c++17 weak_scale_bench.cpp -o weak_scale_bench
```

## Single run
```bash
./weak_scale_bench --threads 8 --k 100000000 --serial-n 1000000 --header
```

## Full sweep (Task 23)
```bash
python3 run_bench.py --runs 5                 # auto thread list: powers of two up to hw concurrency
python3 run_bench.py --threads 1 2 4 8 16 32  # explicit list
```
Pin threads for reproducible results on real hardware:
`OMP_PROC_BIND=close OMP_PLACES=cores python3 run_bench.py` (use `numactl --interleave=all` or one-socket runs to test NUMA effects).

Output: `../results.csv`. Analyse with `../fit_gustafson.py`, plot with `../plot_scaling.py`.
