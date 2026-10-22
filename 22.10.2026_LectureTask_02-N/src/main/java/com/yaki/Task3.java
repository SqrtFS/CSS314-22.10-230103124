package com.yaki;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.VarHandle;
import java.util.Arrays;
import java.util.concurrent.CyclicBarrier;

public class Task3 {

    private static final String STUDENT_ID = "230103124";
    private static final long ITERATIONS = 50_000_000L;
    private static final long WARMUP_ITERATIONS = 5_000_000L;
    private static final int MEASURED_RUNS = 5;

    private static final VarHandle AH = MethodHandles.arrayElementVarHandle(long[].class);

    public static void main(String[] args) throws Exception {
        int logical = Runtime.getRuntime().availableProcessors();
        int physical = physicalCores(logical);

        int threads = args.length > 0 ? Integer.parseInt(args[0]) : physical;

        System.out.println("Student ID: " + STUDENT_ID);
        System.out.println("OS: " + System.getProperty("os.name") + " "
                + System.getProperty("os.version") + " (" + System.getProperty("os.arch") + ")");
        System.out.println("CPU model: " + cpuModel());
        System.out.println("Java: " + System.getProperty("java.version"));
        System.out.println("Logical cores: " + logical + ", physical cores: " + physical);
        System.out.println("Worker threads (N): " + threads);
        System.out.println("Increments per thread: " + ITERATIONS);
        System.out.println("Warm-up: 1 run of " + WARMUP_ITERATIONS + " increments, measured runs: "
                + MEASURED_RUNS + " (median wall time is reported)");
        System.out.println();


        String[] names = {
                "Unpadded shared (8 B apart)",
                "Padded 64 B (stride 8)",
                "Padded 128 B (stride 16)",
                "Local variable + 1 final write"
        };
        int[] strides = {1, 8, 16, 1};
        boolean[] local = {false, false, false, true};

        double[] wall = new double[names.length];
        for (int v = 0; v < names.length; v++) {
            run(threads, strides[v], local[v], WARMUP_ITERATIONS);
            double[] times = new double[MEASURED_RUNS];
            for (int r = 0; r < MEASURED_RUNS; r++) {
                times[r] = run(threads, strides[v], local[v], ITERATIONS);
            }
            Arrays.sort(times);
            wall[v] = times[MEASURED_RUNS / 2];
        }

        System.out.println("Variant                        | Wall Time (ms) | Slowdown of Unpadded vs this variant");
        System.out.println("-------------------------------+----------------+-------------------------------------");
        for (int v = 0; v < names.length; v++) {
            System.out.printf("%-30s | %14.3f | %.2fx%n", names[v], wall[v], wall[0] / wall[v]);
        }
        System.out.println();
        System.out.printf("Execution ratio Unpadded / Padded 64 B  : %.2fx%n", wall[0] / wall[1]);
        System.out.printf("Execution ratio Unpadded / Padded 128 B : %.2fx%n", wall[0] / wall[2]);
        System.out.printf("Execution ratio Unpadded / Local        : %.2fx%n", wall[0] / wall[3]);
        System.out.println("All counters verified: each equals " + ITERATIONS);
    }

    private static double run(int threads, int stride, boolean localMode, long iters) throws Exception {
        long[] sharedCounts = new long[threads * stride];
        CyclicBarrier barrier = new CyclicBarrier(threads + 1);
        Thread[] workers = new Thread[threads];

        for (int t = 0; t < threads; t++) {
            final int idx = t * stride;
            workers[t] = new Thread(() -> {
                try {
                    barrier.await();
                } catch (Exception e) {
                    throw new RuntimeException(e);
                }
                if (localMode) {
                    localLoop(sharedCounts, idx, iters);
                } else {
                    sharedLoop(sharedCounts, idx, iters);
                }
            });
            workers[t].start();
        }

        barrier.await();
        long start = System.nanoTime();
        for (Thread w : workers) {
            w.join();
        }
        long end = System.nanoTime();

        for (int t = 0; t < threads; t++) {
            long v = (long) AH.getOpaque(sharedCounts, t * stride);
            if (v != iters) {
                throw new IllegalStateException("Wrong count at " + t + ": " + v);
            }
        }
        return (end - start) / 1e6;
    }

    private static void sharedLoop(long[] counts, int idx, long iters) {
        for (long k = 0; k < iters; k++) {
            AH.setOpaque(counts, idx, (long) AH.getOpaque(counts, idx) + 1L);
        }
    }

    private static void localLoop(long[] counts, int idx, long iters) {
        long local = 0;
        for (long k = 0; k < iters; k++) {
            local++;
            local ^= local >>> 63;
        }
        AH.setOpaque(counts, idx, local);
    }

    private static int physicalCores(int fallback) {
        try {
            if (System.getProperty("os.name").toLowerCase().contains("mac")) {
                String out = run("sysctl", "-n", "hw.physicalcpu");
                if (!out.isEmpty()) return Integer.parseInt(out);
            }
        } catch (Exception ignored) {
        }
        return fallback;
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