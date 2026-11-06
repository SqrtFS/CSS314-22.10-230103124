# Task 05 — Deconstructing the "Amdahl's Pessimism" Fallacy: the nCUBE/10 Case

> **Source caveat.** This reconstruction relies on my recollection of Gustafson, Montry & Benner (Sandia National Laboratories, 1988; *SIAM J. Sci. Stat. Comput.* 9(4)) and Gustafson's CACM note "Reevaluating Amdahl's Law" (May 1988). I could not open the papers from this sandbox (no network), so specific application figures below should be checked against the originals before you cite them.

## 1. Context

In the mid-1980s the prevailing view, popularised by readings of Amdahl's 1967 paper, was that massive parallelism was futile. If even 1 % of a program is serial, 1000 processors give at most ~91×, and `1/s = 100×` is the hard ceiling. Gustafson's Sandia group were building a 1024-node hypercube (nCUBE/10, each node with ≈0.5 MB of local memory, no shared memory).

## 2. The experiment

* Platform: **1024 processors**, hypercube topology.
* Three production-style applications: a **beam-strain analysis**, a **surface-wave simulation**, and an **unstable fluid-flow** simulation.
* Measured on the 1024-processor machine, the serial fraction (the part not parallelised: program load, set-up, I/O, and the like) was roughly **0.4 % – 0.8 %**.
* Reported scaled speedups were about **1000× – 1020×** (efficiency ≈ 98–99 %).

## 3. Why this "violated" Amdahl

Treating the 0.4 % as an Amdahl `s`:

```
S_Amdahl(1024) = 1 / (0.004 + 0.996/1024) = 201
Ceiling       = 1/0.004 = 250
```
A speedup of 1000+ is five times the ceiling, an apparent impossibility.

## 4. Resolution: problem expansion

Gustafson's observation was that the group *did not run the same problem on more nodes*. Each node had a fixed amount of memory, and they used it all: the problem (grid/mesh size, number of elements) grew to fill the machine, so each processor kept about the same workload, and total runtime stayed ~constant.

* The **serial portion's time** (initialisation, loading, final output) was nearly independent of mesh size, so it stayed ≈ constant in **time** while parallel work grew by ×1024.
* Applying scaled speedup: `S(1024) = 1024 − α·1023`. With `α = 0.004`: `S = 1019.9`; with `α = 0.008`: `S = 1015.8`. This agrees with the reported ~1000+ range.
* Equivalent Amdahl view (Task 03): the serial fraction *of the 1-processor run of the big problem* is `s₁ = 0.004/(0.004 + 0.996·1024) ≈ 3.9×10⁻⁶`, so the Amdahl ceiling for that large problem is ~255 000, not 250.

## 5. Why the experiment was only possible on the parallel machine

A single nCUBE node had ~0.5 MB; the full problem could not run on one node, so the one-processor time had to be **estimated** (from the measured parallel serial time and parallel work). This is exactly the formulation of Task 02. Gustafson also notes this is a legitimate use of scaled speedup, not a measurement artefact.

## 6. Lessons

1. Amdahl's ceiling is a statement about a fixed problem, not about the *application domain*.
2. Users scale problems with machines (finer meshes, more particles), so scaled speedup models real use better.
3. The serial fraction must be quoted together with the problem size and machine on which it was measured.
4. Caveat: the result relies on communication being nearest-neighbour (hypercube-friendly) and on memory per node being constant. Both are assumptions that break for other algorithms (Tasks 12, 13).
