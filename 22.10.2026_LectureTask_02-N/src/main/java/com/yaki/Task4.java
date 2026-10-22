package com.yaki;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.Arrays;
import java.util.Comparator;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.LockSupport;

public class Task4 {
    private static final String STUDENT_ID = "230103124";
    private static final int ITEMS = 1000;
    private static final int WORKERS = 4;
    private static final int MEASURED_RUNS = 5;
    private static final long UNIT_NANOS = 100_000L;
    private static boolean useSleep = false;

    private static class Result {
        double total;
        double delta;
        double[] finish;
        int[] items;
    }

    public static void main(String[] args) throws Exception {
        useSleep = args.length > 0 && args[0].equalsIgnoreCase("sleep");

        System.out.println("Student ID: " + STUDENT_ID);
        System.out.println("OS: " + System.getProperty("os.name") + " "
                + System.getProperty("os.version") + " (" + System.getProperty("os.arch") + ")");
        System.out.println("CPU model: " + cpuModel());
        System.out.println("Java: " + System.getProperty("java.version"));
        System.out.println("Logical cores: " + Runtime.getRuntime().availableProcessors());
        System.out.println("Items: " + ITEMS + ", workers: " + WORKERS
                + ", cost simulation: " + (useSleep ? "sleep (parkNanos)" : "busy-wait"));
        System.out.println("Measured runs per strategy: " + MEASURED_RUNS
                + " (the run with the median total time is shown)");

        runScenario(1, "cost(i) = 0.0001 s * (i % 20)   [as specified]");
        runScenario(2, "cost(i) = 0.0001 s * (i / 50)   [extra: same total work, sorted ascending]");
    }

    private static void runScenario(int scenario, String title) throws Exception {
        long totalNanos = 0;
        for (int i = 0; i < ITEMS; i++) {
            totalNanos += cost(scenario, i);
        }
        double totalWorkMs = totalNanos / 1e6;
        double idealMs = totalWorkMs / WORKERS;

        System.out.println();
        System.out.println("=== Scenario " + scenario + ": " + title + " ===");
        System.out.printf("Total work: %.1f ms, ideal time with %d workers: %.1f ms%n",
                totalWorkMs, WORKERS, idealMs);
        System.out.println();

        String[] names = {
                "A: Static blocks (250 each)",
                "B: Dynamic, chunk = 1",
                "B: Dynamic, chunk = 5"
        };
        int[] chunks = {0, 1, 5};

        System.out.println("Strategy                    | Total (ms) | Finish delta (ms) | Efficiency");
        System.out.println("----------------------------+------------+-------------------+-----------");

        Result[] medians = new Result[names.length];
        for (int s = 0; s < names.length; s++) {
            run(scenario, chunks[s]); // warm-up
            Result[] runs = new Result[MEASURED_RUNS];
            for (int r = 0; r < MEASURED_RUNS; r++) {
                runs[r] = run(scenario, chunks[s]);
            }
            Arrays.sort(runs, Comparator.comparingDouble(x -> x.total));
            medians[s] = runs[MEASURED_RUNS / 2];
            System.out.printf("%-27s | %10.3f | %17.3f | %8.1f%%%n",
                    names[s], medians[s].total, medians[s].delta, 100.0 * idealMs / medians[s].total);
        }

        System.out.println();
        System.out.println("Per-thread finish time (ms) and items processed:");
        for (int s = 0; s < names.length; s++) {
            StringBuilder sb = new StringBuilder(String.format("%-27s :", names[s]));
            for (int t = 0; t < WORKERS; t++) {
                sb.append(String.format("  T%d=%.1f (%d items)", t, medians[s].finish[t], medians[s].items[t]));
            }
            System.out.println(sb);
        }
        System.out.printf("Static vs Dynamic(1): total time ratio %.3fx, finish delta %.3f ms vs %.3f ms%n",
                medians[0].total / medians[1].total, medians[0].delta, medians[1].delta);
    }

    private static Result run(int scenario, int chunk) throws Exception {
        long[] t0 = new long[1];
        CyclicBarrier barrier = new CyclicBarrier(WORKERS, () -> t0[0] = System.nanoTime());
        AtomicInteger next = new AtomicInteger(0);
        double[] finish = new double[WORKERS];
        int[] items = new int[WORKERS];
        Thread[] threads = new Thread[WORKERS];

        for (int t = 0; t < WORKERS; t++) {
            final int id = t;
            threads[t] = new Thread(() -> {
                try {
                    barrier.await();
                } catch (Exception e) {
                    throw new RuntimeException(e);
                }
                int count = 0;
                if (chunk == 0) {
                    int per = (ITEMS + WORKERS - 1) / WORKERS;
                    int from = id * per;
                    int to = Math.min(ITEMS, from + per);
                    for (int i = from; i < to; i++) {
                        simulate(cost(scenario, i));
                        count++;
                    }
                } else {
                    while (true) {
                        int from = next.getAndAdd(chunk);
                        if (from >= ITEMS) break;
                        int to = Math.min(ITEMS, from + chunk);
                        for (int i = from; i < to; i++) {
                            simulate(cost(scenario, i));
                            count++;
                        }
                    }
                }
                finish[id] = (System.nanoTime() - t0[0]) / 1e6;
                items[id] = count;
            });
            threads[t].start();
        }
        for (Thread th : threads) {
            th.join();
        }

        int processed = 0;
        double min = Double.MAX_VALUE, max = 0;
        for (int t = 0; t < WORKERS; t++) {
            processed += items[t];
            min = Math.min(min, finish[t]);
            max = Math.max(max, finish[t]);
        }
        if (processed != ITEMS) {
            throw new IllegalStateException("Processed " + processed + " items instead of " + ITEMS);
        }
        Result res = new Result();
        res.total = max;
        res.delta = max - min;
        res.finish = finish;
        res.items = items;
        return res;
    }

    private static long cost(int scenario, int i) {
        return scenario == 1 ? UNIT_NANOS * (i % 20) : UNIT_NANOS * (i / 50);
    }

    private static void simulate(long nanos) {
        if (nanos <= 0) return;
        long end = System.nanoTime() + nanos;
        if (useSleep) {
            long rem;
            while ((rem = end - System.nanoTime()) > 0) {
                LockSupport.parkNanos(rem);
            }
        } else {
            while (System.nanoTime() < end) {
                Thread.onSpinWait();
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