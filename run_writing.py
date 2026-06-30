#!/usr/bin/env python3
"""Stage 2: Writer agent — writes article sections one at a time."""

import argparse
import asyncio
import json

from pipeline.config import ensure_workspace, file_exists_prompt, pause_for_review
from pipeline.input import parse_input_file
from pipeline.agents.personas import get_persona
from pipeline.agents.writer import write_section, summarize_facts


async def main():
    parser = argparse.ArgumentParser(description="Run the writer agent")
    parser.add_argument("--input", required=True, help="Path to frontmatter markdown input file")
    parser.add_argument("--start-from", type=int, default=1, help="Section number to start from (default: 1)")
    parser.add_argument("--yolo", action="store_true", help="Skip all prompts and overwrite existing files")
    args = parser.parse_args()

    article = parse_input_file(args.input)
    persona = get_persona(article.persona)
    ws = ensure_workspace(article.slug)
    research_file = ws / "research.json"

    if not research_file.exists():
        print(f"Error: {research_file} not found. Run research stage first.")
        return

    research = json.loads(research_file.read_text())
    research_dump = research.get("research_dump", "")
    article_plan = research.get("article_plan", {})
    sections = article_plan.get("sections", [])

    if not sections:
        print("Error: No sections found in article plan.")
        return

    print(f"Writing article: {article_plan.get('title', 'N/A')}")
    print(f"Persona: {persona['name']}")
    print(f"Sections: {len(sections)}, starting from {args.start_from}\n")

    # Load or rebuild facts_established
    facts_file = ws / "draft" / "facts_summary.txt"
    facts_established = ""

    if args.start_from > 1:
        print("Rebuilding facts from existing sections...")
        for i in range(1, args.start_from):
            section_file = ws / "draft" / f"section_{i}.md"
            if not section_file.exists():
                print(f"Error: section_{i}.md not found but --start-from={args.start_from}")
                return
            section_text = section_file.read_text()
            section_data = next((s for s in sections if s["section_number"] == i), None)
            title = section_data["title"] if section_data else f"Section {i}"
            facts_established = await summarize_facts(facts_established, section_text, title)
            print(f"  Rebuilt facts through section {i}")
        print()

    for section in sections:
        num = section["section_number"]
        if num < args.start_from:
            continue

        section_file = ws / "draft" / f"section_{num}.md"

        if not args.yolo and not file_exists_prompt(section_file, f"section_{num}.md"):
            print(f"Skipping section {num}.")
            continue

        print(f"Writing section {num}: {section['title']}...")
        section_text = await write_section(
            research_dump=research_dump,
            article_plan=article_plan,
            section=section,
            facts_established=facts_established,
            persona=persona,
        )

        section_file.write_text(section_text)
        print(f"  Saved to {section_file}")

        facts_established = await summarize_facts(facts_established, section_text, section["title"])
        facts_file.write_text(facts_established)

        if not args.yolo:
            pause_for_review(f"Section {num} written: \"{section['title']}\".")

    print("\nAll sections written.")


if __name__ == "__main__":
    asyncio.run(main())
