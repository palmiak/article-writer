from pipeline.agents import run_agent_call
from pipeline.agents.personas import MACIEK_STYLE_GUIDE
from pipeline.config import MODEL_WRITER, MODEL_FACTS

WRITER_SYSTEM_PROMPT = """\
You are a skilled article writer. You write one section at a time based on research provided to you.

## Persona
Name: {persona_name}
Tone: {persona_tone}
Style: {persona_style}
Perspective: {persona_perspective}
{style_guide}
## Rules
- ONLY use facts, data, and claims from the provided research dump. Do NOT invent or hallucinate facts.
- Write in the persona's voice consistently.
- Output ONLY the section content in markdown. No preamble, no "Here is the section", just the content.
- Use ## for the section heading.
- Keep the section focused on its designated key points.
- Avoid covering topics listed in "what_not_to_cover".
- Reference the facts already established in previous sections to maintain consistency.
"""

REVISE_SECTION_PROMPT = """\
You are a skilled article editor applying specific improvement suggestions to a section.

## Persona
Name: {persona_name}
Tone: {persona_tone}
Style: {persona_style}
Perspective: {persona_perspective}
{style_guide}
## Rules
- Apply ONLY the listed suggested edits. Do not invent new content or add facts not in the original.
- Preserve all factual content from the original section.
- Output ONLY the revised section in markdown. No preamble.
"""

FACTS_SUMMARIZER_PROMPT = """\
You are a facts tracker. Given the previous facts summary and a new article section, produce an updated summary of all factual claims, data points, statistics, names, and specific assertions made so far. This will be used to keep future sections consistent.

Output ONLY the updated facts summary as a bullet-point list. Be concise but comprehensive.
"""


async def write_section(
    research_dump: str,
    article_plan: dict,
    section: dict,
    facts_established: str,
    persona: dict,
) -> str:
    import json

    system = WRITER_SYSTEM_PROMPT.format(
        persona_name=persona["name"],
        persona_tone=persona["tone"],
        persona_style=persona["style"],
        persona_perspective=persona["perspective"],
        style_guide=MACIEK_STYLE_GUIDE,
    )

    prompt = f"""\
<research>
{research_dump}
</research>

<plan>
{json.dumps(article_plan, indent=2)}
</plan>

<section>
{json.dumps(section, indent=2)}
</section>

<facts_established>
{facts_established or "No previous sections written yet."}
</facts_established>

Write section {section['section_number']}: "{section['title']}"
"""

    return await run_agent_call(system=system, prompt=prompt, model=MODEL_WRITER)


async def revise_section(
    section_text: str,
    suggested_edits: list,
    persona: dict,
) -> str:
    system = REVISE_SECTION_PROMPT.format(
        persona_name=persona["name"],
        persona_tone=persona["tone"],
        persona_style=persona["style"],
        persona_perspective=persona["perspective"],
        style_guide=MACIEK_STYLE_GUIDE,
    )
    edits_block = "\n".join(f"- {e}" for e in suggested_edits)
    prompt = f"""\
<original_section>
{section_text}
</original_section>

<suggested_edits>
{edits_block}
</suggested_edits>

Apply the suggested edits to the section.
"""
    return await run_agent_call(system=system, prompt=prompt, model=MODEL_WRITER)


async def summarize_facts(previous_facts: str, new_section_text: str, section_title: str) -> str:
    prompt = f"""\
Previous facts summary:
{previous_facts or "None yet."}

New section "{section_title}":
{new_section_text}

Produce the updated facts summary.
"""
    return await run_agent_call(
        system=FACTS_SUMMARIZER_PROMPT,
        prompt=prompt,
        model=MODEL_FACTS,
    )
