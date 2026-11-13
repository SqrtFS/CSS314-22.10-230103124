from dataclasses import dataclass
import multiprocessing as mp
import time
from typing import Callable


@dataclass
class BenchStats:
    min_ms: float
    median_ms: float
    iqr_ms: float


def fnv1a_hash(s: str) -> int:
    h = 14695981039346656037
    for b in s.encode("utf-8"):
        h = ((h ^ b) * 1099511628211) & 0xFFFFFFFFFFFFFFFF
    return h


def stats_from_samples(samples) -> BenchStats:
    s = sorted(samples)
    n = len(s)
    return BenchStats(s[0], s[n // 2], s[(3 * n) // 4] - s[n // 4])


def run_benchmark(fn: Callable[[], None], warmup: int = 2, runs: int = 7) -> BenchStats:
    for _ in range(warmup):
        fn()
    samples = []
    for _ in range(runs):
        t0 = time.perf_counter_ns()
        fn()
        samples.append((time.perf_counter_ns() - t0) / 1e6)
    samples.sort()
    med = samples[runs // 2]
    return BenchStats(samples[0], med, samples[(3 * runs) // 4] - samples[runs // 4])


def emit_verify_tag(phase: str, seed: int, m1: float, m2: float) -> str:
    hw = mp.cpu_count()
    sig = fnv1a_hash(f"{phase}|{seed}|{hw}|{m1:.4f}|{m2:.4f}")
    return f"VERIFY_HASH[{phase}]: {sig:016X} (P_log={hw})"


def p_series(plog: int):
    ps, p = [], 1
    while p <= plog:
        ps.append(p)
        p *= 2
    if plog not in ps:
        ps.append(plog)
    return ps


def save_md(fname: str, lines) -> None:
    with open(fname, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")