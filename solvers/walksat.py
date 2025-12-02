from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from utils.cnf_parser import parse_dimacs


Clause = List[int]
Assignment = Dict[int, bool]


@dataclass
class SolverStats:
    flips: int = 0
    restarts: int = 0


def initialize_assignment(num_vars: int) -> Assignment:
    return {var: random.choice([True, False]) for var in range(1, num_vars + 1)}


def clause_value(clause: Clause, assignment: Assignment) -> bool:
    for lit in clause:
        var = abs(lit)
        val = assignment.get(var)
        if val is None:
            continue
        if (lit > 0 and val) or (lit < 0 and not val):
            return True
    return False


def unsatisfied_clauses(clauses: Sequence[Clause], assignment: Assignment) -> List[Clause]:
    return [clause for clause in clauses if not clause_value(clause, assignment)]


def flip_variable(assignment: Assignment, var: int) -> None:
    assignment[var] = not assignment[var]


def walk_sat(clauses: Sequence[Clause], num_vars: int, max_flips: int, noise: float, stats: SolverStats) -> Assignment | None:
    assignment = initialize_assignment(num_vars)
    for step in range(max_flips):
        unsatisfied = unsatisfied_clauses(clauses, assignment)
        if not unsatisfied:
            return assignment
        clause = random.choice(unsatisfied)
        stats.flips += 1
        if random.random() < noise:
            var = abs(random.choice(clause))
            flip_variable(assignment, var)
            continue
        best_var = None
        best_score = float("inf")
        for lit in clause:
            var = abs(lit)
            flip_variable(assignment, var)
            broken = len(unsatisfied_clauses(clauses, assignment))
            flip_variable(assignment, var)
            if broken < best_score:
                best_score = broken
                best_var = var
        if best_var is None:
            best_var = abs(random.choice(clause))
        flip_variable(assignment, best_var)
    return None


def run_solver(path: Path, max_flips: int, noise: float, restarts: int) -> Dict[str, object]:
    formula = parse_dimacs(path)
    stats = SolverStats()
    best_assignment = None
    for attempt in range(restarts):
        assignment = walk_sat(formula.clauses, formula.num_vars, max_flips, noise, stats)
        if assignment is not None:
            best_assignment = assignment
            break
        stats.restarts += 1
    status = "SAT" if best_assignment else "UNKNOWN"
    return {
        "solver": "walksat",
        "status": status,
        "flips": stats.flips,
        "restarts": stats.restarts,
        "num_vars": formula.num_vars,
        "num_clauses": formula.num_clauses,
        "assignment": best_assignment or {},
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnf", required=True)
    parser.add_argument("--max-flips", type=int, default=10000)
    parser.add_argument("--noise", type=float, default=0.5)
    parser.add_argument("--restarts", type=int, default=1)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    start = time.perf_counter()
    result = run_solver(Path(args.cnf), args.max_flips, args.noise, args.restarts)
    result["wall_time"] = time.perf_counter() - start
    print(json.dumps(result))


if __name__ == "__main__":
    main()
