package com.yaki;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.TreeSet;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public class Task7 {

    private static final String STUDENT_ID = "230103124";
    private static final int N = 30_000_000;
    private static final int RUNS = 5;
    private static final double STALL_EFFICIENCY = 0.5;
    private static final int COPY = 0;
    private static final int COMPUTE = 1;
    private static final String[] KERNEL_NAMES = {
            "Kernel A (memory-bound): B[i] = A[i]",
            "Kernel B (compute-bound): B[i] = sin(A[i]) * cos(A[i]) + tan(A[i])"
    };

    private static double[] a;
    private static double[] b;
    private static ExecutorService pool;
    private static volatile double sink;

    public static void main(String[] args) throws Exception {
        int maxCores = Runtime.getRuntime().availableProcessors();

        System.out.println("Student ID: " + STUDENT_ID);
        System.out.println("OS: " + System.getProperty("os.name") + " "
                + System.getProperty("os.version") + " (" + System.getProperty("os.arch") + ")");
        System.out.println("CPU model: " + cpuModel());
        System.out.println("Java: " + System.getProperty("java.version"));
        System.out.println("Logical cores: " + maxCores);
        System.out.printf(Locale.US, "Elements: %,d doubles (%.0f MB per array), runs per point: %d (median, after 1 warm-up)%n",
                N, N * 8.0 / 1e6, RUNS);
        if (maxCores < 2) {
            System.out.println("WARNING: only 1 logical core is available, scaling cannot be demonstrated.");
        }

        a = new double[N];
        b = new double[N];
        for (int i = 0; i < N; i++) {
            a[i] = 0.1 + (i % 1000) * 0.001;
        }

        int[] cores = new TreeSet<>(Arrays.asList(1, 2, maxCores)).stream().mapToInt(Integer::intValue).toArray();
        double[][] wall = new double[2][cores.length];

        for (int k = 0; k < 2; k++) {
            for (int c = 0; c < cores.length; c++) {
                pool = Executors.newFixedThreadPool(cores[c]);
                runOnce(k, cores[c]);
                double[] times = new double[RUNS];
                for (int r = 0; r < RUNS; r++) {
                    long start = System.nanoTime();
                    runOnce(k, cores[c]);
                    times[r] = (System.nanoTime() - start) / 1e6;
                }
                pool.shutdown();
                Arrays.sort(times);
                wall[k][c] = times[RUNS / 2];
                verify(k);
            }
        }

        double[][] efficiency = new double[2][cores.length];
        for (int k = 0; k < 2; k++) {
            System.out.println();
            System.out.println("=== " + KERNEL_NAMES[k] + " ===");
            if (k == COPY) {
                System.out.println("Cores | Wall Time (ms) | Speedup | Efficiency | Bandwidth (GB/s)");
                System.out.println("------+----------------+---------+------------+-----------------");
            } else {
                System.out.println("Cores | Wall Time (ms) | Speedup | Efficiency | Throughput (M elem/s)");
                System.out.println("------+----------------+---------+------------+----------------------");
            }
            for (int c = 0; c < cores.length; c++) {
                double speedup = wall[k][0] / wall[k][c];
                efficiency[k][c] = speedup / cores[c];
                double rate = k == COPY
                        ? (2.0 * 8.0 * N / 1e9) / (wall[k][c] / 1e3)
                        : (N / 1e6) / (wall[k][c] / 1e3);
                System.out.printf(Locale.US, "%5d | %14.3f | %6.2fx | %9.1f%% | %.2f%n",
                        cores[c], wall[k][c], speedup, 100.0 * efficiency[k][c], rate);
            }
        }

        int last = cores.length - 1;
        double effCopy = efficiency[COPY][last];
        double effCompute = efficiency[COMPUTE][last];
        double speedupCopy = wall[COPY][0] / wall[COPY][last];
        double speedupCompute = wall[COMPUTE][0] / wall[COMPUTE][last];
        double bandwidthMax = (2.0 * 8.0 * N / 1e9) / (wall[COPY][last] / 1e3);

        System.out.println();
        System.out.println("===== Verdict =====");
        System.out.printf(Locale.US, "At %d cores: Kernel A speedup %.2fx (efficiency %.1f%%), Kernel B speedup %.2fx (efficiency %.1f%%)%n",
                cores[last], speedupCopy, 100.0 * effCopy, speedupCompute, 100.0 * effCompute);

        if (cores[last] < 2 || maxCores < 2) {
            System.out.println("Not enough cores to judge scaling.");
        } else if (effCopy < STALL_EFFICIENCY && effCompute >= STALL_EFFICIENCY) {
            System.out.printf(Locale.US, "Kernel A (vector copy) STALLED in scaling: memory bandwidth saturated at about %.1f GB/s, "
                    + "so extra cores could not move data faster.%n", bandwidthMax);
            System.out.println("Kernel B (sin/cos/tan) kept scaling: it is limited by CPU computation, not by the memory bus.");
        } else if (effCopy < STALL_EFFICIENCY && effCompute < STALL_EFFICIENCY) {
            System.out.printf(Locale.US, "Both kernels fell below %.0f%% efficiency. Kernel A (vector copy) is the memory-bandwidth-bound one "
                            + "(about %.1f GB/s reached); Kernel B is also limited, probably by core heterogeneity or CPU load.%n",
                    100 * STALL_EFFICIENCY, bandwidthMax);
        } else if (effCopy < effCompute) {
            System.out.printf(Locale.US, "Neither kernel fell below %.0f%% efficiency, but Kernel A (vector copy) scaled worse than Kernel B: "
                            + "it is the one closer to memory bandwidth saturation (about %.1f GB/s).%n",
                    100 * STALL_EFFICIENCY, bandwidthMax);
        } else {
            System.out.println("No memory-bandwidth saturation was detected: Kernel A scaled at least as well as Kernel B.");
        }
        if (cores[last] > 2) {
            System.out.printf(Locale.US, "Extra speedup from 2 cores to %d cores: Kernel A %.2fx, Kernel B %.2fx%n",
                    cores[last], wall[COPY][1] / wall[COPY][last], wall[COMPUTE][1] / wall[COMPUTE][last]);
        }
    }

    private static void runOnce(int kernel, int p) throws Exception {
        int chunk = (N + p - 1) / p;
        List<Callable<Void>> tasks = new ArrayList<>(p);
        for (int from = 0; from < N; from += chunk) {
            final int f = from;
            final int t = Math.min(N, from + chunk);
            if (kernel == COPY) {
                tasks.add(() -> {
                    copyKernel(f, t);
                    return null;
                });
            } else {
                tasks.add(() -> {
                    computeKernel(f, t);
                    return null;
                });
            }
        }
        for (Future<Void> fut : pool.invokeAll(tasks)) {
            fut.get();
        }
        sink = b[N / 2];
    }

    private static void copyKernel(int from, int to) {
        for (int i = from; i < to; i++) {
            b[i] = a[i];
        }
    }

    private static void computeKernel(int from, int to) {
        for (int i = from; i < to; i++) {
            double v = a[i];
            b[i] = Math.sin(v) * Math.cos(v) + Math.tan(v);
        }
    }

    private static void verify(int kernel) {
        int step = N / 1000;
        for (int i = 0; i < N; i += step) {
            double v = a[i];
            double expected = kernel == COPY ? v : Math.sin(v) * Math.cos(v) + Math.tan(v);
            if (Math.abs(b[i] - expected) > 1e-9) {
                throw new IllegalStateException("Wrong result at index " + i + " for " + KERNEL_NAMES[kernel]);
            }
        }
    }

    private static String cpuModel() {
        String os = System.getProperty("os.name").toLowerCase();
        try {
            if (os.contains("linux")) {
                try (BufferedReader r = new BufferedReader(new java.io.FileReader("/proc/cpuinfo"))) {
                    String line;
                    while ((line = r.readLine()) != null) {
                        if (line.startsWith("model name")) {
                            return line.substring(line.indexOf(':') + 1).trim();
                        }
                    }
                }
            } else if (os.contains("mac")) {
                String out = run("sysctl", "-n", "machdep.cpu.brand_string");
                if (!out.isEmpty()) return out;
            } else if (os.contains("win")) {
                String env = System.getenv("PROCESSOR_IDENTIFIER");
                if (env != null && !env.isEmpty()) return env;
            }
        } catch (Exception ignored) {
        }
        return "Unknown (" + System.getProperty("os.arch") + ")";
    }

    private static String run(String... cmd) throws Exception {
        Process p = new ProcessBuilder(cmd).redirectErrorStream(true).start();
        try (BufferedReader r = new BufferedReader(new InputStreamReader(p.getInputStream()))) {
            String line = r.readLine();
            return line == null ? "" : line.trim();
        }
    }
}