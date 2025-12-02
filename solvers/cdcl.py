from __future__ import annotations
import argparse
import heapq
import json
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))
from utils.cnf_parser import parse_dimacs
Clause = List[int]
Formula = List[Clause]
Assignment = Dict[int, bool]
WatchList = Dict[int, List[int]]

@dataclass(order=True)
class ScoredVar:
    score: float
    var: int = field(compare=False)

@dataclass
class SolverStats:
    decisions: int = 0
    conflicts: int = 0
    learned_clauses: int = 0
    restarts: int = 0
# CDCL (Conflict-Driven Clause Learning)
# Decision
# Unit Propagation
# 1 UIP Conflict-> implication graph-> learned clause
# Non-Chronological Backtracking
# VSIDS (Variable State Independent Decaying Sum)

class PriorityQueue:
    def __init__(self) -> None:
        self.heap: List[Tuple[float, int]] = []
        self.entries: Dict[int, float] = {}

    def push(self, var: int, score: float) -> None:
        self.entries[var] = score
        heapq.heappush(self.heap, (-score, var))

    def pop(self, assignment: Assignment) -> Optional[int]:
        while self.heap:
            score, var = heapq.heappop(self.heap)
            if var in assignment:
                continue
            current = self.entries.get(var)
            if current is None or -score != current:
                continue
            return var
        return None

    def update(self, var: int, score: float) -> None:
        self.push(var, score)

@dataclass
class SolverState:
    formula: Formula
    assignment: Assignment
    decision_levels: Dict[int, int]
    reason: Dict[int, List[int]]
    level_literals: List[int]
    watches: WatchList
    watch_map: Dict[int, Tuple[int, int]]
    vsids: Dict[int, float]
    queue: PriorityQueue
    phase: Dict[int, bool]
    decision_level: int = 0
    decay: float = 0.95

def initialize_state(formula: Formula) -> SolverState:
    watches: WatchList = {}
    watch_map: Dict[int, Tuple[int, int]] = {}
    for idx, clause in enumerate(formula):
        if len(clause) < 2:
            watch_map[idx] = (clause[0], clause[0])
            watches.setdefault(clause[0], [])
            if idx not in watches[clause[0]]:
                watches[clause[0]].append(idx)
        else:
            watch_map[idx] = (clause[0], clause[1])
            for lit in clause[:2]:
                watches.setdefault(lit, [])
                if idx not in watches[lit]:
                    watches[lit].append(idx)
    vsids: Dict[int, float] = {}
    queue = PriorityQueue()
    for clause in formula:
        for lit in clause:
            var = abs(lit)
            vsids[var] = vsids.get(var, 0.0) + 1.0
    for var, score in vsids.items():
        queue.push(var, score)
    phase: Dict[int, bool] = {var: True for var in vsids.keys()}
    return SolverState(formula, {}, {}, {}, [], watches, watch_map, vsids, queue, phase)

def value_of(literal: int, assignment: Assignment) -> Optional[bool]:
    var = abs(literal)
    val = assignment.get(var)
    if val is None:
        return None
    return val if literal > 0 else not val

def add_watch(state: SolverState, literal: int, clause_idx: int) -> None:
    state.watches.setdefault(literal, [])
    if clause_idx not in state.watches[literal]:
        state.watches[literal].append(clause_idx)

def remove_watch(state: SolverState, literal: int, clause_idx: int) -> None:
    watchers = state.watches.get(literal)
    if not watchers:
        return
    try:
        watchers.remove(clause_idx)
    except ValueError:
        return

def update_watch(state: SolverState, clause_idx: int, old_literal: int, new_literal: int) -> None:
    remove_watch(state, old_literal, clause_idx)
    add_watch(state, new_literal, clause_idx)

def propagate(state: SolverState, stats: SolverStats) -> Optional[List[int]]:
    queue: List[int] = state.level_literals[:]
    while queue:
        literal = queue.pop()
        opposite = -literal
        watchers = list(state.watches.get(opposite, []))
        for clause_idx in watchers:
            clause = state.formula[clause_idx]
            w1, w2 = state.watch_map[clause_idx]
            other = w2 if w1 == opposite else w1
            if value_of(other, state.assignment) is True:
                continue
            found = False
            for candidate in clause:
                if candidate in (w1, w2):
                    continue
                val = value_of(candidate, state.assignment)
                if val is False:
                    continue
                if w1 == opposite:
                    state.watch_map[clause_idx] = (candidate, w2)
                else:
                    state.watch_map[clause_idx] = (w1, candidate)
                update_watch(state, clause_idx, opposite, candidate)
                found = True
                break
            if found:
                continue
            value = value_of(other, state.assignment)
            if value is False:
                stats.conflicts += 1
                return clause
            var = abs(other)
            state.assignment[var] = other > 0
            state.phase[var] = other > 0
            state.decision_levels[var] = state.decision_level
            state.reason[var] = clause
            state.level_literals.append(other)
            queue.append(other)
    return None

