// Task 22 - Weak-scaling micro-benchmark (OpenMP).
//
// Workload: midpoint-rule integration of pi = int_0^1 4/(1+x^2) dx.
//   * Each thread integrates its own sub-interval with a FIXED number of steps k  (weak scaling:
//     total work = k * threads, work per thread constant).
//   * A deliberately SERIAL section (single-thread initialisation of an array) of fixed size is
//     executed first, so that a measurable serial fraction alpha exists.
// Prints one CSV row:  threads,run,k,serial_n,t_total,t_serial,t_parallel,pi
//
// Build: g++ -O2 -fopenmp weak_scale_bench.cpp -o weak_scale_bench
// Run  : ./weak_scale_bench --threads 4 --k 100000000 --serial-n 1000000 --run 0
#include <omp.h>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

using clk = std::chrono::steady_clock;
static double secs(clk::time_point a, clk::time_point b) { return std::chrono::duration<double>(b - a).count(); }

int main(int argc, char** argv) {
    long k = 100000000L, serial_n = 1000000L;
    int threads = omp_get_max_threads(), run = 0, header = 0;
    for (int i = 1; i < argc; ++i) {
        if (!strcmp(argv[i], "--threads") && i + 1 < argc) threads = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--k") && i + 1 < argc) k = atol(argv[++i]);
        else if (!strcmp(argv[i], "--serial-n") && i + 1 < argc) serial_n = atol(argv[++i]);
        else if (!strcmp(argv[i], "--run") && i + 1 < argc) run = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--header")) header = 1;
    }
    omp_set_num_threads(threads);
    if (header) std::printf("threads,run,k,serial_n,t_total,t_serial,t_parallel,pi\n");

    auto t0 = clk::now();

    // ---- serial section (constant size regardless of thread count) ----
    std::vector<double> a(serial_n);
    double acc = 0.0;
    for (long i = 0; i < serial_n; ++i) { a[i] = std::sqrt((double)i + 1.0); acc += a[i]; }
    auto t1 = clk::now();

    // ---- parallel section: k steps per thread over its own slice of [0,1] ----
    double pi = 0.0;
    const double slice = 1.0 / threads;
    const double h = slice / (double)k;
    #pragma omp parallel num_threads(threads) reduction(+ : pi)
    {
        int t = omp_get_thread_num();
        double x0 = t * slice, local = 0.0;
        for (long i = 0; i < k; ++i) {
            double x = x0 + (i + 0.5) * h;
            local += 4.0 / (1.0 + x * x);
        }
        pi += local * h;
    }
    auto t2 = clk::now();

    // acc is consumed to keep the serial loop alive
    std::printf("%d,%d,%ld,%ld,%.9f,%.9f,%.9f,%.12f\n", threads, run, k, serial_n,
                secs(t0, t2), secs(t0, t1), secs(t1, t2), pi + (acc < 0 ? 1.0 : 0.0));
    return 0;
}
