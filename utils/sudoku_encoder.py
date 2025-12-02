from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

DIGITS = range(1, 10)
SIZE = 9
BOX = 3


def var_index(row: int, col: int, value: int) -> int:
    return row * SIZE * SIZE + col * SIZE + value


def parse_puzzle(path: Path) -> List[List[int]]:
    rows: List[List[int]] = []
    for line in path.read_text().splitlines():
        text = line.strip()
        if not text:
            continue
        if len(text) != SIZE:
            raise ValueError("invalid row length")
        rows.append([int(ch) for ch in text])
    if len(rows) != SIZE:
        raise ValueError("invalid puzzle height")
    return rows


def cell_clauses() -> List[List[int]]:
    clauses: List[List[int]] = []
    for r in range(SIZE):
        for c in range(SIZE):
            clauses.append([var_index(r, c, v) for v in DIGITS])
            for v1 in DIGITS:
                for v2 in DIGITS:
                    if v1 < v2:
                        clauses.append([-var_index(r, c, v1), -var_index(r, c, v2)])
    return clauses


def row_clauses() -> List[List[int]]:
    clauses: List[List[int]] = []
    for r in range(SIZE):
        for v in DIGITS:
            clauses.append([var_index(r, c, v) for c in range(SIZE)])
            for c1 in range(SIZE):
                for c2 in range(c1 + 1, SIZE):
                    clauses.append([-var_index(r, c1, v), -var_index(r, c2, v)])
    return clauses


def column_clauses() -> List[List[int]]:
    clauses: List[List[int]] = []
    for c in range(SIZE):
        for v in DIGITS:
            clauses.append([var_index(r, c, v) for r in range(SIZE)])
            for r1 in range(SIZE):
                for r2 in range(r1 + 1, SIZE):
                    clauses.append([-var_index(r1, c, v), -var_index(r2, c, v)])
    return clauses


def box_clauses() -> List[List[int]]:
    clauses: List[List[int]] = []
    for br in range(0, SIZE, BOX):
        for bc in range(0, SIZE, BOX):
            cells = [(br + dr, bc + dc) for dr in range(BOX) for dc in range(BOX)]
            for v in DIGITS:
                clauses.append([var_index(r, c, v) for r, c in cells])
                for i in range(len(cells)):
                    for j in range(i + 1, len(cells)):
                        r1, c1 = cells[i]
                        r2, c2 = cells[j]
                        clauses.append([-var_index(r1, c1, v), -var_index(r2, c2, v)])
    return clauses


def clue_clauses(puzzle: List[List[int]]) -> List[List[int]]:
    clauses: List[List[int]] = []
    for r in range(SIZE):
        for c in range(SIZE):
            value = puzzle[r][c]
            if value:
                clauses.append([var_index(r, c, value)])
    return clauses


def encode(puzzle: List[List[int]]) -> List[List[int]]:
    clauses = []
    clauses.extend(cell_clauses())
    clauses.extend(row_clauses())
    clauses.extend(column_clauses())
    clauses.extend(box_clauses())
    clauses.extend(clue_clauses(puzzle))
    return clauses


def write_dimacs(path: Path, clauses: List[List[int]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        total_vars = SIZE * SIZE * SIZE
        handle.write(f"p cnf {total_vars} {len(clauses)}\n")
        for clause in clauses:
            line = " ".join(str(lit) for lit in clause) + " 0\n"
            handle.write(line)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    puzzle = parse_puzzle(Path(args.input))
    clauses = encode(puzzle)
    write_dimacs(Path(args.output), clauses)


if __name__ == "__main__":
    main()
