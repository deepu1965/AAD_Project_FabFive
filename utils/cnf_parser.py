from dataclasses import dataclass
from pathlib import Path
from typing import List, Tuple


@dataclass
class CNFFormula:
    num_vars: int
    num_clauses: int
    clauses: List[List[int]]


def parse_dimacs(path: str | Path) -> CNFFormula:
    target = Path(path)
    clauses: List[List[int]] = []
    num_vars = 0
    num_clauses = 0
    with target.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line or line.startswith("c"):
                continue
            if line.startswith("p"):
                parts = line.split()
                if len(parts) >= 4:
                    num_vars = int(parts[2])
                    num_clauses = int(parts[3])
                continue
            literals = [int(value) for value in line.split() if value != "0"]
            if literals:
                clauses.append(literals)
    if not num_clauses:
        num_clauses = len(clauses)
    return CNFFormula(num_vars=num_vars, num_clauses=num_clauses, clauses=clauses)


def parse_from_string(data: str) -> CNFFormula:
    clauses: List[List[int]] = []
    num_vars = 0
    num_clauses = 0
    for raw in data.splitlines():
        line = raw.strip()
        if not line or line.startswith("c"):
            continue
        if line.startswith("p"):
            parts = line.split()
            if len(parts) >= 4:
                num_vars = int(parts[2])
                num_clauses = int(parts[3])
            continue
        literals = [int(value) for value in line.split() if value != "0"]
        if literals:
            clauses.append(literals)
    if not num_clauses:
        num_clauses = len(clauses)
    return CNFFormula(num_vars=num_vars, num_clauses=num_clauses, clauses=clauses)
