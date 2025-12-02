import json
import random
import copy
import sys
from pathlib import Path
from typing import List, Dict

# Add project root to sys.path to allow importing from utils
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from utils.sudoku_encoder import encode, write_dimacs

DIGITS = range(1, 10)
SIZE = 9

def parse_grid_from_string(grid_str: str) -> List[List[int]]:
    if isinstance(grid_str, list):
        return [[int(c) for c in row] for row in grid_str]
    
    clean_str = grid_str.replace('\n', '').replace(' ', '')
    if len(clean_str) != 81:
        raise ValueError("Invalid grid string length")
    
    grid = []
    for i in range(9):
        row = [int(c) for c in clean_str[i*9 : (i+1)*9]]
        grid.append(row)
    return grid

def grid_to_string(grid: List[List[int]]) -> List[str]:
    return ["".join(map(str, row)) for row in grid]

def permute_sudoku(grid: List[List[int]]) -> List[List[int]]:
    new_grid = copy.deepcopy(grid)
    mapping = list(range(1, 10))
    random.shuffle(mapping)
    map_dict = {i+1: m for i, m in enumerate(mapping)}
    map_dict[0] = 0
    
    for r in range(9):
        for c in range(9):
            new_grid[r][c] = map_dict[new_grid[r][c]]
            
    for band in range(3):
        start = band * 3
        rows = new_grid[start : start+3]
        random.shuffle(rows)
        new_grid[start : start+3] = rows
        
    new_grid = [list(x) for x in zip(*new_grid)] 
    for stack in range(3):
        start = stack * 3
        rows = new_grid[start : start+3]
        random.shuffle(rows)
        new_grid[start : start+3] = rows
    new_grid = [list(x) for x in zip(*new_grid)]
    
    return new_grid

def make_unsolvable(grid: List[List[int]]) -> List[List[int]]:
    new_grid = copy.deepcopy(grid)
    filled = []
    for r in range(9):
        for c in range(9):
            if new_grid[r][c] != 0:
                filled.append((r, c))
    if not filled:
        return new_grid
    r, c = random.choice(filled)
    val = new_grid[r][c]
    for c2 in range(9):
        if c2 != c and new_grid[r][c2] != 0:
            new_grid[r][c] = new_grid[r][c2]
            break
    return new_grid

def generate_dataset(seed_path: Path, output_json: Path, count: int = 25):
    with open(seed_path, 'r') as f:
        lines = [l.strip() for l in f if l.strip()]
    seed_grid = parse_grid_from_string(lines)
    puzzles = []
    for i in range(count - 5):
        p = permute_sudoku(seed_grid)
        puzzles.append({
            "id": f"sudoku_sat_{i+1:02d}",
            "type": "satisfiable",
            "grid": grid_to_string(p)
        })
    for i in range(5):
        p = permute_sudoku(seed_grid)
        p = make_unsolvable(p)
        puzzles.append({
            "id": f"sudoku_unsat_{i+1:02d}",
            "type": "unsolvable",
            "grid": grid_to_string(p)
        })
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, 'w') as f:
        json.dump(puzzles, f, indent=2)

def export_to_cnf(json_path: Path, output_dir: Path):
    with open(json_path, 'r') as f:
        puzzles = json.load(f)
    output_dir.mkdir(parents=True, exist_ok=True)
    for p in puzzles:
        grid = parse_grid_from_string(p['grid'])
        clauses = encode(grid)        
        filename = output_dir / f"{p['id']}.cnf"
        write_dimacs(filename, clauses)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", default="puzzles/sudoku_easy.csv")
    parser.add_argument("--json-out", default="puzzles/sudoku_puzzles.json")
    parser.add_argument("--cnf-dir", default="benchmarks/sudoku")
    args = parser.parse_args()
    generate_dataset(Path(args.seed), Path(args.json_out))
    export_to_cnf(Path(args.json_out), Path(args.cnf_dir))
