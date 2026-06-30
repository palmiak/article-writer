#!/usr/bin/env python3
"""Journey prep: processes GPX tracks, geotagged photos, and a reflection into research.json.

Replaces the research stage for personal journey/travel articles.
The writing and editing stages run unchanged afterwards.

Usage:
    python run_journey_prep.py --input my-trip/article.md
    python run_journey_prep.py --input my-trip/article.md --yolo
"""

import argparse
import asyncio
import json
from pathlib import Path

from pipeline.config import ensure_workspace, file_exists_prompt
from pipeline.input import parse_input_file
from pipeline.agents.personas import get_persona
from pipeline.journey import process_gpx, process_photos_dir, build_journey_brief
from pipeline.agents.journey_planner import run_journey_planner


async def main():
    parser = argparse.ArgumentParser(description="Run the journey prep agent")
    parser.add_argument("--input", required=True, help="Path to frontmatter markdown input file")
    parser.add_argument("--yolo", action="store_true", help="Skip all prompts and overwrite existing files")
    args = parser.parse_args()

    article = parse_input_file(args.input)
    base = article.base_dir

    if not article.gpx_files and not article.photos_dir and not article.reflection:
        print("Error: frontmatter must include at least one of: gpx_files, photos_dir, reflection")
        return

    persona = get_persona(article.persona)
    ws = ensure_workspace(article.slug)
    output_file = ws / "research.json"

    if not args.yolo and not file_exists_prompt(output_file, "research.json"):
        print("Aborted.")
        return

    # ------------------------------------------------------------------
    # Step 1: Process GPX tracks
    # ------------------------------------------------------------------
    days = []
    if article.gpx_files:
        print(f"\nProcessing {len(article.gpx_files)} GPX track(s)...")
        for gpx_rel in article.gpx_files:
            gpx_path = base / gpx_rel
            if not gpx_path.exists():
                print(f"  Warning: {gpx_path} not found, skipping.")
                continue
            print(f"  {gpx_path.name}...")
            try:
                day = process_gpx(gpx_path)
                days.append(day)
                print(f"    {day.date}: {day.start_place} → {day.end_place} | {day.distance_km} km | +{day.elevation_gain_m}m")
            except Exception as e:
                print(f"  Warning: failed to process {gpx_path.name}: {e}")

    # ------------------------------------------------------------------
    # Step 2: Process photos
    # ------------------------------------------------------------------
    photo_notes = []
    if article.photos_dir:
        photos_dir = base / article.photos_dir
        if not photos_dir.exists():
            print(f"\nWarning: photos_dir '{photos_dir}' not found, skipping.")
        else:
            print(f"\nProcessing photos in {photos_dir}...")
            photo_notes = process_photos_dir(photos_dir)
            geotagged = len(photo_notes)
            noted = sum(1 for p in photo_notes if p.note)
            print(f"  {geotagged} geotagged photo(s), {noted} with sidecar notes")

    # ------------------------------------------------------------------
    # Step 3: Read reflection
    # ------------------------------------------------------------------
    reflection = ""
    if article.reflection:
        reflection_path = base / article.reflection
        if not reflection_path.exists():
            print(f"\nWarning: reflection file '{reflection_path}' not found, skipping.")
        else:
            reflection = reflection_path.read_text().strip()
            print(f"\nReflection loaded: {len(reflection.splitlines())} lines")
    # Also include any inline notes from the frontmatter body
    if article.notes:
        reflection = (reflection + "\n\n" + article.notes).strip()

    # ------------------------------------------------------------------
    # Step 4: Build brief
    # ------------------------------------------------------------------
    print("\nBuilding journey brief...")
    brief = build_journey_brief(
        days=days,
        photo_notes=photo_notes,
        reflection=reflection,
        topic=article.topic,
    )

    brief_file = ws / "journey_brief.md"
    brief_file.write_text(brief)
    print(f"Journey brief saved to {brief_file}")

    # ------------------------------------------------------------------
    # Step 5: Generate article plan via Claude
    # ------------------------------------------------------------------
    print("\nGenerating article plan...")
    if article.aim:
        print(f"Aim: {article.aim}")

    result = await run_journey_planner(
        brief=brief,
        persona=persona,
        aim=article.aim,
    )

    output_file.write_text(json.dumps(result, indent=2))
    print(f"\nResearch saved to {output_file}")

    plan = result.get("article_plan", {})
    print(f"\nTitle: {plan.get('title', 'N/A')}")
    print(f"Angle: {plan.get('angle', 'N/A')}")
    print(f"\nSections ({len(plan.get('sections', []))}):")
    for section in plan.get("sections", []):
        print(f"  {section['section_number']}. {section['title']}")

    print(f"\nNext steps:")
    print(f"  python run_writing.py --input {args.input}")
    print(f"  python run_editing.py --input {args.input}")


if __name__ == "__main__":
    asyncio.run(main())
