# Comparative Analysis of Boolean Satisfiability Algorithms

This project implements and benchmarks five distinct Boolean Satisfiability (SAT) solvers from scratch. It is designed to empirically analyze the performance differences between complete algorithms (DPLL, CDCL) and stochastic local search algorithms (WalkSAT, probSAT) across various problem types, including Random 3-SAT and Sudoku.

## Project Structure

The project follows a modular architecture:

```
.
├── solvers/                # Core solver implementations (Source Code)
│   ├── dpll_baseline.py    # Baseline DPLL (Recursive backtracking)
│   ├── dpll_jw.py          # DPLL with Jeroslow-Wang heuristic
│   ├── cdcl.py             # CDCL with VSIDS, 2-Watched Literals, 1-UIP Learning
│   ├── walksat.py          # WalkSAT (Stochastic Local Search)
│   └── probsat.py          # probSAT (Probabilistic Local Search)
├── harness/                # Experimental infrastructure
│   ├── run_experiments.py  # Main test harness for running all solvers
│   ├── generate_benchmarks.py # Script to generate Random 3-SAT instances
│   └── run_parameter_sensitivity.py # Script for WalkSAT noise parameter study
├── utils/                  # Shared utilities
│   ├── cnf_parser.py       # DIMACS CNF parser
│   ├── sudoku_encoder.py   # Sudoku-to-CNF encoder
│   └── generate_sudoku_dataset.py # Generator for Sudoku benchmark suite
├── analysis/               # Data analysis and visualization
│   ├── generate_plots.py   # Generates all report graphs from results.csv
│   └── plot_walksat_noise.py # Generates parameter sensitivity plots
├── results/                # Output directory for experiment data and plots
│   ├── results.csv         # Main experimental data
│   ├── parameter_sensitivity.csv # WalkSAT noise sweep data
│   └── plots/              # Generated graphs (PNG)
└── report/                 # Documentation
    ├── final_report.pdf    # Academic report template
    └── presentation.pdf    # Presentation slides   
```

## Getting Started

### Prerequisites

- Python 3.10+
- Recommended: A virtual environment

### Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Set up the environment:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # On Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    ```

## Usage Guide

### 1. Generating Benchmarks

First, generate the benchmark datasets (Random 3-SAT and Sudoku):

```bash
# Generate Random 3-SAT instances (50-200 vars)
python3 harness/generate_benchmarks.py

# Generate Sudoku instances (Satisfiable & Unsolvable)
python3 utils/generate_sudoku_dataset.py
```

### 2. Running Solvers Individually

You can run any solver on a specific `.cnf` file. The output is a JSON object containing status and metrics.

**Example (CDCL on Sudoku):**
```bash
python3 solvers/cdcl.py --cnf benchmarks/sudoku/sudoku_sat_01.cnf
```

**Example (WalkSAT on Random 3-SAT):**
```bash
python3 solvers/walksat.py --cnf benchmarks/random_sat/random_3sat_100v_426c_01.cnf --max-flips 100000
```

### 3. Running the Full Experiment Suite

The test harness executes all 5 solvers against the entire benchmark suite and records metrics to `results/results.csv`.

```bash
python3 harness/run_experiments.py \
  --benchmarks benchmarks/random_sat benchmarks/sudoku \
  --output results/results.csv \
  --solver-timeout 60
```

### 4. Running Parameter Sensitivity Analysis

To analyze the effect of the noise parameter on WalkSAT performance:

```bash
python3 harness/run_parameter_sensitivity.py
```

### 5. Generating Plots

Once experiments are complete, generate the visualizations for the report:

```bash
# General Performance Plots (Scalability, Heuristics, etc.)
python3 analysis/generate_plots.py --input results/results.csv

# Parameter Sensitivity Plot
python3 analysis/plot_walksat_noise.py --summary results/parameter_sensitivity.csv
```
*Plots will be saved in `results/plots/`.*

## Metrics Captured

The harness captures the following metrics for every run:
- **Status**: SAT, UNSAT, or TIMEOUT.
- **Time**: CPU time and Wall-clock time.
- **Memory**: Peak memory usage.
- **Internal Stats**: Decisions, Conflicts, Learned Clauses, Flips, Restarts.
- **Verification**: Automatically verifies if the model returned by the solver satisfies the formula.


