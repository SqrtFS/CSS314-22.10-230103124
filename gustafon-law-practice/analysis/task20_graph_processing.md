# Task 20 — Parallel Graph Traversal & Irregular Workloads

## Why regular dense linear algebra is the easy case

For GEMM/LU/stencils: work per rank is **known a priori** and **regular** (blocked, contiguous, predictable). Communication patterns are structured (nearest-neighbour or broadcast along rows/columns), and arithmetic intensity grows with block size (`O(n)` flops/byte for GEMM), so memory latency is hidden.

## Why BFS and PageRank on power-law graphs resist weak scaling

| Property | Effect on Gustafson's premises |
|---|---|
| **Power-law degree distribution** (few hubs with millions of edges, many with 1–10) | 1-D vertex partitioning gives severe load imbalance; the rank holding a hub is the straggler → the "constant per-rank time" premise fails. `α_eff` includes `max − mean` imbalance |
| **Irregular memory access**, random neighbour lookups | Compute is ~ 0 flops per edge, so performance is bound by memory latency/bandwidth and cache-miss rate (`~1 cache miss/edge`). Arithmetic intensity ≈ 0.1 flop/B; cache blocking doesn't apply |
| **BFS frontier imbalance**, frontier sizes swing by 4–6 orders of magnitude between levels; low-diameter graphs have ~6–10 levels but nearly all work in 2–3 | Per-level synchronisation (barrier + frontier exchange) with very uneven work per level; level-synchronous BFS time is the sum of per-level maxima |
| **Data-dependent synchronisation** | Atomic updates / visited-bit contention at hubs; message volumes unknown in advance |
| **Communication volume doesn't shrink with locality** | Edge cuts of random/power-law graphs are Θ(E); no good partition exists (no surface-to-volume effect). Communication per rank stays ≈ `E/P·(1 − 1/P)` bytes while compute per edge is trivial, so comm/comp is huge and roughly constant |
| **Problem growth isn't well defined** | Doubling a real graph doesn't preserve structure. Synthetic Kronecker/RMAT generators (Graph500) grow but diameter and hub size change (hub degree grows with `N^{0.5}`+), so "constant work per rank" and "constant critical path" both break |
| **PageRank iteration count** | Iterations to a tolerance depend weakly on `N` but each iteration needs a global `Allreduce` for convergence and all-to-all rank-vector exchange: `C(P) = Θ(log P)` to `Θ(P)` |
| **Termination detection / global frontier emptiness** | Extra collectives per BFS level (`O(D·log P)`, `D` = diameter) |

## Effects on the model

* `α_eff(P)` is **not** constant: it contains imbalance `(T_max/T_mean − 1)` which grows with `P` (more ranks → more variance in max-of-P).
* Efficiency measured in TEPS (traversed edges per second) per node typically *drops* as nodes are added in Graph500 results; weak scaling holds only approximately and only with 2-D partitioning, direction-optimising BFS, delegate/hub replication, and compression.
* Memory-bound irregular workloads also violate the "node count ∝ throughput" assumption as soon as network injection bandwidth (rather than compute) becomes the limiter.

## Mitigations

1. 2-D (edge) partitioning: communication `O(N/√P)` rather than `O(N)`.
2. Direction-optimising (top-down/bottom-up hybrid) BFS cuts edge checks by ~10×.
3. Hub delegation/vertex-cut partitioning (PowerGraph) to balance hubs.
4. Asynchronous/active-message models that overlap latency (e.g. Charm++, HPX, AM++).
5. Report *Gustafson-style* results only with the generator, scale, and per-rank edge count stated, and report load-imbalance directly.

## Summary

Gustafson's law needs *constant per-rank work, constant per-rank communication, and constant serial time*. Graph analytics violate all three: the work is skewed, communication volume tracks edge count rather than a shrinking surface, and synchronisation points are data-dependent. This is why dense linear algebra approaches `E ≈ 1 − α`, while graph workloads typically show falling per-node throughput.
