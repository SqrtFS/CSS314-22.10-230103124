# Task 04 — Asymptotic Analysis of Parallel Efficiency

## 1. Gustafson efficiency

```
E_G(P) = S(P)/P = [P − α(P−1)]/P = 1 − α(P−1)/P = 1 − α + α/P
```

**Limit.**

```
lim_{P→∞} E_G(P) = lim (1 − α + α/P) = 1 − α
```
since `α/P → 0`. *Proof.* For any `ε > 0`, `|E_G − (1−α)| = α/P < ε` whenever `P > α/ε`. ∎

Properties
* `E_G` is **monotonically decreasing** in `P` (derivative `−α/P² < 0`) and **bounded below** by `1 − α`. It converges from above.
* Largest drop is between `P = 1` (`E = 1`) and `P = 2` (`E = 1 − α/2`). After that it flattens.
* Dependence on `α`: `E_∞ = 1 − α`, linear. A 4 % serial fraction → 96 % efficiency forever.

## 2. Amdahl efficiency

```
S_A(P) = 1/(s + (1−s)/P)
E_A(P) = S_A/P = 1/(sP + 1 − s) = 1/(1 + s(P−1))
```

**Limit.**

```
lim_{P→∞} E_A(P) = lim 1/(1 + s(P−1)) = 0      (for any s > 0)
```
*Proof.* Given `ε > 0`, `E_A < ε ⇔ 1 + s(P−1) > 1/ε ⇔ P > 1 + (1/ε − 1)/s`. ∎

Asymptotically `E_A ≈ 1/(sP)`, i.e. `E_A = Θ(1/P)` — hyperbolic decay. Also `S_A → 1/s`.

## 3. Comparison table (`α = s = 0.04`)

| P | `E_G(P)` | `E_A(P)` |
|---|---|---|
| 16 | 0.9625 | 0.6250 |
| 64 | 0.9606 | 0.2841 |
| 256 | 0.9602 | 0.0893 |
| 1024 | 0.9600 | 0.0239 |
| 16384 | 0.9600 | 0.0015 |

## 4. Deductions

1. Under weak scaling the machine stays ≈ `(1−α)` utilised: the serial section wastes only `α` of one processor-time slice of `P`, **per unit of wall time**, so the waste is `α(P−1)/P ≤ α`.
2. Under strong scaling the idle fraction tends to 1: the waste `s(P−1)` processor-seconds is compared with a fixed `1` unit of useful work.
3. The two limits differ qualitatively (`1−α` vs `0`), the formal statement of "Amdahl's pessimism".
4. Rate of approach: Gustafson converges as `O(1/P)`; Amdahl decays as `O(1/P)` to zero. Both have `1/P` terms, but with entirely different leading constants (`α` vs `1/s`).
