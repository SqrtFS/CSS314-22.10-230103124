# Task 16 — Dense Matrix Multiplication (GEMM) Scaling

## Derivation

Work `W(N) = 2N³` flops. Ideal parallel runtime on `P` processors, each delivering `r` flop/s: `T = 2N³/(P·r)`. Gustafson requires `T = const = T₀` (the single-core time for the base size `N₀`: `T₀ = 2N₀³/r`):

```
2N³/(P·r) = 2N₀³/r   ⇒   N³ = P·N₀³   ⇒   N(P) = N₀·P^{1/3}
```

**Result: matrix dimension must grow as `P^{1/3}`.** Total workload grows `∝ P`; matrix **memory** grows `N² ∝ P^{2/3}` — *slower* than P.

## Consequences

* Memory per node: `3·8·N²/P = 24·N₀²·P^{-1/3}` bytes, so **per-node memory shrinks** with `P`: GEMM under fixed-time scaling uses less and less of each node's memory (data reuse is not the problem, but capacity is under-used).
* Communication (2-D SUMMA): per-rank volume `O(N²/√P) = O(N₀²·P^{1/6})` words, growing slowly while per-rank flops stay constant, so the compute/comm ratio degrades as `P^{-1/6}` (Task 12 applies, `C ∝ P^{1/6}`).
* If instead one *fills memory* (Sun–Ni): `N = N₀√P`, work grows `P^{3/2}`, runtime grows `√P`.

## Scaling targets (`N₀ = 1000` at `P = 1`)

| P | `N = 1000·P^{1/3}` | Work `2N³` (Gflop) | Matrix memory total (3 × 8 B × N²) | per node |
|---:|---:|---:|---:|---:|
| 1 | 1 000 | 2 | 24 MB | 24 MB |
| 8 | 2 000 | 16 | 96 MB | 12 MB |
| 64 | 4 000 | 128 | 384 MB | 6 MB |
| 512 | 8 000 | 1 024 | 1.54 GB | 3 MB |
| 4 096 | 16 000 | 8 192 | 6.14 GB | 1.5 MB |

(`N` for non-cube `P` is rounded in practice to a multiple of the block size.)
