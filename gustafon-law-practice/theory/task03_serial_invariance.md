# Task 03 — The Serial Fraction Invariance Paradox

## The apparent contradiction

* Amdahl: serial fraction `s` bounds speedup at `1/s`. With `s = 0.04`, max 25×.
* Gustafson: with `α = 0.04` and `P = 16384`, `S ≈ 15 729`. Same number, wildly different outcome.

How can the same 4 % be harmless in one law and fatal in the other? The resolution is that **the two `s` values are different physical quantities, measured in different reference frames.**

## Frame of reference

| | Amdahl `s` | Gustafson `α` |
|---|---|---|
| Measured on | 1 processor | `P` processors |
| Denominator | `T₁(W₀)` (serial time of the *fixed* problem) | `T_P(W_P)` (parallel time of the *scaled* problem) |
| Definition | `s = T_serial-part / T₁` | `α = T_serial-part / T_P` |
| Meaning | share of the *work* that is serial | share of the *wall-clock* that is serial |

## Analytical conversion between the two

Let the scaled problem on `P` processors be measured on the parallel machine as `α` (serial time) and `1 − α` (parallel time). The equivalent one-processor time is `α + (1−α)P`. Hence the **serial fraction as seen by a uniprocessor** running that *same scaled problem* is

```
s₁ = α / (α + (1 − α)P)                                       (1)
```

Insert this `s₁` in Amdahl's law for the scaled problem:

```
S_Amdahl = 1 / (s₁ + (1 − s₁)/P)
         = 1 / ( α/(α+(1−α)P) + ((1−α)P/(α+(1−α)P))/P )
         = 1 / ( (α + (1−α)) / (α+(1−α)P) )
         = α + (1−α)P                                         (2)
```

Equation (2) *is* Gustafson's law. So **Amdahl's law applied to the scaled problem, with the uniprocessor serial fraction `s₁` of that scaled problem, reproduces Gustafson exactly.** There is no contradiction in the mathematics, only in what gets plugged in.

## Why the "throttle" disappears

From (1), `s₁ → α/((1−α)P) → 0` as `P → ∞`. Growing the problem makes the (constant-time) serial section an ever smaller fraction of the *uniprocessor* work. Amdahl's `1/s₁` ceiling therefore grows without bound:

```
1/s₁ = (α + (1−α)P)/α  ~  (1−α)P/α   →  ∞
```

Numerical illustration with `α = 0.04`, `P = 1024`:
* `s₁ = 0.04 / (0.04 + 0.96·1024) = 0.04/983.08 = 4.07×10⁻⁵`
* Amdahl ceiling for that problem: `1/s₁ = 24 577`, far above `P = 1024`, so the 1024 cores are almost fully usable.

## The key assumption

The invariance requires that the serial **time** stays roughly constant while the parallel **work** grows (set-up, I/O, a fixed-size reduction, a master-rank decision). If the serial part itself grows with problem size (e.g. `O(N)` serial post-processing for an `O(N)` problem), then `α` is not constant and the paradox returns. That is the failure mode in Tasks 12 and 13.

## Practical memo

1. Always state **where** the serial fraction was measured.
2. Quote Amdahl's `s` only for fixed-size strong-scaling studies; quote Gustafson's `α` for weak scaling.
3. A serial fraction measured on `P` cores is automatically "after the problem has been enlarged", so it already embeds the effect of scaling.
4. Beware converting between them: `s₁ = α/(α+(1−α)P)` and `α = s₁P / (1 + s₁(P−1))`.
