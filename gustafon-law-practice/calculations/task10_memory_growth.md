# Task 10 — Memory Growth Rate vs. Scaled Speedup

## Formulation

Weak scaling: `W(P) = P·W(1)`. Memory: `M(P) = c·P`, with `c = 32 GiB` the hard per-node cap. A 3-D grid with `b` bytes per grid point (all fields included) has `N³` points, so:

```
b·N³ ≤ c·P   ⇒   N_max(P) = (c·P / b)^{1/3} = N_max(1)·P^{1/3}
```

(Using 32 GiB = 2³⁵ B = 34.36 GB; with decimal 32 GB the numbers drop by 1.6 %.)

## Numbers

`b = 8` B (one `double` per point), per-node limit `(2³⁵/8)^{1/3} = 2^{32/3} = 1625.5`.

| P | Total memory | Points `c·P/b` | `N_max` (b = 8 B) | `N_max` (b = 40 B, 5 double fields) |
|---:|---:|---:|---:|---:|
| 1 | 32 GiB | 4.295·10⁹ | 1 625 | 950 |
| 64 | 2 TiB | 2.749·10¹¹ | **6 502** | **3 802** |
| 512 | 16 TiB | 2.199·10¹² | **13 004** | **7 604** |

Check: the ratio `N(512)/N(64) = (8)^{1/3} = 2` ✓.

## Interpretation

* The *linear* dimension grows only as `P^{1/3}`: 8× more nodes → 2× finer resolution per axis.
* Gustafson's workload growth `W ∝ P` is exactly `N³ ∝ P` for an `O(N³)` kernel, so memory and time both permit weak scaling. For explicit time-stepping, however, the number of steps grows as `N` (CFL), so time-to-solution of a full simulation grows `∝ P^{1/3}` even if the time *per step* is constant (a gentle violation of "constant runtime"; see Task 13).
* In practice reserve ~10–25 % for the OS, MPI buffers and halos: multiply `N` by `0.9^{1/3} = 0.965` to `0.75^{1/3} = 0.909`.
* If memory per point grows (e.g. extra fields for higher-order schemes), `N_max` falls with `b^{-1/3}`.
