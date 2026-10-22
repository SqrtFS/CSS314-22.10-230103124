package com.yaki;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.lang.invoke.MethodHandles;
import java.lang.invoke.VarHandle;
import java.util.Arrays;
import java.util.Locale;
import java.util.concurrent.CyclicBarrier;
import java.util.concurrent.atomic.AtomicInteger;

public class Task6 {

    private static final String STUDENT_ID = "230103124";
    private static final int THREADS = 4;
    private static final int INCREMENTS = 2_000_000;
    private static final int EXPECTED = THREADS * INCREMENTS;
    private static final int RUNS = 5;

    private static int plainCounter = 0;

    private static final VarHandle AH = MethodHandles.arrayElementVarHandle(int[].class);
    private static final int[] opaqueCell = new int[1];

    private static final AtomicInteger atomicCounter = new AtomicInteger();

    private static final int PLAIN = 0, OPAQUE = 1, ATOMIC = 2;
    private static final String[] NAMES = {
            "Unsafe: plain counter++ (no synchronization)",
            "Unsafe: non-atomic load + store forced on every increment",
            "Safe: AtomicInteger.incrementAndGet()"
    };

    public static void main(String[] args) throws Exception {
        System.out.println("Student ID: " + STUDENT_ID);
        System.out.println("OS: " + System.getProperty("os.name") + " "
                + System.getProperty("os.version") + " (" + System.getProperty("os.arch") + ")");
        System.out.println("CPU model: " + cpuModel());
        System.out.println("Java: " + System.getProperty("java.version"));
        System.out.println("Logical cores: " + Runtime.getRuntime().availableProcessors());
        System.out.println("Threads: " + THREADS + ", increments per thread: " + String.format(Locale.US, "%,d", INCREMENTS));
        System.out.println("Expected final value: " + String.format(Locale.US, "%,d", EXPECTED));
        System.out.println("Runs per variant: " + RUNS + " (after 1 warm-up run)");

        double[] medianTime = new double[3];
        double[] avgLost = new double[3];

        for (int v = 0; v < 3; v++) {
            System.out.println();
            System.out.println("--- " + NAMES[v] + " ---");
            run(v);

            double[] times = new double[RUNS];
            double lostSum = 0;
            for (int r = 0; r < RUNS; r++) {
                long[] res = run(v);
                long actual = res[0];
                times[r] = res[1] / 1000.0;
                long lost = EXPECTED - actual;
                double lostPct = 100.0 * lost / EXPECTED;
                lostSum += lostPct;
                System.out.printf(Locale.US, "Run %d: actual = %,d | lost updates = %,d (%.2f%%) | wall time = %.3f ms%n",
                        r + 1, actual, lost, lostPct, times[r]);
                if (v == ATOMIC && actual != EXPECTED) {
                    throw new IllegalStateException("AtomicInteger lost updates: " + actual);
                }
            }
            Arrays.sort(times);
            medianTime[v] = times[RUNS / 2];
            avgLost[v] = lostSum / RUNS;
            System.out.printf(Locale.US, "Average lost: %.2f%% | median wall time: %.3f ms%n", avgLost[v], medianTime[v]);
        }

        System.out.println();
        System.out.println("===== Summary =====");
        System.out.printf(Locale.US, "Expected final value : %,d%n", EXPECTED);
        for (int v = 0; v < 3; v++) {
            System.out.printf(Locale.US, "%-58s lost %6.2f%% | %9.3f ms%n", NAMES[v], avgLost[v], medianTime[v]);
        }
        System.out.println();
        System.out.println("Synchronization penalty of AtomicInteger (correct result, 0% lost) = T(atomic) - T(unsafe):");
        printPenalty("vs unsafe with forced load/store (fair comparison)", medianTime[ATOMIC], medianTime[OPAQUE]);
        printPenalty("vs unsafe plain counter++ (JIT may keep it in a register)", medianTime[ATOMIC], medianTime[PLAIN]);
    }

    private static void printPenalty(String label, double atomicMs, double unsafeMs) {
        System.out.printf(Locale.US, "  %-62s %+.3f ms (atomic time = %.2fx of unsafe time)%n",
                label, atomicMs - unsafeMs, atomicMs / unsafeMs);
    }

    private static long[] run(int variant) throws Exception {
        plainCounter = 0;
        opaqueCell[0] = 0;
        atomicCounter.set(0);

        long[] t0 = new long[1];
        CyclicBarrier barrier = new CyclicBarrier(THREADS, () -> t0[0] = System.nanoTime());
        Thread[] threads = new Thread[THREADS];
        for (int t = 0; t < THREADS; t++) {
            threads[t] = new Thread(() -> {
                try {
                    barrier.await();
                } catch (Exception e) {
                    throw new RuntimeException(e);
                }
                switch (variant) {
                    case PLAIN -> plainLoop();
                    case OPAQUE -> opaqueLoop();
                    default -> atomicLoop();
                }
            });
            threads[t].start();
        }
        for (Thread th : threads) {
            th.join();
        }
        long end = System.nanoTime();

        long actual = switch (variant) {
            case PLAIN -> plainCounter;
            case OPAQUE -> (int) AH.getVolatile(opaqueCell, 0);
            default -> atomicCounter.get();
        };
        return new long[]{actual, (end - t0[0]) / 1000};
    }

    private static void plainLoop() {
        for (int i = 0; i < INCREMENTS; i++) {
            plainCounter++;
        }
    }

    private static void opaqueLoop() {
        for (int i = 0; i < INCREMENTS; i++) {
            AH.setOpaque(opaqueCell, 0, (int) AH.getOpaque(opaqueCell, 0) + 1);
        }
    }

    private static void atomicLoop() {
        for (int i = 0; i < INCREMENTS; i++) {
            atomicCounter.incrementAndGet();
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