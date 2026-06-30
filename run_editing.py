#!/usr/bin/env python3
"""Stage 3: Editor agent — reviews sections, transitions, assembles, and humanizes the final article."""

import argparse
import asyncio
import json

from pipeline.config import ensure_workspace, pause_for_review
from pipeline.input import parse_input_file
from pipeline.agents.personas import get_persona
from pipeline.agents.editor import review_section, review_transitions, assemble_final, condense
from pipeline.agents.fact_checker import check_facts
from pipeline.agents.humanizer import humanize
from pipeline.agents.writer import write_section, revise_section, summarize_facts

MAX_REVIEW_LOOPS = 3


async def main():
    parser = argparse.ArgumentParser(description="Run the editor agent")
    parser.add_argument("--input", required=True, help="Path to frontmatter markdown input file")
    parser.add_argument("--yolo", action="store_true", help="Skip all prompts and auto-rewrite failing sections")
    parser.add_argument("--condense", action="store_true", help="Run the condenser pass after humanization")
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

    # Load all section files
    section_texts = []
    for section in sections:
        num = section["section_number"]
        section_file = ws / "draft" / f"section_{num}.md"
        if not section_file.exists():
            print(f"Error: {section_file} not found. Run writing stage first.")
            return
        section_texts.append(section_file.read_text())

    print(f"Editing article: {article_plan.get('title', 'N/A')}")
    print(f"Persona: {persona['name']}")
    print(f"Sections to review: {len(sections)}\n")

    # Pass 0: Fact checking
    print("=" * 50)
    print("PASS 0: Fact Checking")
    print("=" * 50)

    any_fact_issues = False
    for i, section in enumerate(sections):
        num = section["section_number"]
        print(f"\nFact-checking section {num}: {section['title']}...")

        fact_result = await check_facts(
            section_text=section_texts[i],
            research_dump=research_dump,
            section_title=section["title"],
        )

        fact_file = ws / "reviews" / f"section_{num}_facts.json"
        fact_file.write_text(json.dumps(fact_result, indent=2))

        flagged = fact_result.get("flagged_claims", [])
        verdict = fact_result.get("verdict", "clean")
        print(f"  Verdict: {verdict.upper()} — {len(flagged)} flagged claim(s)")
        for claim in flagged:
            print(f"  [FLAGGED] \"{claim['claim']}\"")
            print(f"            Issue: {claim['issue']}")
            print(f"            Fix:   {claim['suggestion']}")
            any_fact_issues = True

    if any_fact_issues and not args.yolo:
        pause_for_review("\nFact-check complete. Review flagged claims above before continuing.")
    elif not any_fact_issues:
        print("\nNo factual issues found.")

    # Pass 1: Section reviews
    print("\n" + "=" * 50)
    print("PASS 1: Section Reviews")
    print("=" * 50)

    for i, section in enumerate(sections):
        num = section["section_number"]
        review_file = ws / "reviews" / f"section_{num}_review.json"

        print(f"\nReviewing section {num}: {section['title']}...")

        for attempt in range(MAX_REVIEW_LOOPS):
            review = await review_section(
                section_text=section_texts[i],
                section_plan=section,
                full_plan=article_plan,
                research_dump=research_dump,
                persona=persona,
            )
            review_file.write_text(json.dumps(review, indent=2))

            approved = review.get("approved")
            suggested_edits = review.get("suggested_edits", [])
            status = "APPROVED" if approved else "NEEDS REVISION"
            loop_label = f" (attempt {attempt + 1}/{MAX_REVIEW_LOOPS})" if attempt > 0 else ""
            print(f"  Status: {status}{loop_label}")
            for issue in review.get("issues", []):
                print(f"  - {issue}")

            if approved:
                # Apply suggested_edits once in yolo mode even when approved
                if args.yolo and suggested_edits:
                    print(f"  Applying {len(suggested_edits)} suggested edit(s)...")
                    for edit in suggested_edits:
                        print(f"  · {edit}")
                    new_text = await revise_section(
                        section_text=section_texts[i],
                        suggested_edits=suggested_edits,
                        persona=persona,
                    )
                    section_file = ws / "draft" / f"section_{num}.md"
                    section_file.write_text(new_text)
                    section_texts[i] = new_text
                    print(f"  Section {num} revised with suggestions.")
                break

            # Not approved — decide whether to rewrite
            if attempt == MAX_REVIEW_LOOPS - 1:
                print(f"  Max attempts ({MAX_REVIEW_LOOPS}) reached, keeping last version.")
                break

            do_rewrite = args.yolo
            if not args.yolo:
                answer = input(f"  Re-run writer for section {num}? (y/n): ").strip().lower()
                do_rewrite = answer == "y"

            if not do_rewrite:
                break

            facts_established = ""
            for j in range(i):
                prev_section = sections[j]
                facts_established = await summarize_facts(
                    facts_established,
                    section_texts[j],
                    prev_section["title"],
                )

            print(f"  Re-writing section {num} (attempt {attempt + 2}/{MAX_REVIEW_LOOPS})...")
            new_text = await write_section(
                research_dump=research_dump,
                article_plan=article_plan,
                section=section,
                facts_established=facts_established,
                persona=persona,
            )
            section_file = ws / "draft" / f"section_{num}.md"
            section_file.write_text(new_text)
            section_texts[i] = new_text

    if not args.yolo:
        pause_for_review("\nSection reviews complete.")

    # Pass 2: Transitions review
    print("\n" + "=" * 50)
    print("PASS 2: Transitions Review")
    print("=" * 50)

    transitions = await review_transitions(section_texts, article_plan, persona)
    transitions_file = ws / "reviews" / "transitions_review.json"
    transitions_file.write_text(json.dumps(transitions, indent=2))

    print(f"\nTransition issues found: {len(transitions.get('issues', []))}")
    for issue in transitions.get("issues", []):
        sections_between = issue.get("between_sections", "?")
        print(f"  - Between sections {sections_between}: {issue.get('issue', '')}")

    if not args.yolo:
        pause_for_review("\nTransitions review complete.")

    # Pass 3: Final assembly
    print("\n" + "=" * 50)
    print("PASS 3: Final Assembly")
    print("=" * 50)

    print("\nAssembling final article...")
    final_text, final_review = await assemble_final(
        section_texts, article_plan, transitions, persona
    )

    final_file = ws / "final_article.md"
    final_file.write_text(final_text)

    final_review_file = ws / "reviews" / "final_review.json"
    final_review_file.write_text(json.dumps(final_review, indent=2))

    print(f"\nFinal article saved to {final_file}")

    if not args.yolo:
        pause_for_review("\nFinal assembly complete.")

    # Pass 4: Humanizer
    print("\n" + "=" * 50)
    print("PASS 4: Humanizer")
    print("=" * 50)

    print("\nRemoving AI writing patterns...")
    humanized_text = await humanize(final_text)

    humanized_file = ws / "final_article_humanized.md"
    humanized_file.write_text(humanized_text)

    print(f"\nHumanized article saved to {humanized_file}")

    if args.condense:
        if not args.yolo:
            pause_for_review("\nHumanizer complete.")

        # Pass 5: Condenser
        print("\n" + "=" * 50)
        print("PASS 5: Condenser")
        print("=" * 50)

        print("\nCondensing article...")
        condensed_text = await condense(humanized_text)

        condensed_file = ws / "final_article_condensed.md"
        condensed_file.write_text(condensed_text)

        print(f"\nCondensed article saved to {condensed_file}")

    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())
