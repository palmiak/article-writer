#!/usr/bin/env python3
"""Standalone condenser — trims an article file and saves a condensed version alongside it."""

import argparse
import asyncio
from pathlib import Path

from pipeline.agents.editor import condense


async def main():
    parser = argparse.ArgumentParser(description="Condense a markdown article")
    parser.add_argument("--input", required=True, help="Path to a markdown file to condense")
    args = parser.parse_args()

    input_path = Path(args.input).resolve()
    if not input_path.exists():
        print(f"Error: {input_path} not found.")
        return

    text = input_path.read_text()
    print(f"Condensing {input_path.name}...")

    condensed = await condense(text)

    output_path = input_path.with_stem(input_path.stem + "_condensed")
    output_path.write_text(condensed)
    print(f"Saved to {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
