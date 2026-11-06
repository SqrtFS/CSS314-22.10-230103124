# Task 15 — Energy and Power Proportionality under Scaled Speedup

## Model

* `P_idle` — static power drawn by one node whenever it is powered on (even when idle).
* `P_active` — **additional** dynamic power when a node computes. A busy node draws `P_idle + P_active`.
* Wall-clock time of the weak-scaling run: `T` (constant by Gustafson). Serial fraction of the run: `α` (time share in which only 1 node is busy).

## 1. Energy on `P` nodes (scaled problem)

During `αT`: 1 node active, `P−1` idle. During `(1−α)T`: `P` nodes active.

```
E_P = P·P_idle·T + P_active·[α·1 + (1−α)·P]·T
    = T·[ P·P_idle + P_active·S(P) ]                          (1)
```
using `S(P) = α + (1−α)P` (Task 02). Notice that busy-node time `= S(P)·T`, the work done.

## 2. Energy for the *same work* on 1 node

The scaled problem needs `S(P)·T` time on one node (Task 02). Energy:

```
E_1(S·T) = S(P)·T·(P_idle + P_active)                         (2)
```

## 3. Energy for the same **wall-clock** (T) on 1 node

One node can do only `1/S(P)` of the scaled problem in time `T`. Energy `E = T(P_idle + P_active)` for a problem `S(P)×` smaller. Per unit work: `T(P_idle + P_active)` vs. `T[P·P_idle + P_active S]/S`.

## 4. Energy per unit of work

```
e_P = E_P / (S·T) = P_active + P_idle · P/S(P) = P_active + P_idle / E(P)       (3)
e_1 = P_active + P_idle
```
Since `E(P) ≤ 1`, `e_P ≥ e_1`: energy per unit work rises by `P_idle (1/E − 1)`, which is the idle energy burnt during the serial phase:

```
e_P − e_1 = P_idle·(1/E(P) − 1) = P_idle·α(P−1)/S(P)  →  P_idle·α/(1−α)     (P→∞)
```

## 5. Ratio

```
E_P / E_1(S·T) = [P·P_idle + P_active·S] / [S·(P_idle + P_active)]
               = [P_idle/E(P) + P_active] / [P_idle + P_active]
```

Define `ρ = P_idle/(P_idle + P_active)` (static-power fraction). Then `E_P/E_1 = 1 + ρ(1/E(P) − 1)`.

## 6. Numerical example

`α = 0.04`, `P_idle = 100 W`, `P_active = 200 W`, `T = 1 h`, `P = 1024`:

* `S = 983.08`, `E = 0.9600`.
* `E_P = 1 h·[1024·100 + 200·983.08] W = 102.4 kWh + 196.6 kWh = 299.0 kWh`.
* `E_1(S·T) = 983.08 h·300 W = 294.9 kWh`.
* Ratio = `1.0139`: **1.4 %** more energy than the serial run, in `1/983` of the time.

If `P_idle` dominates (`ρ = 0.9`), ratio = `1 + 0.9(0.0417) = 1.0375`.

## 7. Conclusions

1. Under weak scaling energy for a given amount of work rises only by the idle energy burned in serial phases: `ρ(1/E − 1)`, which is small when `E ≈ 1 − α` is high.
2. The comparison at *identical wall-clock*: `P` nodes consume `≈ P×` the energy of 1 node but process `S ≈ P×` the work, so energy per unit work is nearly constant. Weak scaling is close to **energy-proportional** *if* static power is low or `α` is small.
3. If nodes could power-gate during the serial phase (`P_idle → 0` for the idle nodes), `E_P = P_active·S·T` and `e_P = e_1`: perfect proportionality.
4. Under strong scaling energy per job rises further, because `E_A → 0` makes `1/E` blow up.
