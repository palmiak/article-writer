#!/usr/bin/env python3
"""Stage 1: Research agent — gathers information and produces an article plan."""

import argparse
import asyncio
import json

from pipeline.config import ensure_workspace, file_exists_prompt
from pipeline.input import parse_input_file
from pipeline.agents.personas import get_persona
from pipeline.agents.researcher import run_researcher


async def main():
    parser = argparse.ArgumentParser(description="Run the research agent")
    parser.add_argument("--input", required=True, help="Path to frontmatter markdown input file")
    parser.add_argument("--yolo", action="store_true", help="Skip all prompts and overwrite existing files")
    args = parser.parse_args()

    article = parse_input_file(args.input)
    persona = get_persona(article.persona)
    ws = ensure_workspace(article.slug)
    output_file = ws / "research.json"

    if not args.yolo and not file_exists_prompt(output_file, "research.json"):
        print("Aborted.")
        return

    print(f"Researching: {article.topic}")
    print(f"Persona: {persona['name']}")
    if article.aim:
        print(f"Aim: {article.aim}")
    if article.links:
        print(f"Links to fetch: {len(article.links)}")
    print("This may take a few minutes...\n")

    result = await run_researcher(
        topic=article.topic,
        persona=persona,
        aim=article.aim,
        links=article.links,
        notes=article.notes,
    )

    output_file.write_text(json.dumps(result, indent=2))
    print(f"\nResearch saved to {output_file}")

    plan = result.get("article_plan", {})
    print(f"\nTitle: {plan.get('title', 'N/A')}")
    print(f"Angle: {plan.get('angle', 'N/A')}")
    print(f"Target audience: {plan.get('target_audience', 'N/A')}")
    print(f"\nSections ({len(plan.get('sections', []))}):")
    for section in plan.get("sections", []):
        print(f"  {section['section_number']}. {section['title']}")


if __name__ == "__main__":
    asyncio.run(main())
