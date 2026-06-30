#!/usr/bin/env python3
"""Full pipeline: research → write → edit, all in yolo mode."""

import argparse
import subprocess
import sys


def run(script: str, input_path: str, extra_args: list[str] | None = None):
    cmd = [sys.executable, script, "--input", input_path] + (extra_args or [])
    print(f"\n{'=' * 60}")
    print(f"Running: {' '.join(cmd)}")
    print("=" * 60 + "\n")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        print(f"\nError: {script} exited with code {result.returncode}. Aborting.")
        sys.exit(result.returncode)


def main():
    parser = argparse.ArgumentParser(description="Run the full article pipeline in yolo mode")
    parser.add_argument("--input", required=True, help="Path to frontmatter markdown input file")
    parser.add_argument(
        "--journey",
        action="store_true",
        help="Use run_journey_prep.py instead of run_research.py",
    )
    parser.add_argument("--condense", action="store_true", help="Run the condenser pass after humanization")
    args = parser.parse_args()

    research_script = "run_journey_prep.py" if args.journey else "run_research.py"

    run(research_script, args.input)
    run("run_writing.py", args.input)
    editing_args = ["--yolo"]
    if args.condense:
        editing_args.append("--condense")
    run("run_editing.py", args.input, editing_args)


if __name__ == "__main__":
    main()
