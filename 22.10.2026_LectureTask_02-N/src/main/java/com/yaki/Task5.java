package com.yaki;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.Callable;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.function.IntToDoubleFunction;

public class Task5 {

    private static final String STUDENT_ID = "230103124";
    private static final int[] SIZES = {100, 1_000, 10_000, 100_000, 1_000_000, 10_000_000};
    private static final double A = 2.5;
    private static final double B = 1.25;
    private static final long TARGET_ELEMENTS = 20_000_000L;
    private static final int MIN_REPS = 5;
    private static final int MAX_REPS = 100_000;
    private static final int TRIALS = 5;
    private static final int REFINE_STEPS = 6;

    private static volatile double sink;
    private static ExecutorService pool;
    private static int workers;

    public static void main(String[] args) throws Exception {
        workers = args.length > 0 ? Integer.parseInt(args[0]) : Runtime.getRuntime().availableProcessors();
        pool = Executors.newFixedThreadPool(workers);

        System.out.println("Student ID: " + STUDENT_ID);
        System.out.println("OS: " + System.getProperty("os.name") + " "
                + System.getProperty("os.version") + " (" + System.getProperty("os.arch") + ")");
        System.out.println("CPU model: " + cpuModel());
        System.out.println("Java: " + System.getProperty("java.version"));
        System.out.println("Logical cores: " + Runtime.getRuntime().availableProcessors()
                + ", worker threads used: " + workers);
        if (workers < 2) {
            System.out.println("WARNING: only 1 worker thread, so there is no real parallelism; "
                    + "the numbers below only show the overhead.");
        }
        System.out.println("Operation: y[i] = a * x[i] + b  (a = " + A + ", b = " + B + ")");
        System.out.println("Timing: per-operation time, median of " + TRIALS
                + " batches; thread pool is created once and not included in the timing.");
        System.out.println();

        System.out.println("           N | Serial (us/op) | Parallel (us/op) | Speedup | Faster");
        System.out.println("-------------+----------------+------------------+---------+---------");

        double[] speedups = new double[SIZES.length];
        for (int i = 0; i < SIZES.length; i++) {
            double[] r = measure(SIZES[i]);
            speedups[i] = r[0] / r[1];
            printRow(SIZES[i], r[0], r[1]);
        }
        System.out.println();

        reportCrossover(SIZES, speedups, Task5::speedupWithRow);

        pool.shutdown();
    }

    // ---------------------------------------------------------------- analysis

    static void reportCrossover(int[] sizes, double[] speedups, IntToDoubleFunction speedupAt) {
        System.out.println("===== Crossover analysis =====");
        int firstFaster = -1;
        for (int i = sizes.length - 1; i >= 0; i--) {
            if (speedups[i] > 1.0) {
                firstFaster = i;
            } else {
                break;
            }
        }

        if (firstFaster == -1) {
            System.out.printf(Locale.US, "RESULT: multi-threading was never faster than serial for N up to %,d "
                            + "(speedup at N=%,d: %.2fx).%n", sizes[sizes.length - 1], sizes[sizes.length - 1],
                    speedups[sizes.length - 1]);
            return;
        }
        if (firstFaster == 0) {
            System.out.printf(Locale.US, "RESULT: multi-threading was already faster at the smallest tested N=%,d; "
                    + "the crossover is below that.%n", sizes[0]);
            return;
        }

        int lo = sizes[firstFaster - 1];
        int hi = sizes[firstFaster];
        double sLo = speedups[firstFaster - 1];
        double sHi = speedups[firstFaster];
        System.out.printf(Locale.US, "Coarse bracket: SLOWER at N=%,d (%.2fx), FASTER at N=%,d (%.2fx)%n",
                lo, sLo, hi, sHi);
        System.out.println("Refinement (bisection in log scale between those sizes):");

        for (int step = 1; step <= REFINE_STEPS; step++) {
            if (hi - lo <= 1) break;
            int mid = (int) Math.round(Math.sqrt((double) lo * hi));
            if (mid <= lo || mid >= hi) break;
            double s = speedupAt.applyAsDouble(mid);
            if (s > 1.0) {
                hi = mid;
                sHi = s;
            } else {
                lo = mid;
                sLo = s;
            }
        }

        double t = -Math.log(sLo) / (Math.log(sHi) - Math.log(sLo));
        double estimate = Math.exp(Math.log(lo) + t * (Math.log(hi) - Math.log(lo)));

        System.out.println();
        System.out.printf(Locale.US, "RESULT: multi-threading is SLOWER than serial up to N = %,d (%.2fx)%n", lo, sLo);
        System.out.printf(Locale.US, "        and FASTER than serial from N = %,d (%.2fx).%n", hi, sHi);
        System.out.printf(Locale.US, "        Tipping point range: %,d < N <= %,d%n", lo, hi);
        System.out.printf(Locale.US, "        Estimated break-even (speedup = 1.00): N ~ %,d elements%n", Math.round(estimate));
    }

