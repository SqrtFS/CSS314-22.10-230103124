# Task 18 — N-Body Gravitational Problem Scaling

Base problem: `N₁ = 10⁵` particles on one core, time per iteration `T₀`. Goal: keep time per iteration at `T₀` as `P` grows.

## 1. Direct all-pairs, `O(N²)`

```
T_comp = c·N²/P = const = c·N₁²   ⇒   N(P) = N₁·√P
```
* Particles per rank: `N/P = N₁/√P` — **shrinks**, while pair interactions per rank `N²/P = N₁²` stay constant.
* Communication: every rank needs all `N` positions (all-gather or ring pass): `Θ(N) = Θ(N₁√P)` words received per rank per step, so it **grows as `√P`**.
* Comm/comp ratio: `N / (N²/P) = P/N = √P/N₁` → **grows ∝ √P**.
* Effective serial/overhead fraction `α_eff(P) ≈ α₀ + κ√P` → Task 12 with `C(P) = Θ(√P)`: efficiency `Θ(P^{-1/2})`. Compute is perfectly parallel, but data volume fights back.

## 2. Barnes–Hut, `O(N log N)`

```
c·N log₂N / P = c·N₁ log₂N₁     ⇒   N·log₂N = P·N₁·log₂N₁
```
Solution (numerical):

| P | Direct `N = N₁√P` | Barnes–Hut `N` | BH particles / rank |
|---:|---:|---:|---:|
| 1 | 1.0·10⁵ | 1.0·10⁵ | 100 000 |
| 64 | 8.0·10⁵ | 4.79·10⁶ | 74 846 |
| 1 024 | 3.2·10⁶ | 6.55·10⁷ | 63 969 |
| 16 384 | 1.28·10⁷ | 9.14·10⁸ | 55 797 |

Asymptotically `N ≈ P·N₁·log N₁/log N = Θ(P/log P)`·(const): nearly linear growth.

* Particles per rank shrink only logarithmically (`N/P = N₁ log N₁/log N`), so per-rank data volume is almost constant.
* Communication: locally-essential-tree (LET) exchange ∝ surface of each rank's domain, `O((N/P)^{2/3})` ≈ constant, plus tree-top terms `O(log P)`.
* Serial/replicated parts: top-level tree built or replicated by every rank (`O(P)` cells in the worst case); domain decomposition (sorting/space-filling curve, `O(log P)` collectives); load imbalance from clustering.
* So `α_eff(P) ≈ α₀ + κ'·log P + imbalance`: slow growth.

## 3. How the serial/parallel ratio shifts

| | Direct | Barnes–Hut |
|---|---|---|
| Workload growth for constant time | `N ∝ P^{1/2}` | `N ∝ P/log P` |
| Total interactions processed | `N²` ∝ `P` | `N log N` ∝ `P` |
| Comm per rank | `Θ(√P)` | `Θ(1)` + `O(log P)` |
| Serial-ish fraction | grows `√P` | grows ~`log P` |
| Scaling verdict | fixed-time scaling holds in compute, **fails in communication** | **closest to ideal Gustafson** |

## 4. Key observations

1. For the same wall-clock, Barnes–Hut simulates 6× (P = 64) to 71× (P = 16 384) more particles than direct summation.
2. Direct summation has the larger *arithmetic* intensity (good for GPUs) but its all-to-all data dependency makes its weak-scaling `α` grow. Use ring/systolic schemes or a 2-D force decomposition: each rank holds `N/√P` particles, so received volume is `O(N/√P) = O(N₁)` (constant under this scaling) at the price of row/column collectives of `O(log P)`.
3. Barnes–Hut shifts the problem to irregularity (tree traversal, imbalance), a theme developed in Task 20.
