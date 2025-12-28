# GPUStat: Global Infrastructure Optimizer & Benchmark Suite

A comprehensive toolkit for fetching cloud instance prices (GPU/CPU), optimizing server clusters for geographical coverage and fault tolerance, and performing high-fidelity statistical benchmarking of rented infrastructure.

## Features

### 1. High-Fidelity Pricing Database
- **Live Fetching**: Retrieves over 30,000 live pricing entries from the Azure Retail Prices API and others.
- **Multi-Category**: Explicitly marks instances as `gpu`, `cpu`, `storage`, or `backup`.
- **Multi-Format**: Generates `prices.db` (SQLite), `prices.csv`, and `prices.hpp` (C++23 header).
- **Extensive Providers**: Includes AWS, Azure, GCP, Cloudflare, CoreWeave, Lambda Labs, Hetzner, Vultr, and specialized budget/VPS providers.

### 2. Infrastructure Optimization
- **Population-Aware**: Uses top 50 US cities data to maximize reach.
- **Fault-Tolerant**: Constraints for 2-fault tolerance (3x redundancy) and Multi-Vendor redundancy (min 2 companies per city).
- **Sync-Constrained**: Solves for optimal placement under 1ms to 20ms inter-server synchronization windows.
- **Risk-Weighted**: Incorporates a Gaussian Risk Variable ($\sigma_{risk}$) for each vendor based on history (e.g., OVHcloud fire incidents).

### 3. C++23 Benchmark Suite (64 Tests)
- **Architectural Discovery**: 64 orthogonal tests including L1/L3 latency, False Sharing, Context Switching, and TLB misses.
- **Statistical Analysis**: Automatically identifies performance distributions (Normal, Cauchy, Log-Normal, Bimodal).
- **Dynamic Convergence**: Runs tests until a 99.9% Confidence Interval is reached or timeout.
- **Tail Latency**: Focuses on P99.9 "worst-case" performance rather than just means.

## File Structure

- `fetch_prices.py`: The main data collection engine.
- `benchmark/benchmark.cpp`: The full 64-test C++23 suite.
- `optimal_n_scaling.py`: Optimization script for scaling configurations.
- `compute_optimizer.py`: Task-based solver (e.g., "Generate 1024 images in 2h").
- `vendor/`: Detailed risk analysis reports for each infrastructure provider.
- `backbone_info.md`: Analysis of the US internet backbone and latency models.

## Usage

### Updating the Database
```bash
python3 fetch_prices.py
```

### Running Benchmarks
```bash
g++ -std=c++23 benchmark/benchmark.cpp -o benchmark/bench
./benchmark/bench
```

### Optimizing a Configuration
```bash
python3 optimal_n_scaling.py
```

## Risk Model
We use a Gaussian risk variable to quantify provider reliability:
- **Low Risk ($\sigma \approx 0.15$):** Azure, AWS, GCP.
- **Moderate Risk ($\sigma \approx 0.40$):** OVHcloud, Vultr.
- **High Risk ($\sigma \ge 0.60$):** Budget VPS marketplaces.

## License
MIT
