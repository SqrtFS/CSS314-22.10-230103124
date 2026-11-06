# Task 14 — Isoefficiency Relation with Gustafson Scaling

## 1. Isoefficiency definitions (Grama, Gupta, Kumar)

* Serial work `W` (= `T_S`, serial time).
* Total overhead `T_o(W, P) = P·T_P − W`.
* Efficiency `E = W/(P·T_P) = 1/(1 + T_o/W)`.
* Holding `E` constant requires `W = K·T_o(W, P)` with `K = E/(1−E)`. Solving for `W` as a function of `P` yields the **isoefficiency function** `W = f_E(P)`. Smaller growth (`Θ(P)` is the best possible) means better scalability.

## 2. Gustafson-compliant program

Per-processor wall-clock `T_P = 1` (normalised). Serial section: one processor works, `P−1` idle for time `α`. All idle time is overhead:

```
T_o = (P − 1)·α                                               (1)
```
Work: `W = α + (1−α)P`. Then

```
E = W/(P·T_P) = [α + (1−α)P]/P = 1 − α(P−1)/P                 (2)
```
which is Task 02's `E(P)`. ✓.

## 3. Derive the isoefficiency function

Hold `E` at its target. From `E = 1/(1 + T_o/W)`, `W = K·T_o`. With `T_o = α(P−1)` (time units of serial section × idle processors):

```
W = K·α·(P − 1) = Θ(P)                                        (3)
```

Where `α` is in time units equal to the serial section's duration. If the serial section's duration is a *constant* `t_s` (independent of `W`), `T_o = t_s(P − 1)`, hence

```
W = K·t_s·(P−1) = Θ(P).
```

**Result: isoefficiency function of a Gustafson-compliant program is `Θ(P)`.** That is the *optimal* isoefficiency, since `W ≥ Ω(P)` is necessary just to give every processor something to do.

## 4. Interpretation

* Weak scaling at `W ∝ P` keeps `E` constant at `1 − α` **exactly because** the overhead `T_o` grows only linearly with `P`.
* Compare with Amdahl: the fixed-size run keeps `W` constant while `T_o = (P−1)s W` grows linearly in `P`; to hold `E`: `W = K·s·W·(P−1)`, which cannot be satisfied for large `P`: no problem-size growth helps *if* `s` is a fraction of `W`. Isoefficiency `= ∞`. The difference: Gustafson's `α` is a time, Amdahl's `s` is a proportion of `W`.
* With communication overhead `C(P)` (Task 12): `T_o = P·C(P)·T₁ + α(P−1)` → `W = Θ(P·C(P))`. For `C = log P`: `W = Θ(P log P)`. For `C = √P`: `W = Θ(P^{3/2})`, so weak scaling at `W ∝ P` cannot hold the efficiency.

## 5. Critique

1. Isoefficiency is memory-agnostic: `W = Θ(P)` can still be infeasible if `M(W) > M_node·P`. Combine with the Sun–Ni condition (Task 11).
2. For GEMM `W = N³`, `M = N²`: `W = Θ(P)` → `N = Θ(P^{1/3})` and per-node memory shrinks as `P^{-1/3}`, all right. For algorithms with `T_o = Θ(P^{3/2})`, memory needs `M = Θ(P^{...})` may exceed node limits.
3. The "optimal" `Θ(P)` is a condition, not a guarantee: it assumes the overhead terms are exactly those in (1).
