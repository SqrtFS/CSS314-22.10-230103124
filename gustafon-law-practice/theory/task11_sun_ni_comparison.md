# Task 11 — Sun–Ni Memory-Bounded Speedup vs. Gustafson

## 1. Formulations

Let `s`, `p = 1−s` be the serial/parallel fractions of the **single-node** problem and let `G(P)` be the factor by which the parallel workload grows when the memory grows `P`-fold.

| Model | Workload growth | Speedup |
|---|---|---|
| Amdahl (fixed-size) | `G(P) = 1` | `1 / (s + p/P)` |
| Gustafson (fixed-time) | `G(P) = P` | `s + pP` |
| **Sun–Ni (memory-bounded)** | `G(P)` = whatever fills `P×` memory | `S* = (s + p·G(P)) / (s + p·G(P)/P)` |

Check: `G = 1` → Amdahl. `G = P` → `(s + pP)/(s + p) = s + pP` → Gustafson. So both classic laws are special cases.

## 2. Where `G(P)` comes from

If the work is `W = N^a` and the memory needed is `M = N^b`, a machine with `P×` the memory can hold a problem with `N' = N·P^{1/b}`, so:

```
N' = N·P^{1/b}   →   G(P) = (N'/N)^a = P^{a/b}
```

| Kernel | work `a` | memory `b` | `G(P)` | Relation to Gustafson |
|---|---|---|---|---|
| Vector ops / stencil sweep | 3 (3D, per step) | 3 | `P` | equal |
| Dense GEMM | 3 | 2 | `P^{3/2}` | `G > P` |
| Direct N-body | 2 | 1 | `P²` | `G ≫ P` |
| FFT | `N log N` | `N` | `≈ P log P` | slightly above |
| Algorithm with replicated data | `a` | grows with `P` | `< P` | `G < P` |

## 3. When Gustafson **under**estimates achievable throughput

If compute grows faster than memory (`a > b`, e.g. GEMM, N-body), filling memory yields *more* work than a fixed-time rule would permit, so `G(P) > P`. Sun–Ni then predicts a higher speedup than Gustafson: `S* ≥ s + pP`. The catch is that **runtime is no longer constant**: it grows as `P^{a/b − 1}` (for GEMM, `√P`). Gustafson's prediction is then the right answer for a *different* question (how much work fits in the time budget), not a prediction for the memory-filling run. Equivalent statement: Gustafson underestimates the *work completed* when users are happy to wait longer.

## 4. When Gustafson **over**estimates

1. **Memory-limited workloads, `G(P) < P`.** If memory per node must shrink with `P` (replicated global tables, ghost-cell blow-up, per-rank buffers `O(P)`), usable problem growth is below `P`, so the fixed-time assumption cannot be met, and `S* < s + pP`.
2. **Overheads that grow with `P`** (communication `O(log P)` or `O(√P)`, load imbalance, contention). Both Gustafson and Sun–Ni in the form above ignore this term (Task 12).
3. **Algorithmic complexity changes.** Iteration counts rising with problem size (CG, Task 13), so work doesn't grow `∝ P` for fixed time.
4. **I/O and checkpoint volume** that scales with total memory but cannot be parallelised past the file-system bandwidth.
5. **Single-node infeasibility.** The one-node time `s + pP` used in the derivation is never measured, only extrapolated. If caching effects make the real single-node run much slower (spilling to disk) the "speedup" is inflated (super-linear artefacts).

## 5. Worked example (GEMM, `s = 0.02`, `P = 64`)

* Gustafson: `S = 0.02 + 0.98·64 = 62.74`
* Sun–Ni: `G = 64^{1.5} = 512`; `S* = (0.02 + 0.98·512)/(0.02 + 0.98·512/64) = 501.8/7.86 = 63.84`

Sun–Ni gives a slightly higher efficiency (99.7 % vs 98.0 %) because the serial part is amortised over 8× more work than in Gustafson's regime, but the run takes `512/64 = 8×` longer than a single-node run.

## 6. Take-away

Gustafson assumes the *time* constraint binds; Sun–Ni assumes the *memory* constraint binds. The tighter of the two actually limits growth: take `G(P) = min(G_time(P), G_memory(P))`. A design checklist: compute both growth rates for your kernel and see which one you hit first.
