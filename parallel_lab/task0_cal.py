import time
import multiprocessing as mp
from harness import emit_verify_tag


def calibrate_timer():
    iterations = 2_000_000
    t0 = time.perf_counter_ns()
    for _ in range(iterations):
        time.perf_counter_ns()
    t1 = time.perf_counter_ns()

    avg_latency_ns = (t1 - t0) / iterations
    return avg_latency_ns


if __name__ == "__main__":
    cpu_count = mp.cpu_count()
    avg_lat = calibrate_timer()

    print(f"CPU Count: {cpu_count}")
    print(f"Average timer call latency: {avg_lat:.2f} ns")

    student_seed = 230103124
    verify_tag = emit_verify_tag("PHASE0", student_seed, avg_lat, float(cpu_count))
    print(verify_tag)