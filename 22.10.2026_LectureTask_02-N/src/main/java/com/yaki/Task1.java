package com.yaki;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.util.Random;

public class Task1 {

    private static final String STUDENT_ID = "230103124";
    private static final int N = 20_000_000;

    public static void main(String[] args) {
        long seed = seedFromId(STUDENT_ID);

        System.out.println("Student ID: " + STUDENT_ID);
        System.out.println("Seed: " + seed);
        System.out.println("OS: " + System.getProperty("os.name") + " "
                + System.getProperty("os.version") + " (" + System.getProperty("os.arch") + ")");
        System.out.println("CPU model: " + cpuModel());
        System.out.println("Java: " + System.getProperty("java.version")
                + " (" + System.getProperty("java.vm.name") + ")");
        System.out.println("Logical cores (availableProcessors): "
                + Runtime.getRuntime().availableProcessors());

        // 2. 20,000,000 float64
        long genStart = System.nanoTime();
        Random rng = new Random(seed);
        double[] data = new double[N];
        for (int i = 0; i < N; i++) {
            data[i] = rng.nextDouble();
        }
        long genEnd = System.nanoTime();

        // 3. Serial sum and standard deviation (single thread)
        long start = System.nanoTime();

        double sum = 0.0;
        for (int i = 0; i < N; i++) {
            sum += data[i];
        }
        double mean = sum / N;

        double sqDiff = 0.0;
        for (int i = 0; i < N; i++) {
            double d = data[i] - mean;
            sqDiff += d * d;
        }
        double stdDev = Math.sqrt(sqDiff / N); // population standard deviation

        long end = System.nanoTime();

        // 4. Timing
        System.out.println("Array size: " + N);
        System.out.printf("Sum: %.6f%n", sum);
        System.out.printf("Mean: %.10f%n", mean);
        System.out.printf("Standard deviation (population): %.10f%n", stdDev);
        System.out.printf("Generation time: %.3f ms%n", (genEnd - genStart) / 1e6);
        System.out.printf("Serial compute time (sum + std): %.3f ms%n", (end - start) / 1e6);
        System.out.printf("Total wall-clock time (generate + compute): %.3f ms%n", (end - genStart) / 1e6);
    }

    private static long seedFromId(String id) {
        String digits = id.replaceAll("\\D", "");
        if (!digits.isEmpty() && digits.length() <= 18) {
            return Long.parseLong(digits);
        }
        return id.hashCode();
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