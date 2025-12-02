from __future__ import annotations
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

def success_rate_vs_noise(summary_csv: Path, output_png: Path) -> None:
    df = pd.read_csv(summary_csv)
    grouped = df.groupby('noise')['status'].apply(lambda s: (s == 'SAT').mean())
    fig, ax = plt.subplots()
    ax.plot(grouped.index, grouped.values, marker='o')
    ax.set_xlabel('WalkSAT noise (p)')
    ax.set_ylabel('Success rate')
    ax.set_ylim(0, 1)
    fig.tight_layout()
    output_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_png)
    plt.close(fig)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--summary', required=True, help='Path to walksat_noise_summary.csv')
    parser.add_argument('--output', default='results/walksat_sweep/success_rate_vs_noise.png')
    args = parser.parse_args()
    success_rate_vs_noise(Path(args.summary), Path(args.output))

if __name__ == '__main__':
    main()
