# Gustafson's Law & Weak Scaling — Practice Repository

Parallel & Distributed Computing Architecture — practice task sheet (Instructor: Sufyan bin Uzayr). Branch/folder: `gustafson-law-practice/`.

> **Honest status note.** Tasks 01–21 are analytical/numeric and were verified by script. Tasks 22–24 were *executed* in a **single-vCPU** sandbox, so the measured data illustrate oversubscription (α_observed ≈ 1), **not** Gustafson scaling. The code is complete and portable; re-run it on a multi-core host (commands below) to get meaningful curves. Task 05 quotes historical figures from memory; verify against the 1988 papers before citing.

## Table of contents
1. [Core mathematical rules](#1-core-mathematical-rules)
2. [When to design around Gustafson weak scaling](#2-when-to-design-around-gustafson-weak-scaling)
3. [Architectural synthesis of the findings](#3-architectural-synthesis-of-the-findings)
4. [Execution commands](#4-execution-commands)
5. [Artifact index](#5-artifact-index)
6. [Limitations](#6-limitations)

## 1. Core mathematical rules

| Quantity | Formula | Key facts |
|---|---|---|
| Amdahl (fixed size) | `S_A = 1/(s + (1−s)/P)` | `→ 1/s`; `E_A → 0` (`≈ 1/(sP)`) |
| Gustafson (fixed time) | `S = P − α(P−1) = α + (1−α)P` | slope `1−α`, no ceiling |
| Efficiency | `E = 1 − α + α/P` | `→ 1−α` from above |
| Frame of reference | `s₁ = α/(α+(1−α)P)` | Amdahl on the *scaled* problem = Gustafson (Task 03) |
| Max tolerable `α` | `α ≤ (P − S_req)/(P−1)` | `P=8192, S≥7500 ⇒ α ≤ 0.08448` |
| Communication-aware | `S_C = [α+(1−α)P]/(1+C(P))` | `C = γ log P` → `Θ(P/log P)`; `C = γ√P` → `Θ(√P)` |
| Memory-bounded (Sun–Ni) | `S* = (s+pG)/(s+pG/P)` | `G=1` Amdahl, `G=P` Gustafson, `G>P` GEMM/N-body |
| Isoefficiency of Gustafson codes | `W = Θ(P)` | optimal; with `C=log P`, `Θ(P log P)` |
| Energy per unit work | `e_P = P_active + P_idle/E(P)` | idle energy in serial phases is the penalty |

## 2. When to design around Gustafson weak scaling

Use it when **all** of these hold:
1. The science/product benefits from a *bigger* problem (finer mesh, more particles, more samples), not just a faster answer.
2. Work grows ≈ linearly with the resource you add, and the per-rank workload can stay constant.
3. Serial time (set-up, I/O, master logic) is roughly independent of problem size, i.e. `α` is a *time*, not a fraction of work.
4. Communication per rank is bounded (nearest-neighbour halos, `O(log P)` collectives at most) and memory per node can be filled.
5. Algorithmic iteration count does not grow with the problem size (Task 13).

Prefer **strong-scaling (Amdahl) analysis** when the problem is fixed (latency-critical inference, a fixed benchmark, a legal deadline on a given dataset). Use **Sun–Ni** when memory, not time, is the binding limit. Use the **communication-aware** model for any code with global collectives or all-to-all.

Design checklist: measure `α` on the *parallel* machine; fit `C(P)`; compute the isoefficiency growth; verify memory per node; report imbalance (`T_max/T_mean`).

## 3. Architectural synthesis of the findings

* **Numbers (Tasks 06–10):** with `α = 0.04` efficiency stays ≈ 96 % from 16 to 16 384 cores, whereas Amdahl drops to 0.15 %. At `α = 0.08`, `P = 128`: Gustafson 117.84 vs Amdahl 11.47 (10.3×). Three-phase simulation: `α = 0.08` ⇒ `S(512) = 471.12`, `S(2048) = 1884.24`. A 3-D grid at 32 GiB/node reaches `N ≈ 6 502` (64 nodes) and `13 004` (512 nodes) at 8 B/point.
* **Kernels (Tasks 16–20):** GEMM needs `N ∝ P^{1/3}` (and per-node memory *shrinks*); stencils keep surface-to-volume constant (`6/n`); direct N-body needs `N ∝ √P` but communication grows `√P`, Barnes–Hut `N ∝ P/log P`; Monte-Carlo gets `α ~ 5·10⁻⁴` with tree reductions; graph analytics break all three Gustafson premises.
* **Limits (Tasks 11–15):** Gustafson over-estimates when overheads or algorithmic iterations grow with `P` (CG, 3-D FFT); under-estimates wall-time-flexible work when compute outgrows memory (Sun–Ni). Energy follows parallel efficiency through the idle term.
* **Empirics (Tasks 21–24):** the simulator reproduces all hand calculations; the benchmark harness, regression and plot pipeline are validated end-to-end, and the audit explains why the single-vCPU result gives `α ≈ 1` and `S ≈ 1.03`.

## 4. Execution commands

```bash
# Task 21 – simulator (CSV + overlay plots)
python3 benchmarks/simulator.py --csv benchmarks/simulator_output.csv --plot-dir plots
python3 benchmarks/simulator.py --alphas 0.04 --P 16 64 256 1024 4096 16384 --no-plot   # Task 06 check

# Task 22 – build + run the weak-scaling benchmark
make -C benchmarks/weak_scale_bench
python3 benchmarks/weak_scale_bench/run_bench.py --runs 5            # -> benchmarks/results.csv   (Task 23 data)

# Task 23 – regression;  Task 24 – plots
python3 benchmarks/fit_gustafson.py
python3 benchmarks/plot_scaling.py                                   # -> plots/scaling_comparison.(png|pdf)
```
Requirements: Python 3.9+, `numpy`, `matplotlib`; `g++` with OpenMP. For real hardware use `OMP_PROC_BIND=close OMP_PLACES=cores`.

## 5. Artifact index

| Task | Artifact |
|---|---|
| 01 | `theory/task01_scaling_models.md` |
| 02 | `theory/task02_derivation.md` |
| 03 | `theory/task03_serial_invariance.md` |
| 04 | `theory/task04_asymptotic_limits.md` |
| 05 | `theory/task05_historical_ncube.md` |
| 06 | `calculations/task06_parametric_table.md` |
| 07 | `calculations/task07_tolerable_serial.md` |
| 08 | `calculations/task08_cross_divergence.md` |
| 09 | `calculations/task09_multicomponent.md` |
| 10 | `calculations/task10_memory_growth.md` |
| 11 | `theory/task11_sun_ni_comparison.md` |
| 12 | `theory/task12_communication_penalty.md` |
| 13 | `theory/task13_failure_cases.md` |
| 14 | `theory/task14_isoefficiency.md` |
| 15 | `theory/task15_energy_scaling.md` |
| 16 | `calculations/task16_gemm_scaling.md` |
| 17 | `calculations/task17_stencil_scaling.md` |
| 18 | `analysis/task18_nbody_scaling.md` |
| 19 | `analysis/task19_monte_carlo.md` |
| 20 | `analysis/task20_graph_processing.md` |
| 21 | `benchmarks/simulator.py`, `benchmarks/simulator_output.csv`, `plots/simulator_overlay.(png\|pdf)` |
| 22 | `benchmarks/weak_scale_bench/` (`weak_scale_bench.cpp`, `run_bench.py`, `Makefile`, `README.md`) |
| 23 | `benchmarks/results.csv`, `benchmarks/fit_gustafson.py`, `benchmarks/fit_results.json` |
| 24 | `plots/scaling_comparison.(png\|pdf)`, `benchmarks/plot_scaling.py`, `analysis/task24_hardware_audit.md` |
| 25 | `README.md` (this file) |

## 6. Limitations

* Tasks 22–24 data come from a 1-vCPU VM (see `analysis/task24_hardware_audit.md`); regenerate on multi-core hardware before drawing scaling conclusions.
* Task 05 historical figures are from memory (no network access when written).
* Task 10 depends on the assumed bytes per grid point (8 B and 40 B shown).
* Task 09 treats synchronisation as serial (conservative); the alternative is shown.
