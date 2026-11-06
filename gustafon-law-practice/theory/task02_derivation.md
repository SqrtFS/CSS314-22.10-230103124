# Task 02 — Formal Derivation of Scaled Speedup

## Setup

Let the **parallel run on `P` processors** take normalised wall-clock time

```
T_par(P) = s + p = 1                                          (1)
```

* `s` — time the parallel program spends in strictly serial sections (one processor busy, `P−1` idle).
* `p` — time spent in parallel sections (all `P` processors busy).

By definition `α ≡ s` (the serial fraction *measured on the parallel machine*), so `p = 1 − α`.

## Step 1 — Work executed by the parallel program

During the serial phase one processor performs `s` units of work (one processor-second per second).
During the parallel phase `P` processors each perform `p` units, so in total `P·p`.

```
W_total = s·1 + p·P                                           (2)
```
*Justification:* work = (number of busy processors) × (time busy), summed over phases.

## Step 2 — Time the same work needs on one processor

Assume the best serial algorithm needs no more time than the sum of the processors' busy times, i.e. no parallel overhead is hidden in `s` or `p` (otherwise the result is a lower bound on speedup). A single processor must do all of `W_total` sequentially:

```
T_serial = s + p·P                                            (3)
```
*Justification:* the serial part still takes `s`; each of the `P` slices of parallel work that ran concurrently must now run back-to-back, costing `P·p`.

## Step 3 — Speedup

Speedup is the ratio of the single-processor time to the parallel time for the *same (scaled) problem*:

```
S(P) = T_serial / T_par = (s + p·P) / (s + p) = s + p·P       (4)
```
*Justification:* the denominator is 1 by normalisation (1).

## Step 4 — Express in terms of α

Substitute `s = α`, `p = 1 − α`:

```
S(P) = α + (1 − α)·P
     = α + P − αP
     = P − αP + α
     = P − α(P − 1)                                           (5)   ∎
```

## Step 5 — Sanity checks

| Check | Result |
|---|---|
| `P = 1` | `S = 1 − α·0 = 1` ✓ |
| `α = 0` | `S = P` (ideal linear) ✓ |
| `α = 1` | `S = P − (P−1) = 1` (fully serial) ✓ |
| Slope | `dS/dP = 1 − α` — linear in `P`, no asymptote ✓ |

## Step 6 — Efficiency

```
E(P) = S(P)/P = 1 − α(P−1)/P                                  (6)
```

## Remark on the assumption in Step 2

Equation (3) assumes the one-processor machine can hold the scaled problem. In practice it often cannot (memory), so `T_serial` is *extrapolated* from smaller runs. Task 11 (Sun–Ni) treats the memory constraint explicitly.
