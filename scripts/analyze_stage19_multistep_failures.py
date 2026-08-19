"""Create Stage 19 read-only JSON and SVG artifacts from a Stage 18 report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from openpi_robot_runtime.stage19_analysis import analyze_stage18_report, mean_curve_svg


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_report", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    report = json.loads(args.input_report.read_text(encoding="utf-8"))
    analysis = analyze_stage18_report(report)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "report.json").write_text(json.dumps(analysis, indent=2), encoding="utf-8")
    (args.output_dir / "mean_distance_curves.svg").write_text(mean_curve_svg(analysis), encoding="utf-8")
    print(json.dumps({"variants": {key: {field: value for field, value in summary.items() if field != "mean_distance_curve_m"} for key, summary in analysis["variants"].items()}}, indent=2))


if __name__ == "__main__":
    main()
