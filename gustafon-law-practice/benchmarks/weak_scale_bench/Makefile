CXX ?= g++
CXXFLAGS ?= -O2 -fopenmp -std=c++17
all: weak_scale_bench
weak_scale_bench: weak_scale_bench.cpp
	$(CXX) $(CXXFLAGS) $< -o $@
clean:
	rm -f weak_scale_bench
