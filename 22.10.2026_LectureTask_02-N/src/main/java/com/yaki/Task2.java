package com.yaki;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Random;
import java.util.TreeSet;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public class Task2 {

    private static final String STUDENT_ID = "230103124";
    private static final int N = 20_000_000;
    private static final double P = 0.95;
    private static final int WARMUP_RUNS = 3;
    private static final int MEASURED_RUNS = 7;

    public static void main(String[] args) throws Exception {
        long seed = Long.parseLong(STUDENT_ID.replaceAll("\\D", ""));
        int maxCores = Runtime.getRuntime().availableProcessors();

        System.out.println("Student ID: " + STUDENT_ID);
        System.out.println("OS: " + System.getProperty("os.name") + " "
                + System.getProperty("os.version") + " (" + System.getProperty("os.arch") + ")");
        System.out.println("CPU model: " + cpuModel());
        System.out.println("Java: " + System.getProperty("java.version"));
        System.out.println("Logical cores (availableProcessors): " + maxCores);

        // Same data as Task 1: 20,000,000 float64 values from the Student ID seed
        Random rng = new Random(seed);
        double[] data = new double[N];
        for (int i = 0; i < N; i++) {
            data[i] = rng.nextDouble();
        }
        System.out.println("Array size: " + N + ", seed: " + seed);
        System.out.println("Warm-up runs: " + WARMUP_RUNS + ", measured runs: " + MEASURED_RUNS
                + " (median wall time is reported)");

        double serialSum = serialSum(data);
        System.out.printf("Reference serial sum: %.6f%n%n", serialSum);

        // Worker counts: 1, 2, 4, max_cores, max_cores * 2 (duplicates removed, sorted)
        TreeSet<Integer> counts = new TreeSet<>(Arrays.asList(1, 2, 4, maxCores, maxCores * 2));

        System.out.println("Cores | Wall Time (ms) | Speedup | Amdahl Upper Bound | Sum");
        System.out.println("------+----------------+---------+--------------------+----------------");

        double t1 = -1;
        for (int p : counts) {
            ExecutorService pool = Executors.newFixedThreadPool(p);
            double sum = 0;

            for (int i = 0; i < WARMUP_RUNS; i++) {
                sum = parallelSum(pool, data, p);
            }

            double[] times = new double[MEASURED_RUNS];
            for (int i = 0; i < MEASURED_RUNS; i++) {
                long start = System.nanoTime();
                sum = parallelSum(pool, data, p);
                long end = System.nanoTime();
                times[i] = (end - start) / 1e6;
            }
            pool.shutdown();

            Arrays.sort(times);
            double wall = times[MEASURED_RUNS / 2]; // median
            if (p == 1) {
                t1 = wall;
            }
            double speedup = t1 / wall;
            double amdahl = 1.0 / ((1.0 - P) + P / p);

            System.out.printf("%5d | %14.3f | %7.2f | %18.2f | %.6f%n", p, wall, speedup, amdahl, sum);
        }

        System.out.println();
        System.out.println("Speedup S(p) = T(1) / T(p); Amdahl bound = 1 / ((1 - P) + P / p), P = " + P);
    }

    private static double serialSum(double[] data) {
        double s = 0.0;
        for (double v : data) {
            s += v;
        }
        return s;
    }

    private static double parallelSum(ExecutorService pool, double[] data, int p) throws Exception {
        int chunk = (data.length + p - 1) / p;
        List<Callable<Double>> tasks = new ArrayList<>(p);
        for (int t = 0; t < p; t++) {
            final int from = t * chunk;
            final int to = Math.min(data.length, from + chunk);
            tasks.add(() -> {
                double s = 0.0;
                for (int i = from; i < to; i++) {
                    s += data[i];
                }
                return s;
            });
        }
        double total = 0.0;
        for (Future<Double> f : pool.invokeAll(tasks)) {
            total += f.get();
        }
        return total;
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