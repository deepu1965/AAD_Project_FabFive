import argparse
import csv
import sys
import time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from solvers import walksat

def run_experiment(benchmarks_dir: Path, output_file: Path):
    noise_values = [0.1, 0.3, 0.5, 0.7]
    benchmark_files = sorted(list(benchmarks_dir.glob("random_3sat_100v_*.cnf")))
    if not benchmark_files:
        return
    results = []
    for noise in noise_values:
        for cnf_path in benchmark_files:
            start_time = time.perf_counter()
            result = walksat.run_solver(cnf_path, max_flips=10000, noise=noise, restarts=1)
            elapsed = time.perf_counter() - start_time
            
            record = {
                "solver": "walksat",
                "benchmark_file": cnf_path.name,
                "noise": noise,
                "status": result["status"],
                "flips": result["flips"],
                "elapsed_time": elapsed
            }
            results.append(record)

    output_file.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["solver", "benchmark_file", "noise", "status", "flips", "elapsed_time"]
    
    with open(output_file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmarks", default="benchmarks/random_sat")
    parser.add_argument("--output", default="results/parameter_sensitivity.csv")
    args = parser.parse_args()
    run_experiment(Path(args.benchmarks), Path(args.output))

if __name__ == "__main__":
    main()
