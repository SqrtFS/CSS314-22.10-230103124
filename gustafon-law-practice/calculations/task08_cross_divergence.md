# Task 08 — Cross-Over / Divergence between Amdahl and Gustafson

**Given:** serial fraction `0.08`, `P = 128`.

## Step 1 — Amdahl

```
S_A = 1 / (s + (1−s)/P)
    = 1 / (0.08 + 0.92/128)
    = 1 / (0.08 + 0.0071875)
    = 1 / 0.0871875
    = 11.4695
```

## Step 2 — Gustafson

```
S_G = P − α(P−1) = 128 − 0.08·127 = 128 − 10.16 = 117.84
```

## Step 3 — Discrepancy

| Measure | Value |
|---|---|
| Absolute difference | `117.84 − 11.47 = 106.37` |
| Variance ratio `S_G/S_A` | **10.27×** |
| `(S_G − S_A)/S_A` | **927.4 %** (Gustafson is 927 % higher than Amdahl) |
| `(S_G − S_A)/S_G` | **90.3 %** (Amdahl is 90.3 % lower than Gustafson) |
| Efficiencies | Amdahl `E = 8.96 %`; Gustafson `E = 92.06 %` |

## Step 4 — How the gap grows with P (`0.08` in both)

| P | `S_A` | `S_G` | `S_G/S_A` |
|---:|---:|---:|---:|
| 8 | 5.13 | 7.44 | 1.45 |
| 32 | 9.20 | 29.52 | 3.21 |
| 128 | 11.47 | 117.84 | 10.27 |
| 512 | 12.23 | 471.12 | 38.54 |
| 2 048 | 12.43 | 1 884.24 | 151.59 |
| 8 192 | 12.48 | 7 536.72 | 603.78 |

## Step 5 — Why they diverge

* **Amdahl** saturates: `S_A → 1/s = 12.5`; the table shows 12.48 at 8 192 cores.
* **Gustafson** is linear: slope `1 − α = 0.92`, so `S_G ≈ 0.92P + 0.08`.
* The ratio `S_G/S_A ≈ 0.92P·s ≈ 0.0736P` for large `P` grows linearly without bound. They agree only at `P = 1`; there is no "crossover" in the sense of switching order. Gustafson ≥ Amdahl for all `P ≥ 1` when `α = s`.
* **Important caveat:** the problem says "same α", but as Task 03 shows, `s` (uniprocessor, fixed problem) and `α` (parallel machine, scaled problem) are different measurements. Equal numbers mean the code is *assumed* to have the same serial share in two different experiments. The divergence is a difference in *what is held fixed* (problem size vs. time), not an error in either law.
