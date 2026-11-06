# Task 12 — Communication Overhead Penalty Integration

## 1. Limitation of the classic model

Gustafson's `α` is taken as constant. On distributed-memory machines, collective operations (`MPI_Allreduce`, barriers) cost `O(log P)` latency terms and diameter-bound nearest-neighbour or all-to-all costs can go as `O(√P)` (2-D torus) or `O(P^{1/3})` (3-D torus). These do not shrink when per-rank work is held constant, so runtime creeps up and `α` effectively becomes a function of `P`.

## 2. Model

Normalise the *single-processor* time of the per-rank problem to `T₁ = 1` (so `s + p = 1`). On `P` processors the scaled problem has `s + pP` units of work, executed by `P` ranks. Runtime is now

```
T(P) = s + p + C(P) = 1 + C(P)
```
where `C(P) ≥ 0` is communication/sync time per unit of the normalised run (not overlapped with compute). Then:

```
S_C(P) = (s + p·P) / (1 + C(P))                                   (1)
       = [α + (1−α)P] / [1 + C(P)]
E_C(P) = S_C(P)/P = [1 − α(P−1)/P] / [1 + C(P)]                   (2)
```

Equivalently, the effective serial fraction is

```
α_eff(P) = (α + C(P)) / (1 + C(P))                                (3)
```
which gives `S_C ≈ P − α_eff(P)·(P−1)` for `C ≪ 1`, i.e. Gustafson's form with a `P`-dependent serial fraction.

## 3. Overhead families

| Pattern | `C(P)` | Example |
|---|---|---|
| Tree reduction / barrier | `γ·log₂P` | `MPI_Allreduce` of scalars |
| 2-D mesh diameter | `γ·√P` | long-range halo, 2-D torus all-to-all |
| 3-D torus diameter | `γ·P^{1/3}` | |
| Pairwise all-to-all | `γ·P` | naive transpose |
| Constant | `γ` | nearest-neighbour halo (absorb into `α`) |

`γ` is the communication time per unit step relative to the per-rank compute time (dimensionless).

## 4. Asymptotics

For large `P`:

* `C = γ log₂ P`: `S_C ≈ (1−α)P / (γ log₂P)` → `Θ(P/log P)`; `E_C → 0` slowly as `1/log P`.
* `C = γ√P`: `S_C ≈ (1−α)√P/γ` → `Θ(√P)`; `E_C = Θ(P^{-1/2})`.
* Any `C(P)` with `C(P) = o(1)` preserves Gustafson's limit `E → 1−α`. Any `C(P) → ∞` kills it. Weak scaling holds only if overheads are bounded.

## 5. Numerical example (`α = 0.01`)

| P | `γ=0.01`, `C=γ log₂P` | `S` | `E` | `γ=0.001`, `C=γ√P` | `S` | `E` |
|---|---|---|---|---|---|---|
| 64 | 0.060 | 59.8 | 0.934 | 0.008 | 62.9 | 0.982 |
| 1 024 | 0.100 | 921.6 | 0.900 | 0.032 | 982.3 | 0.959 |
| 16 384 | 0.140 | 14 228 | 0.868 | 0.128 | 14 380 | 0.878 |
| 65 536 | 0.160 | 55 932 | 0.853 | 0.256 | 51 657 | 0.788 |

The `√P` penalty starts smaller but crosses the `log P` penalty near `P ≈ 10⁴` and degrades faster beyond it.

## 6. Mitigation and design rules

* Overlap communication with compute: effective `C(P) → max(0, C(P) − overlap)`.
* Use hierarchical / topology-aware collectives (reduces constant `γ`).
* Reduce collective frequency (communication-avoiding or pipelined methods).
* Fit `γ` empirically: measure `T(P)` at constant per-rank load and regress `T(P) − T(1)` on `log₂P`, `√P`.