def analyze_conflict(state: SolverState, conflict: List[int]) -> Tuple[List[int], int]:
    learned = conflict[:]
    def count_curr_level(clause: List[int]) -> int:
        return sum(1 for lit in clause if state.decision_levels.get(abs(lit), -1) == state.decision_level)
    def resolve(clause: List[int], pivot_var: int) -> List[int]:
        reason = state.reason.get(pivot_var)
        if not reason:
            return clause[:]
        resolvent: List[int] = []
        present = set()
        for lit in clause:
            if abs(lit) == pivot_var:
                continue
            if -lit in present:
                continue
            if lit not in present:
                present.add(lit)
                resolvent.append(lit)
        for lit in reason:
            if abs(lit) == pivot_var:
                continue
            if -lit in present:
                try:
                    resolvent.remove(-lit)
                    present.remove(-lit)
                except ValueError:
                    pass
                continue
            if lit not in present:
                present.add(lit)
                resolvent.append(lit)
        return resolvent

    while count_curr_level(learned) > 1:
        pivot_var: Optional[int] = None
        for assigned_lit in reversed(state.level_literals):
            v = abs(assigned_lit)
            if any(abs(l) == v for l in learned) and state.decision_levels.get(v, -1) == state.decision_level:
                pivot_var = v
                break
        if pivot_var is None:
            break
        learned = resolve(learned, pivot_var)

    backjump = 0
    for lit in learned:
        lvl = state.decision_levels.get(abs(lit), 0)
        if lvl != state.decision_level and lvl > backjump:
            backjump = lvl
    return learned, backjump

def backtrack(state: SolverState, level: int) -> None:
    to_remove = [var for var, dl in state.decision_levels.items() if dl > level]
    for var in to_remove:
        state.assignment.pop(var, None)
        state.decision_levels.pop(var, None)
        state.reason.pop(var, None)
    state.decision_level = level
    state.level_literals = [lit for lit in state.level_literals if state.decision_levels.get(abs(lit), -1) == level]

def learn_clause(state: SolverState, clause: List[int], stats: SolverStats) -> None:
    state.formula.append(clause)
    idx = len(state.formula) - 1
    if len(clause) == 1:
        state.watch_map[idx] = (clause[0], clause[0])
        add_watch(state, clause[0], idx)
    else:
        state.watch_map[idx] = (clause[0], clause[1])
        for lit in clause[:2]:
            add_watch(state, lit, idx)
    stats.learned_clauses += 1
    for lit in clause:
        var = abs(lit)
        state.vsids[var] = state.vsids.get(var, 0.0) + 1.0
        state.queue.update(var, state.vsids[var])

def decay_scores(state: SolverState) -> None:
    for var in state.vsids:
        state.vsids[var] *= state.decay
        state.queue.update(var, state.vsids[var])

def select_branch_literal(state: SolverState) -> Optional[int]:
    var = state.queue.pop(state.assignment)
    if var is None:
        return None
    sign = state.phase.get(var, True)
    return var if sign else -var
def cdcl(state: SolverState, stats: SolverStats) -> Tuple[bool, Assignment]:
    restart_limit = 100
    restart_multiplier = 1.5
    conflicts_since_restart = 0

    while True:
        conflict = propagate(state, stats)
        if conflict:
            stats.conflicts += 1
            conflicts_since_restart += 1
            if state.decision_level == 0:
                return False, state.assignment
            clause, backjump = analyze_conflict(state, conflict)
            learn_clause(state, clause, stats)
            asserting = None
            for lit in clause:
                if state.decision_levels.get(abs(lit), -1) == state.decision_level:
                    asserting = lit
                    break
            backtrack(state, backjump)
            decay_scores(state)
            if asserting is not None:
                var = abs(asserting)
                state.assignment[var] = asserting > 0
                state.decision_levels[var] = state.decision_level
                state.reason[var] = clause
                state.phase[var] = asserting > 0
                state.level_literals.append(asserting)
            
            if conflicts_since_restart >= restart_limit:
                stats.restarts += 1
                backtrack(state, 0)
                conflicts_since_restart = 0
                restart_limit = int(restart_limit * restart_multiplier)
            
            continue
        literal = select_branch_literal(state)
        if literal is None:
            return True, state.assignment
        state.decision_level += 1
        stats.decisions += 1
        var = abs(literal)
        state.assignment[var] = literal > 0
        state.phase[var] = literal > 0
        state.decision_levels[var] = state.decision_level
        state.reason[var] = []
        state.level_literals.append(literal)

def run_solver(path: Path) -> Dict[str, object]:
    formula = parse_dimacs(path).clauses
    state = initialize_state([clause[:] for clause in formula])
    stats = SolverStats()
    
    for clause in state.formula:
        if len(clause) == 1:
            lit = clause[0]
            var = abs(lit)
            val = state.assignment.get(var)
            if val is not None:
                if val != (lit > 0):
                    return {
                        "solver": "cdcl",
                        "status": "UNSAT",
                        "decisions": 0,
                        "conflicts": 0,
                        "learned_clauses": 0,
                        "restarts": 0,
                        "assignment": {},
                        "num_clauses": len(state.formula),
                    }
            else:
                state.assignment[var] = lit > 0
                state.decision_levels[var] = 0
                state.reason[var] = []
                state.phase[var] = lit > 0
                state.level_literals.append(lit)
    
    if propagate(state, stats) is not None:
         return {
            "solver": "cdcl",
            "status": "UNSAT",
            "decisions": 0,
            "conflicts": 0,
            "learned_clauses": 0,
            "restarts": 0,
            "assignment": {},
            "num_clauses": len(state.formula),
        }

    sat, assignment = cdcl(state, stats)
    return {
        "solver": "cdcl",
        "status": "SAT" if sat else "UNSAT",
        "decisions": stats.decisions,
        "conflicts": stats.conflicts,
        "learned_clauses": stats.learned_clauses,
        "restarts": stats.restarts,
        "assignment": assignment if sat else {},
        "num_clauses": len(state.formula),
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

# o(2^n) in the worst case (since SAT is NP-Complete)