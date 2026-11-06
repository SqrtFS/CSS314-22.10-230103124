# Task 17 — 3-D Stencil Hydrodynamics: Surface-to-Volume Scaling

## Setup

7-point stencil, global grid `N³`, `P` ranks in a `P^{1/3} × P^{1/3} × P^{1/3}` decomposition. Local block `n × n × n`, `n = N/P^{1/3}`.

* Computation per step per rank: `≈ c_f·n³` (≈ 8 flops/point for 7-pt, constants aside).
* Halo exchange per step per rank: 6 faces × `n²` points × 8 B = `48n²` B.
* Ratio: `R = comm/comp ∝ n²/n³ = 1/n`.

## Weak scaling (Gustafson): volume ∝ P

Keep `n` fixed → `N = n·P^{1/3}`.

```
R_weak = 6n²/(n³) = 6/n    — independent of P
```
Per-rank compute and per-rank halo bytes are constant. Communication cost per step is constant (nearest-neighbour, ≤ 6 messages), so overhead is absorbed in a constant `α` (the **ratio neither improves nor degrades** with `P`).

Relative to the *serial* run (`P = 1`, which has no halo exchange), the ratio is a one-time step from 0 to `6/n`, then flat.

## Strong scaling (fixed `N`): for comparison

`n = N/P^{1/3}`, so `R_strong = 6P^{1/3}/N`, which **degrades** (grows) as `P^{1/3}`. Surface-to-volume ratio rises as the sub-domains shrink. Example: `N = 1024`:

| P | n | `6/n` |
|---:|---:|---:|
| 8 | 512 | 0.012 |
| 512 | 128 | 0.047 |
| 32 768 | 32 | 0.188 |

## Weak-scaling table (`n = 128` fixed)

| P | `N` | Per-rank compute (pts) | Per-rank halo (pts) | `R` |
|---:|---:|---:|---:|---:|
| 8 | 256 | 2.10 M | 98.3 k | 0.0469 |
| 64 | 512 | 2.10 M | 98.3 k | 0.0469 |
| 512 | 1 024 | 2.10 M | 98.3 k | 0.0469 |
| 4 096 | 2 048 | 2.10 M | 98.3 k | 0.0469 |
| 32 768 | 4 096 | 2.10 M | 98.3 k | 0.0469 |

## Conclusion

Surface-to-volume ratio under weak scaling stays at `6/n`: **constant**, hence no degradation with `P` in volume terms. This is why stencils are a canonical Gustafson-friendly workload. Caveats:

1. Global operations (`dt` selection via `Allreduce` for CFL, norms) add `O(log P)` (Task 12).
2. The number of time steps grows `∝ N ∝ P^{1/3}` (CFL), so total simulation runtime is *not* constant, only the time per step is.
3. Larger `n` reduces `R`; stencil codes should maximise `n` subject to memory.
