from __future__ import annotations

import argparse
import json
import math
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


def break_score(clauses: Sequence[Clause], assignment: Assignment, var: int) -> int:
    flip_variable(assignment, var)
    score = sum(1 for clause in clauses if not clause_value(clause, assignment))
    flip_variable(assignment, var)
    return score


def select_variable_probabilistic(clause: Clause, clauses: Sequence[Clause], assignment: Assignment, epsilon: float) -> int:
    scores = []
    total = 0.0
    for lit in clause:
        var = abs(lit)
        score = math.pow(epsilon, break_score(clauses, assignment, var))
        scores.append((var, score))
        total += score
    r = random.random() * total
    accum = 0.0
    for var, score in scores:
        accum += score
        if accum >= r:
            return var
    return scores[-1][0]


def prob_sat(clauses: Sequence[Clause], num_vars: int, max_flips: int, epsilon: float, stats: SolverStats) -> Assignment | None:
    assignment = initialize_assignment(num_vars)
    for step in range(max_flips):
        unsatisfied = unsatisfied_clauses(clauses, assignment)
        if not unsatisfied:
            return assignment
        clause = random.choice(unsatisfied)
        var = select_variable_probabilistic(clause, clauses, assignment, epsilon)
        flip_variable(assignment, var)
        stats.flips += 1
    return None


def run_solver(path: Path, max_flips: int, epsilon: float, restarts: int) -> Dict[str, object]:
    formula = parse_dimacs(path)
    stats = SolverStats()
    best_assignment = None
    for attempt in range(restarts):
        assignment = prob_sat(formula.clauses, formula.num_vars, max_flips, epsilon, stats)
        if assignment is not None:
            best_assignment = assignment
            break
        stats.restarts += 1
    status = "SAT" if best_assignment else "UNKNOWN"
    return {
        "solver": "probsat",
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
    parser.add_argument("--epsilon", type=float, default=0.5)
    parser.add_argument("--restarts", type=int, default=1)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    if args.seed is not None:
        random.seed(args.seed)
    start = time.perf_counter()
    result = run_solver(Path(args.cnf), args.max_flips, args.epsilon, args.restarts)
    result["wall_time"] = time.perf_counter() - start
    print(json.dumps(result))


if __name__ == "__main__":
    main()
