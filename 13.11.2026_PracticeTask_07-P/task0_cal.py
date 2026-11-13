import multiprocessing as mp
import time

from config import STUDENT_ID
from harness import emit_verify_tag, save_md

CALLS = 10 ** 6


def main():
    plog = mp.cpu_count()
    clock = time.perf_counter_ns
    t0 = clock()
    for _ in range(CALLS):
        clock()
    total = clock() - t0
    avg_ns = total / CALLS
    tag = emit_verify_tag("PHASE0", STUDENT_ID, float(plog), avg_ns)
    lines = [
        "## Phase 0 - calibration",
        f"- P_log = mp.cpu_count() = {plog}",
        f"- average perf_counter_ns() call latency over {CALLS} calls = {avg_ns:.2f} ns",
        "",
        tag,
    ]
    print("\n".join(lines))
    save_md("results_task0.md", lines)


if __name__ == "__main__":
    main()
