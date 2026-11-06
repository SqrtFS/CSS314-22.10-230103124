# Task 19 — Monte Carlo Path Simulation: The Ideal Weak-Scaling Model

Monte Carlo (MC) is embarrassingly parallel: each of `P` ranks simulates `n` independent paths (`N = nP` total). Statistical error falls as `1/√N`, so weak scaling is "more samples in the same time → smaller error".

## 1. Sources of non-zero serial fraction `α`

| Source | Scaling | Typical size | Mitigation |
|---|---|---|---|
| **PRNG seed management**, master draws seeds and sends them sequentially | `O(P)` serial | 1 µs × P | Counter-based RNG (Philox, Threefry) or skip-ahead: stream = `f(global_seed, rank)`; computed locally, `O(1)`; guarantees non-overlapping streams and results independent of `P` |
| Program start-up, config read, model calibration | `O(1)` | 10–100 ms | Read once + broadcast; or replicate |
| **Result reduction** (sum, sum of squares, histograms) | `O(log P)` tree, `O(P)` chain | µs–ms | Tree/ butterfly reductions, hierarchical (node-level then global) |
| **Output serialisation**, rank 0 writes the result/paths; or gathers per-rank files | `O(P·bytes/BW)` | up to 100s ms | Parallel I/O (MPI-IO, HDF5), write only aggregates |
| Load imbalance, e.g. variable-length paths, early termination | `O(max − mean)` | few % | Dynamic work stealing, batching |
| Barrier / final synchronisation | `O(log P)` | µs | — |

## 2. Quantifying the reduction tree

Per-level message cost `t_c` (latency + a few bytes at 50 µs, including software overhead). A binomial tree needs `⌈log₂P⌉` levels, a naive linear gather needs `P−1`.

Assume run time `T = 100 s`, serial start-up/finish `s₀ = 50 ms`:

```
α(P) = (s₀ + t_red(P)) / T
S(P) = P − α(P)(P−1)
```

| P | Levels | `t_red` (tree) | `α` | `S(P)` | `E` |
|---:|---:|---:|---:|---:|---:|
| 64 | 6 | 0.30 ms | 5.03·10⁻⁴ | 63.968 | 99.950 % |
| 1 024 | 10 | 0.50 ms | 5.05·10⁻⁴ | 1 023.48 | 99.950 % |
| 16 384 | 14 | 0.70 ms | 5.07·10⁻⁴ | 16 375.7 | 99.949 % |
| 65 536 | 16 | 0.80 ms | 5.08·10⁻⁴ | 65 502.7 | 99.949 % |

The tree reduction adds `< 0.001 %` to `α`: **negligible**, since `log₂P` grows slowly; the 50 ms start-up dominates.

### Counter-examples

* **Linear (chain) reduction** at `P = 65 536`: `t_red = 65 535 × 50 µs = 3.28 s` → `α = 0.0333`, `S = 63 356`, `E = 96.7 %`. That is a loss of ≈ 2 180 cores' worth, caused by an algorithmic choice.
* **Serialised output**, rank 0 receives 1 KB from each of 65 536 ranks at 1 GB/s: `64 ms` → `α = 1.16·10⁻³`, `S = 65 460`, `E = 99.88 %`. It exceeds the whole 50 ms start-up, but the effect is still minor.
* **Sequential seeding** from the master: `P × 1 µs = 65 ms` at `P = 65 536`, comparable to `s₀`.

## 3. Conclusions

1. MC reaches Gustafson's ideal: `E ≈ 1 − α` with `α ~ 10⁻³–10⁻⁴`.
2. The serial fraction is dominated by `O(1)` start-up and `O(P)` I/O, rarely by the reduction tree.
3. Pitfalls are **correctness**, not speed: overlapping RNG streams, results that depend on `P` (loss of reproducibility), floating-point sum order (use deterministic reduction orders or compensated/Kahan or integer accumulators).
4. Variance reduction techniques (antithetic, quasi-MC / Sobol) require coordinated sequences, so they add some synchronisation in sequence partitioning, but still `O(1)`.
