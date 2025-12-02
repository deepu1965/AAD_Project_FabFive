from __future__ import annotations
import os
import shutil
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional
ROOT = Path(__file__).resolve().parents[1]
BENCH_DIR = ROOT / "benchmarks"

def _download_zip(url: str, dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        tmp_zip = Path(td) / "dataset.zip"
        urllib.request.urlretrieve(url, tmp_zip)
        with zipfile.ZipFile(tmp_zip, "r") as zf:
            zf.extractall(dest_dir)

def ensure_dataset(dataset: str, url: Optional[str]) -> None:
    target = BENCH_DIR / dataset
    if target.exists() and any(target.rglob("*.cnf")):
        return
    if not url:
        return

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        _download_zip(url, tmp_dir)
        if not target.exists():
            target.mkdir(parents=True, exist_ok=True)
        for item in tmp_dir.iterdir():
            if item.is_dir():
                for sub in item.iterdir():
                    dest = target / sub.name
                    if dest.exists():
                        if dest.is_dir():
                            shutil.rmtree(dest)
                        else:
                            dest.unlink()
                    shutil.move(str(sub), str(dest))
            else:
                dest = target / item.name
                if dest.exists():
                    dest.unlink()
                shutil.move(str(item), str(dest))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
