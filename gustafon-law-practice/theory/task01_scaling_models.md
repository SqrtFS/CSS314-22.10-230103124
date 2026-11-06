# Task 01 — Strong Scaling vs. Weak Scaling Foundations

## Notation
* `P` — number of processing units
* `s`, `p` — serial / parallelizable fractions (`s + p = 1`)
* `W` — total problem size (amount of work)
* `T(P, W)` — wall-clock runtime of problem `W` on `P` processors

## 1. The two models in one table

| Aspect | Amdahl (1967) | Gustafson–Barsis (1988) |
|---|---|---|
| Question asked | "How much faster can I solve *this* problem?" | "How much *more* problem can I solve in *this* time?" |
| Held constant | Total workload `W` | Wall-clock runtime `T` |
| Behaviour of `W` as `P → ∞` | `W` fixed: `W(P) = W₀` | `W` grows: `W(P) = W₀·(s + p·P)`, i.e. `Θ(P)` |
| Per-processor load | `W₀ / P → 0` | roughly constant |
| Serial portion | Constant **work**, so its **share of runtime grows** as parallel work shrinks | Constant **time** (`s`), so its share of runtime stays fixed |
| Speedup | `1 / (s + p/P)` → `1/s` | `s + p·P = P − α(P−1)` → unbounded, slope `1−α` |
| Efficiency limit | `E → 0` | `E → 1 − α` |
| Scaling type | Strong scaling | Weak scaling |

## 2. Why "fixed-size" vs. "fixed-time"

**Amdahl** normalises the *one-processor* run: `T(1) = s + p = 1`. On `P` processors only the parallel part shrinks: `T(P) = s + p/P`. The problem size is the same in both runs, hence **fixed-size** speedup. Because `T(P) ≥ s`, the best possible speedup is `1/s`. A 5 % serial fraction caps speedup at 20×, no matter what hardware is added.

**Gustafson** normalises the *parallel* run: `T(P) = s + p = 1`. The question becomes: how long would the *same enlarged problem* take on one processor? Answer: `s + p·P`. Runtime is the invariant, so the model is **fixed-time**. Users do not use bigger machines only to run the same job faster. They use them to refine a mesh, add particles, or raise resolution, until the run again takes the time they are willing to wait (overnight, one coffee break, a forecast deadline).

## 3. Philosophical divergence

* Amdahl treats the **problem as given** and the machine as the variable. It is a statement about the *latency* of a fixed job and is the right tool for deciding whether a given code is worth parallelising at all.
* Gustafson treats the **time budget as given** and the problem as the variable. It is a statement about *capacity/throughput* and is the right tool for planning ambitions on large machines.
* The two are not contradictory: they are the same algebra under different invariants. Amdahl's `s` is the serial fraction of a run on 1 core of the *small* problem; Gustafson's `α` is the serial fraction of a run on `P` cores of the *large* problem. For most scientific codes the serial **work** is roughly independent of problem size (set-up, I/O, a global reduction) while the parallel work grows with resolution, so `α ≪ s` and scaling looks very different.

## 4. Physical divergence

Physically, the difference lives in what happens to the **work per processor**.

* Strong scaling → work per core shrinks → communication/computation ratio rises (surface-to-volume effect) → synchronisation, latency, and the serial part dominate. Efficiency collapses.
* Weak scaling → work per core is constant → communication/computation ratio stays (nominally) constant → efficiency plateaus near `1 − α`, **provided** the overheads themselves do not grow with `P` (see Tasks 12, 13).

## 5. Summary

Amdahl's ceiling `1/s` is a property of *fixed-size* experiments. Gustafson showed that if the problem grows with the machine, there is no ceiling on speedup, only a reduced slope `1 − α`. Which law applies is a modelling choice about what the user wants to hold constant.
