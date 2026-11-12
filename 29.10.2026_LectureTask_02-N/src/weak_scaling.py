import csv
import json
import multiprocessing as mp
import os
import platform
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone

import numpy as np

STUDENT_ID = 230103124
N0 = 800_000 + (STUDENT_ID % 25) * 40_000
K1 = (STUDENT_ID % 8) + 2
K2 = ((STUDENT_ID // 10) % 6) + 3

REPEATS = 3


def sysctl_value(key):
    try:
        result = subprocess.run(
            ["sysctl", "-n", key],
            capture_output=True,
            text=True,
            check=True,
            timeout=3,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return None


def hardware_telemetry():
    physical = os.cpu_count() or 1
    logical = os.cpu_count() or 1
    cpu_brand = platform.processor() or None

    if platform.system() == "Darwin":
        physical_value = sysctl_value("hw.physicalcpu")
        logical_value = sysctl_value("hw.logicalcpu")
        brand_value = sysctl_value("machdep.cpu.brand_string")

        if physical_value and physical_value.isdigit():
            physical = int(physical_value)
        if logical_value and logical_value.isdigit():
            logical = int(logical_value)
        if brand_value:
            cpu_brand = brand_value

        if not cpu_brand or cpu_brand.lower() in ("", "arm"):
            cpu_brand = "Apple Silicon (Apple M1, user-reported)"

    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "student_id": STUDENT_ID,
        "os_platform": platform.platform(),
        "system": platform.system(),
        "machine_architecture": platform.machine(),
        "processor_microarchitecture": cpu_brand or "Not reported by operating system",
        "physical_core_count": physical,
        "logical_thread_count": logical,
        "python_version": sys.version,
        "numpy_version": np.__version__,
        "base_array_elements_per_process_N0": N0,
        "K1": K1,
        "K2": K2,
    }


def compute_chunk(seed_offset, chunk_size, k1, k2):

    data = np.linspace(
        seed_offset,
        seed_offset + 2.0,
        chunk_size,
        dtype=np.float64,
    )
    weights = np.sqrt(np.abs(data * k1) + 1.0)
    kernel_val = 1.0 / (1.0 + (data / k2) ** 2)
    return float(np.sum(weights * kernel_val))


def run_serial(task_count):
    total = 0.0
    for task_index in range(task_count):
        total += compute_chunk(task_index * 2.0, N0, K1, K2)
    return total


def run_parallel(pool, task_count):

    tasks = [
        (task_index * 2.0, N0, K1, K2)
        for task_index in range(task_count)
    ]
    results = pool.starmap(compute_chunk, tasks)
    return float(sum(results))


def median_seconds(function, repeats):
    durations = []
    result = None

    for _ in range(repeats):
        start = time.perf_counter()
        result = function()
        durations.append(time.perf_counter() - start)

    return statistics.median(durations), result


def main():
    telemetry = hardware_telemetry()
    physical_cores = telemetry["physical_core_count"]
    p_phys = min(physical_cores, 16)

    process_counts = sorted(set([1, 2, 4, p_phys, 2 * p_phys]))


    compute_chunk(0.0, 10_000, K1, K2)

    rows = []

    for process_count in process_counts:
        print(f"Running P={process_count} ...", flush=True)

        serial_time, serial_result = median_seconds(
            lambda: run_serial(process_count),
            REPEATS,
        )

        with mp.Pool(processes=process_count) as pool:
            parallel_time, parallel_result = median_seconds(
                lambda: run_parallel(pool, process_count),
                REPEATS,
            )

        if process_count == 1:
            speedup = 1.0
            empirical_serial_fraction = None
        else:
            speedup = serial_time / parallel_time
            empirical_serial_fraction = (
                process_count - speedup
            ) / (process_count - 1)

        efficiency = speedup / process_count

        memory_mb = (
            process_count * N0 * 8 * 3
        ) / (1024 ** 2)
        throughput_gbps = (
            memory_mb / parallel_time / 1024
            if parallel_time > 0
            else 0.0
        )

        rows.append({
            "processes": process_count,
            "total_elements": process_count * N0,
            "T_parallel_seconds": parallel_time,
            "T_serial_seconds": serial_time,
            "speedup": speedup,
            "empirical_serial_fraction": empirical_serial_fraction,
            "weak_scaling_efficiency": efficiency,
            "memory_footprint_MB": memory_mb,
            "estimated_memory_throughput_GBps": throughput_gbps,
            "serial_checksum": serial_result,
            "parallel_checksum": parallel_result,
        })

        print(
            f"  T_parallel={parallel_time:.4f}s, "
            f"T_serial={serial_time:.4f}s, "
            f"speedup={speedup:.3f}, "
            f"efficiency={efficiency:.3f}",
            flush=True,
        )

    with open("telemetry.json", "w", encoding="utf-8") as file:
        json.dump(telemetry, file, indent=4)

    fieldnames = list(rows[0].keys())
    with open("benchmark_results.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\nFinished.")
    print("Created: telemetry.json")
    print("Created: benchmark_results.csv")
    print(f"Student ID: {STUDENT_ID}")
    print(f"N0={N0:,}, K1={K1}, K2={K2}")
    print(f"Process counts: {process_counts}")


if __name__ == "__main__":
    mp.freeze_support()
    main()
