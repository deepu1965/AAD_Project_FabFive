from __future__ import annotations
import argparse
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd

def ensure_output(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

def line_plot(df: pd.DataFrame, metric: str, output: Path, ylabel: str) -> None:
    fig, ax = plt.subplots()
    for solver, group in df.groupby("solver"):
        series = group.groupby("num_vars")[metric].mean().sort_index()
        ax.plot(series.index, series.values, marker="o", label=solver)
    ax.set_xlabel("num_vars")
    ax.set_ylabel(ylabel)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)

def stacked_plot(df: pd.DataFrame, output: Path) -> None:
    fig, ax = plt.subplots()
    pivot = df.pivot_table(values="cpu_time", index="num_vars", columns="problem_type", aggfunc="mean")
    pivot.plot(kind="bar", ax=ax)
    ax.set_xlabel("num_vars")
    ax.set_ylabel("cpu_time")
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)

def metric_bar(df: pd.DataFrame, metric: str, output: Path) -> None:
    fig, ax = plt.subplots()
    agg = df.groupby("solver")[metric].mean().sort_values(ascending=False)
    agg.plot(kind="bar", ax=ax)
    ax.set_ylabel(metric)
    fig.tight_layout()
    fig.savefig(output)
    plt.close(fig)

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", default="results/plots")
    args = parser.parse_args()
    df = pd.read_csv(args.input)
    output_dir = Path(args.output)
    ensure_output(output_dir)
    line_plot(df, "cpu_time", output_dir / "cpu_time_vs_vars.png", "cpu_time")
    line_plot(df, "peak_memory", output_dir / "peak_memory_vs_vars.png", "peak_memory")
    stacked_plot(df, output_dir / "cpu_time_by_problem_type.png")
    metric_bar(df[df["problem_type"] == "random_3sat"], "flips", output_dir / "random_flips.png")
    solvers_decisions = ["dpll_baseline", "dpll_jw", "cdcl"]
    df_decisions = df[df["solver"].isin(solvers_decisions)]
    if not df_decisions.empty:
        metric_bar(df_decisions, "decisions", output_dir / "decisions_comparison.png")

    solvers_flips = ["walksat", "probsat"]
    df_flips = df[df["solver"].isin(solvers_flips)]
    if not df_flips.empty:
        metric_bar(df_flips, "flips", output_dir / "flips_comparison.png")

    df_cdcl = df[df["solver"] == "cdcl"]
    if not df_cdcl.empty:
        line_plot(df_cdcl, "conflicts", output_dir / "cdcl_conflicts.png", "conflicts")
        line_plot(df_cdcl, "learned_clauses", output_dir / "cdcl_learned_clauses.png", "learned_clauses")

if __name__ == "__main__":
    main()
