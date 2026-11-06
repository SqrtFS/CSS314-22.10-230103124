# Task 06 — Parametric Speedup Across Processor Densities (α = 0.04)

Formulas: `S(P) = P − α(P−1)`, `E(P) = S(P)/P`, with `α = 0.04`.

## Worked arithmetic

| P | `α(P−1)` | `S(P) = P − α(P−1)` | `E(P) = S/P` | Idle-core equivalents `P − S` | Amdahl `S_A` (s = 0.04) |
|---:|---:|---:|---:|---:|---:|
| 16 | 0.04·15 = 0.60 | **15.40** | **96.250 %** | 0.60 | 10.00 |
| 64 | 0.04·63 = 2.52 | **61.48** | **96.063 %** | 2.52 | 18.18 |
| 256 | 0.04·255 = 10.20 | **245.80** | **96.016 %** | 10.20 | 22.86 |
| 1 024 | 0.04·1023 = 40.92 | **983.08** | **96.004 %** | 40.92 | 24.43 |
| 4 096 | 0.04·4095 = 163.80 | **3 932.20** | **96.001 %** | 163.80 | 24.85 |
| 16 384 | 0.04·16383 = 655.32 | **15 728.68** | **96.0002 %** | 655.32 | 24.96 |

(Values verified by script; see `benchmarks/simulator.py --alpha 0.04`.)

## Evaluation

* **Efficiency does not degrade meaningfully.** `E(P) = 0.96 + 0.04/P`. Across a 1024× increase in cores (16 → 16 384) it moves from 96.25 % to 96.0002 %, a change of 0.25 percentage points. It converges to `1 − α = 96 %` from above.
* **Absolute idle capacity grows linearly** (`P − S = α(P−1)`): 0.6 cores' worth at 16 cores vs. 655 cores' worth at 16 384. That is a real cost in node-hours, even though the *percentage* is flat.
* **Contrast with Amdahl** using the same number as a fixed-size `s`: at 16 384 cores the Amdahl speedup is 24.96, efficiency 0.15 %.
* **Caveat.** The flat 96 % is a modelling result: it assumes `α` is independent of `P` and communication is negligible. Task 12 shows how `log P` or `√P` overheads erode this.
