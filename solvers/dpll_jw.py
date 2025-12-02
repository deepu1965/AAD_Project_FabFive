from __future__ import annotations
import argparse
import json
import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from utils.cnf_parser import parse_dimacs
Clause = List[int]
Formula = List[Clause]
Assignment = Dict[int, bool]

@dataclass
class SolverStats:
    decisions: int = 0
    unit_propagations: int = 0
    pure_eliminations: int = 0

def assign_literal(clauses: Formula, assignment: Assignment, literal: int) -> Tuple[Formula, bool]:
    var = abs(literal)
    value = literal > 0
    existing = assignment.get(var)
    if existing is not None and existing != value:
        return clauses, True
    assignment[var] = value
    updated: Formula = []
    for clause in clauses:
        if literal in clause:
            continue
        if -literal in clause:
            reduced = [lit for lit in clause if lit != -literal]
            if not reduced:
                return clauses, True
            updated.append(reduced)
        else:
            updated.append(clause)
    return updated, False

def unit_propagate(clauses: Formula, assignment: Assignment, stats: SolverStats) -> Tuple[Formula, bool]:
    current = clauses
    while True:
        unit_literal = None
        for clause in current:
            satisfied = False
            undecided = []
            for lit in clause:
                var = abs(lit)
                val = assignment.get(var)
                if val is None:
                    undecided.append(lit)
                elif (lit > 0 and val) or (lit < 0 and not val):
                    satisfied = True
                    break
            if satisfied:
                continue
            if not undecided:
                return current, True
            if len(undecided) == 1:
                unit_literal = undecided[0]
                break
        if unit_literal is None:
            return current, False
        stats.unit_propagations += 1
        current, conflict = assign_literal(current, assignment, unit_literal)
        if conflict:
            return current, True

def pure_literal_elimination(clauses: Formula, assignment: Assignment, stats: SolverStats) -> Tuple[Formula, bool]:
    literal_counts: Dict[int, int] = {}
    for clause in clauses:
        clause_satisfied = False
        for lit in clause:
            var = abs(lit)
            val = assignment.get(var)
            if val is None:
                literal_counts[lit] = literal_counts.get(lit, 0) + 1
            elif (lit > 0 and val) or (lit < 0 and not val):
                clause_satisfied = True
                break
        if clause_satisfied:
            continue
    pure_literals = [lit for lit in literal_counts if -lit not in literal_counts]
    if not pure_literals:
        return clauses, False
    current = clauses
    for lit in pure_literals:
        stats.pure_eliminations += 1
        current, conflict = assign_literal(current, assignment, lit)
        if conflict:
            return current, True
    return current, False

def pick_literal(clauses: Formula, assignment: Assignment) -> int:
    scores: Dict[int, float] = {}
    for clause in clauses:
        weight = math.pow(2.0, -len(clause)) if clause else 0.0
        satisfied = False
        for lit in clause:
            var = abs(lit)
            val = assignment.get(var)
            if val is None:
                scores[lit] = scores.get(lit, 0.0) + weight
            elif (lit > 0 and val) or (lit < 0 and not val):
                satisfied = True
                break
        if satisfied:
            continue
    if not scores:
        for clause in clauses:
            for lit in clause:
                if abs(lit) not in assignment:
                    return lit
    return max(scores.items(), key=lambda item: item[1])[0]

def dpll(clauses: Formula, assignment: Assignment, stats: SolverStats) -> Tuple[bool, Assignment]:
    current, conflict = unit_propagate(clauses, assignment, stats)
    if conflict:
        return False, assignment
    current, conflict = pure_literal_elimination(current, assignment, stats)
    if conflict:
        return False, assignment
    if not current:
        return True, assignment
    literal = pick_literal(current, assignment)
    var = abs(literal)
    for value in (True, False):
        stats.decisions += 1
        trial_assignment = assignment.copy()
        trial_literal = var if value else -var
        new_clauses, branch_conflict = assign_literal(current, trial_assignment, trial_literal)
        if branch_conflict:
            continue
        result, final_assignment = dpll(new_clauses, trial_assignment, stats)
        if result:
            return True, final_assignment
    return False, assignment

def run_solver(path: Path) -> Dict[str, object]:
    formula = parse_dimacs(path)
    stats = SolverStats()
    sat, assignment = dpll([clause[:] for clause in formula.clauses], {}, stats)
    return {
        "solver": "dpll_jw",
        "status": "SAT" if sat else "UNSAT",
        "decisions": stats.decisions,
        "unit_propagations": stats.unit_propagations,
        "pure_eliminations": stats.pure_eliminations,
        "assignment": assignment if sat else {},
        "num_vars": formula.num_vars,
        "num_clauses": formula.num_clauses,
    }
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cnf", required=True)
    args = parser.parse_args()
    start = time.perf_counter()
    result = run_solver(Path(args.cnf))
    result["wall_time"] = time.perf_counter() - start
    print(json.dumps(result))

if __name__ == "__main__":
    main()