    private static double speedupWithRow(int n) {
        try {
            double[] r = measure(n);
            printRow(n, r[0], r[1]);
            return r[0] / r[1];
        } catch (Exception e) {
            throw new RuntimeException(e);
        }
    }

    private static void printRow(int n, double serialUs, double parallelUs) {
        double speedup = serialUs / parallelUs;
        System.out.printf(Locale.US, "%,12d | %14.4f | %16.4f | %6.2fx | %s%n",
                n, serialUs, parallelUs, speedup, speedup > 1.0 ? "Parallel" : "Serial");
    }

    // ---------------------------------------------------------------- measurement


    private static double[] measure(int n) throws Exception {
        double[] x = new double[n];
        double[] y = new double[n];
        for (int i = 0; i < n; i++) {
            x[i] = (i % 1000) * 0.001;
        }
        verify(x);

        int reps = (int) Math.max(MIN_REPS, Math.min(MAX_REPS, TARGET_ELEMENTS / n));

        serialBatch(x, y, reps);
        parallelBatch(x, y, reps);

        double[] serial = new double[TRIALS];
        double[] parallel = new double[TRIALS];
        for (int t = 0; t < TRIALS; t++) {
            long s0 = System.nanoTime();
            serialBatch(x, y, reps);
            serial[t] = (System.nanoTime() - s0) / 1e3 / reps;

            long p0 = System.nanoTime();
            parallelBatch(x, y, reps);
            parallel[t] = (System.nanoTime() - p0) / 1e3 / reps;
        }
        Arrays.sort(serial);
        Arrays.sort(parallel);
        return new double[]{serial[TRIALS / 2], parallel[TRIALS / 2]};
    }


    private static void verify(double[] x) throws Exception {
        double[] ys = new double[x.length];
        double[] yp = new double[x.length];
        kernel(x, ys, A, B, 0, x.length);
        parallelOnce(x, yp, A);
        if (!Arrays.equals(ys, yp)) {
            throw new IllegalStateException("Parallel result differs from serial for N=" + x.length);
        }
    }

    private static void serialBatch(double[] x, double[] y, int reps) {
        double acc = 0;
        for (int r = 0; r < reps; r++) {
            kernel(x, y, A + r * 1e-9, B, 0, x.length);
            acc += y[y.length - 1];
        }
        sink = acc;
    }

    private static void parallelBatch(double[] x, double[] y, int reps) throws Exception {
        double acc = 0;
        for (int r = 0; r < reps; r++) {
            parallelOnce(x, y, A + r * 1e-9);
            acc += y[y.length - 1];
        }
        sink = acc;
    }


    private static void parallelOnce(double[] x, double[] y, double a) throws Exception {
        int n = x.length;
        int chunk = (n + workers - 1) / workers;
        List<Callable<Void>> tasks = new ArrayList<>(workers);
        for (int from = 0; from < n; from += chunk) {
            final int f = from;
            final int t = Math.min(n, from + chunk);
            tasks.add(() -> {
                kernel(x, y, a, B, f, t);
                return null;
            });
        }
        for (Future<Void> fut : pool.invokeAll(tasks)) {
            fut.get();
        }
    }

    private static void kernel(double[] x, double[] y, double a, double b, int from, int to) {
        for (int i = from; i < to; i++) {
            y[i] = a * x[i] + b;
        }
    }

    // ---------------------------------------------------------------- system info

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