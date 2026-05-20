"""
Aggregate per-run evaluation CSV files in results/metrics/ into a single summary table.

Each per-run CSV (produced by evaluate_mesh.py) contains one row of metrics.
Their file names encode the experimental setting, e.g.:

    synthetic_01_100000_sample_points_f0.10_v0.10.csv
    ^^^^^^^^^^^^                       ^^^^ ^^^^
       tree id     sampled point count   F   voxel
                                       thr  size

This script:
  1. Parses the file names to extract tree id, sampled points, F-threshold,
     and voxel size.
  2. Concatenates all per-run rows into a single full summary table.
  3. Extracts a "canonical" view (configurable defaults: 100k samples,
     F-threshold 0.10 m, voxel 0.10 m) into a compact table suitable for
     inclusion in the report.
  4. Prints a Markdown table to stdout (handy to paste into the README).
  5. Saves both the full and canonical tables as CSV.

Usage (run from the repo root):
    python scripts/aggregate_results.py
    python scripts/aggregate_results.py --metrics-dir results/metrics --out-dir results
    python scripts/aggregate_results.py --canonical-points 100000 --canonical-f 0.10
"""

import argparse
import re
from pathlib import Path

import pandas as pd


FILENAME_RE = re.compile(
    r"^(?P<tree>.+?)_(?P<points>\d+)_sample_points_f(?P<f>[\d.]+)_v(?P<v>[\d.]+)\.csv$"
)


def parse_filename(name: str) -> dict | None:
    match = FILENAME_RE.match(name)
    if not match:
        return None
    return {
        "tree": match.group("tree"),
        "sampled_points": int(match.group("points")),
        "f_threshold": float(match.group("f")),
        "voxel_size": float(match.group("v")),
    }


def collect_results(metrics_dir: Path) -> pd.DataFrame:
    if not metrics_dir.exists():
        raise FileNotFoundError(f"Metrics directory does not exist: {metrics_dir}")

    csv_paths = sorted(metrics_dir.glob("*.csv"))
    if not csv_paths:
        raise FileNotFoundError(f"No CSV files found in: {metrics_dir}")

    rows = []
    skipped = []
    for csv_path in csv_paths:
        meta = parse_filename(csv_path.name)
        if meta is None:
            skipped.append(csv_path.name)
            continue

        df = pd.read_csv(csv_path)
        if df.empty:
            skipped.append(csv_path.name)
            continue

        # Each per-run CSV has exactly one row of metrics
        row = df.iloc[0].to_dict()
        # Override/add metadata from the filename so we always have these columns even if the per-run CSV is missing them
        row["tree"] = meta["tree"]
        row["sampled_points"] = meta["sampled_points"]
        row["f_threshold"] = meta["f_threshold"]
        row["voxel_size"] = meta["voxel_size"]
        row["source_csv"] = csv_path.name
        rows.append(row)

    if skipped:
        print(f"Skipped {len(skipped)} file(s) that did not match the expected pattern:")
        for name in skipped:
            print(f"  - {name}")

    combined = pd.DataFrame(rows)

    # Stable, readable column order
    leading = [
        "tree",
        "sampled_points",
        "f_threshold",
        "voxel_size",
        "chamfer_distance",
        "hausdorff_distance",
        "precision",
        "recall",
        "f_score",
        "voxel_iou",
    ]
    leading = [c for c in leading if c in combined.columns]
    remaining = [c for c in combined.columns if c not in leading]
    combined = combined[leading + remaining]

    return combined.sort_values(
        ["tree", "sampled_points", "f_threshold"], kind="stable"
    ).reset_index(drop=True)


# Filter the full table down to a single experimental setting per tree
def canonical_view(
    full: pd.DataFrame, sampled_points: int, f_threshold: float
) -> pd.DataFrame:
    canonical = full[
        (full["sampled_points"] == sampled_points)
        & (full["f_threshold"].round(4) == round(f_threshold, 4))
    ].copy()

    columns = [
        "tree",
        "chamfer_distance",
        "hausdorff_distance",
        "precision",
        "recall",
        "f_score",
        "voxel_iou",
    ]
    columns = [c for c in columns if c in canonical.columns]
    return canonical[columns].reset_index(drop=True)

# Render a DataFrame as a GitHub-flavoured Markdown table
def dataframe_to_markdown(df: pd.DataFrame, float_format: str = "{:.4f}") -> str:
    headers = list(df.columns)

    def render_cell(value):
        if isinstance(value, float):
            return float_format.format(value)
        return str(value)

    lines = []
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("|" + "|".join(["---"] * len(headers)) + "|")
    for _, row in df.iterrows():
        lines.append("| " + " | ".join(render_cell(row[h]) for h in headers) + " |")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Aggregate per-run evaluation CSVs into a single summary table."
        )
    )
    parser.add_argument(
        "--metrics-dir",
        default="results/metrics",
        help="Directory containing per-run evaluation CSV files.",
    )
    parser.add_argument(
        "--out-dir",
        default="results",
        help="Directory to write aggregated outputs to.",
    )
    parser.add_argument(
        "--canonical-points",
        type=int,
        default=100000,
        help="sampled_points value used for the canonical (report-ready) view.",
    )
    parser.add_argument(
        "--canonical-f",
        type=float,
        default=0.10,
        help="F-threshold used for the canonical view (in model units).",
    )
    parser.add_argument(
        "--write-markdown",
        action="store_true",
        help="Also write the canonical table as a Markdown snippet.",
    )
    args = parser.parse_args()

    metrics_dir = Path(args.metrics_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    full = collect_results(metrics_dir)
    print(f"Loaded {len(full)} run(s) from {metrics_dir}.")

    full_csv = out_dir / "summary_full.csv"
    full.to_csv(full_csv, index=False)
    print(f"Wrote full summary table -> {full_csv}")

    canonical = canonical_view(
        full,
        sampled_points=args.canonical_points,
        f_threshold=args.canonical_f,
    )

    if canonical.empty:
        print(
            "\nWARNING: canonical view is empty. "
            f"No rows match sampled_points={args.canonical_points} "
            f"and f_threshold={args.canonical_f}."
        )
        return

    canonical_csv = out_dir / "summary.csv"
    canonical.to_csv(canonical_csv, index=False)
    print(f"Wrote canonical summary table -> {canonical_csv}")

    print(
        f"\nCanonical view ({args.canonical_points} sampled points, "
        f"F-threshold = {args.canonical_f}):"
    )
    markdown = dataframe_to_markdown(canonical)
    print()
    print(markdown)
    print()

    if args.write_markdown:
        md_path = out_dir / "summary.md"
        md_path.write_text(markdown + "\n", encoding="utf-8")
        print(f"Wrote Markdown table -> {md_path}")


if __name__ == "__main__":
    main()
