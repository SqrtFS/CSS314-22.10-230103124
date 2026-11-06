# Task 13 — Boundary Case: When Gustafson Fails

Gustafson's law needs two premises: (i) the *work* can grow ∝ `P` while per-rank work and runtime stay constant, and (ii) the serial time and overheads do not grow with `P`. Two algorithms violate them.

## Case A — Conjugate-Gradient solve of a 3-D Poisson problem

**Setup.** Grid `n³` points per rank, `P` ranks, global `N³ = n³P`, so `N = nP^{1/3}`.

**Why the premise breaks.**
1. **Iteration count grows with problem size.** For unpreconditioned CG, iterations to a fixed tolerance scale with the square root of the condition number, `κ ~ N²`, so `iters ∝ N ∝ P^{1/3}`. The *work per iteration* is constant per rank (weak scaling), but there are `P^{1/3}` times as many iterations. Runtime grows `T(P) ∝ P^{1/3}`.
2. **Global reductions.** Each iteration has two dot products (`MPI_Allreduce`), costing `O(log P)` latency each, so per-iteration time grows as `a + b·log₂P`.
3. Combined: `T(P) ≈ T₁·P^{1/3}(1 + γ log₂P)`.

**Consequence.** For `P = 4096`, runtime is ≈ `16×` larger than the one-rank run, even before reduction cost. "Constant runtime" is false, so the number `P − α(P−1)` bears no relation to reality. The *scaled speedup* under the corrected time: `S ≈ P / (P^{1/3}(1+γ log₂ P)) = P^{2/3}/(1 + γ log₂P)`.

**Mitigation.** Multigrid or preconditioners that make iterations `N`-independent (`O(1)` iterations) restore weak scalability (but coarse levels then introduce their own `O(log P)` serial-like cost).

## Case B — Distributed 3-D FFT (pencil/slab decomposition)

**Setup.** `N³` points, `P` ranks, `N³ = n³P` kept so per-rank data is constant.

**Why the premise breaks.**
1. **Complexity changes.** Work is `O(N³ log N)`, not `O(N³)`. Fixed-time weak scaling would need `n³ log N` constant per rank, but `log N` grows with `P`: `T_comp ∝ log N = log n + (1/3) log P`. Mild, but non-constant.
2. **All-to-all transpose.** Each rank must exchange data with `O(√P)` (pencil) or `O(P)` (slab) partners, and the **bisection bandwidth** of the network is the limit. Total data across the bisection is `Θ(N³)=Θ(nP)`-ish while bisection bandwidth of a 3-D torus scales as `P^{2/3}`. So `T_comm ∝ P^{1/3}` even with ideal routing.
3. **Message size shrinks.** With pairwise exchange, each message has size `n³/P`. Latency-dominated for large `P`.

**Consequence.** Time per transform grows with `P` (by roughly `P^{1/3}` on a 3-D torus), `α_eff(P)` grows, and the Gustafson curve overestimates achievable throughput.

## Why the "constant-runtime" premise breaks (general conditions)

| Condition | A (CG) | B (FFT) |
|---|---|---|
| Algorithmic iterations/complexity depend on `N` | ✔ | ✔ (log factor) |
| Global synchronisation / collective | ✔ | ✔ |
| Bisection-bandwidth limit | — | ✔ |
| Serial/overhead time grows with `P` | ✔ | ✔ |

## Evaluation guideline

Before applying Gustafson's law, answer: *If I multiply the problem by `P`, does every per-rank cost stay the same?* If a global reduction, a transpose, or an N-dependent iteration count exists, use the modified model of Task 12 with `C(P)` fitted to the measured growth.
