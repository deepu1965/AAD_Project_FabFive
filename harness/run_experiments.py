from __future__ import annotations
import argparse
import csv
import random
import signal
import sys
import time
import tracemalloc
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterable, List
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from solvers import cdcl, dpll_baseline, dpll_jw, probsat, walksat
from utils.cnf_parser import parse_dimacs
from harness.datasets import ensure_dataset

def collect_files(paths: Iterable[str]) -> List[Path]:
    files: List[Path] = []
    for raw in paths:
        target = Path(raw)
        if target.is_file() and target.suffix == ".cnf":
            files.append(target)
        elif target.is_dir():
            for path in sorted(target.rglob("*.cnf")):
                files.append(path)
    return files

def infer_problem_type(path: Path) -> str:
    parts = [part.lower() for part in path.parts]
    if "sudoku" in parts:
        return "sudoku"
    if "random_sat" in parts:
        return "random_3sat"
    return "unknown"

def clause_satisfied(clause: List[int], assignment: Dict[int, bool]) -> bool:
    for lit in clause:
        var = abs(lit)
        val = assignment.get(var)
        if val is None:
            continue
        if (lit > 0 and val) or (lit < 0 and not val):
            return True
    return False

def verify_assignment(clauses: List[List[int]], assignment: Dict[int, bool]) -> bool:
    if not assignment:
        return False
    return all(clause_satisfied(clause, assignment) for clause in clauses)

def build_runners(args: argparse.Namespace) -> Dict[str, object]:
    return {
        "dpll_baseline": lambda cnf: dpll_baseline.run_solver(cnf),
        "dpll_jw": lambda cnf: dpll_jw.run_solver(cnf),
        "cdcl": lambda cnf: cdcl.run_solver(cnf),
        "walksat": lambda cnf: walksat.run_solver(cnf, args.walksat_max_flips, args.walksat_noise, args.walksat_restarts),
        "probsat": lambda cnf: probsat.run_solver(cnf, args.probsat_max_flips, args.probsat_epsilon, args.probsat_restarts),
    }

@contextmanager
def solver_timeout(seconds: float):
    if seconds is None or seconds <= 0:
        yield
        return

    def handler(signum, frame):
        raise TimeoutError()

    previous = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmarks", nargs="+", required=True)
    parser.add_argument("--output", default="results/results.csv")
    parser.add_argument("--solvers", nargs="+", default=["dpll_baseline", "dpll_jw", "cdcl", "walksat", "probsat"])
    parser.add_argument("--walksat-max-flips", type=int, default=10000)
    parser.add_argument("--walksat-noise", type=float, default=0.5)
    parser.add_argument("--walksat-restarts", type=int, default=1)
    parser.add_argument("--probsat-max-flips", type=int, default=10000)
    parser.add_argument("--probsat-epsilon", type=float, default=0.5)
    parser.add_argument("--probsat-restarts", type=int, default=1)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--solver-timeout", type=float, default=60.0)
    parser.add_argument("--download-if-missing", action="store_true")
    parser.add_argument("--random3sat-url", type=str, default="")
    parser.add_argument("--sudoku-url", type=str, default="")
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    runners = build_runners(args)
    if args.download_if_missing:
        random_url = args.random3sat_url.strip() or None
        sudoku_url = args.sudoku_url.strip() or None
        for raw in args.benchmarks:
            lower = raw.lower()
            if "random_sat" in lower:
                ensure_dataset("random_sat", random_url)
            if "sudoku" in lower:
                ensure_dataset("sudoku", sudoku_url)
    selected = [name for name in args.solvers if name in runners]
    files = collect_files(args.benchmarks)
    results_dir = Path(args.output).parent
    results_dir.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "solver",
        "benchmark_file",
        "problem_type",
        "num_vars",
        "num_clauses",
        "status",
        "cpu_time",
        "elapsed_time",
        "wall_time",
        "peak_memory",
        "decisions",
        "unit_propagations",
        "pure_eliminations",
        "conflicts",
        "learned_clauses",
        "flips",
        "restarts",
        "verified",
    ]
    with Path(args.output).open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
    for cnf_path in files:
        meta = parse_dimacs(cnf_path)
        for solver_name in selected:
            runner = runners[solver_name]
            tracemalloc.start()
            start_wall = time.perf_counter()
            start_cpu = time.process_time()
            timed_out = False
            try:
                with solver_timeout(args.solver_timeout):
                    result = runner(Path(cnf_path))
            except TimeoutError:
                timed_out = True
                result = {}
            elapsed = time.perf_counter() - start_wall
            cpu_used = time.process_time() - start_cpu
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            status = result.get("status", "UNKNOWN") if not timed_out else "TIMEOUT"
            wall_time = result.get("wall_time", elapsed) if not timed_out else elapsed
            assignment = result.get("assignment") or {}
            verified = None
            if status == "SAT" and assignment:
                try:
                    verified = verify_assignment(meta.clauses, assignment)
                    if not verified:
                        status = "ERROR"
                except Exception:
                    verified = False
                    status = "ERROR"
            record = {
                "solver": solver_name,
                "benchmark_file": str(cnf_path),
                "problem_type": infer_problem_type(cnf_path),
                "num_vars": meta.num_vars,
                "num_clauses": meta.num_clauses,
                "status": status,
                "cpu_time": cpu_used,
                "elapsed_time": elapsed,
                "wall_time": wall_time,
                "peak_memory": peak,
                "decisions": result.get("decisions"),
                "unit_propagations": result.get("unit_propagations"),
                "pure_eliminations": result.get("pure_eliminations"),
                "conflicts": result.get("conflicts"),
                "learned_clauses": result.get("learned_clauses"),
                "flips": result.get("flips"),
                "restarts": result.get("restarts"),
                "verified": verified,
            }
            
            with Path(args.output).open("a", newline="", encoding="utf-8") as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writerow(record)

if __name__ == "__main__":
    main()
