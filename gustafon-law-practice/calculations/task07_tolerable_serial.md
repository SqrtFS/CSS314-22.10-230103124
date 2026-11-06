# Task 07 — Maximum Tolerable Serial Overhead

**Given:** `P = 8192`, requirement `S(P) ≥ 7500`.

## Derivation

```
S(P) = P − α(P−1) ≥ 7500
⇒  α(P−1) ≤ P − 7500
⇒  α ≤ (P − 7500)/(P − 1)
```

Substituting `P = 8192`:

```
α_max = (8192 − 7500)/(8192 − 1) = 692/8191 = 0.0844830…
```

## Result

**`α_max ≈ 0.08448` (8.448 %).**

Verification: `S = 8192 − 0.0844830·8191 = 8192 − 692.00 = 7500.00` ✓.

Equivalent efficiency floor: `E = 7500/8192 = 91.55 %`.

## Sensitivity

| Required S | `α_max` |
|---:|---:|
| 8 000 | 0.02344 |
| 7 500 | 0.08448 |
| 7 000 | 0.14553 |

Each additional 500 of required speedup costs ≈ 6.1 percentage points of serial-fraction budget (`500/8191 = 0.061`).

## Comment

Note that the requirement is expressed as a *fraction of parallel wall-clock time*, so at `P = 8192`, 8.4 % of a run may be spent with a single core active. With an hour-long job that is ~5 minutes of serial work (set-up, I/O, reductions).
