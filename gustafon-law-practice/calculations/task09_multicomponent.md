# Task 09 — Multi-Component Workload Partitioning

| Phase | Description | Share of parallel runtime | Classification |
|---|---|---:|---|
| A | Initial disk I/O + parameter broadcast | 2 % | serial (single-rank I/O / master-driven) |
| B | Boundary message-passing synchronisation | 6 % | treated as serial (non-overlapped synchronisation: all ranks wait) |
| C | Core domain flux computation | 92 % | parallel |

## Aggregate serial fraction

```
α = 0.02 + 0.06 = 0.08
```

## Scaled speedup

```
S(P) = P − α(P−1)
```

| P | `α(P−1)` | `S(P)` | `E(P)` |
|---:|---:|---:|---:|
| 512 | 0.08·511 = 40.88 | **471.12** | 92.02 % |
| 2 048 | 0.08·2047 = 163.76 | **1 884.24** | 92.00 % |

## Per-phase interpretation

* Each phase's contribution to lost speedup is `α_i(P−1)`: A loses 10.22 (P=512) / 40.94 (P=2048); B loses 30.66 / 122.82.
* **B is the dominant target.** Reducing synchronisation cost from 6 % → 2 % would give `α = 0.04` and `S(2048) = 1 966.12` (+4.3 %).

## Sensitivity: B is not truly serial

Synchronisation is a *communication* cost, not serial computation: all ranks participate. Treating it as `α` is the conservative choice. If B is considered *parallel overhead independent of P*, with `α = 0.02` only:

| P | `S` (α = 0.02) | `E` |
|---:|---:|---:|
| 512 | 501.78 | 98.0 % |
| 2 048 | 2 007.06 | 98.0 % |

and if B grows with `P` (e.g. `∝ log P`), use Task 12's model. State which assumption you use. The primary answer is `α = 0.08`.
