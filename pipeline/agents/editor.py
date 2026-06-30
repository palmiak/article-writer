import json

from pipeline.agents import run_agent_call, _extract_json
from pipeline.agents.personas import MACIEK_STYLE_GUIDE
from pipeline.config import MODEL_EDITOR

SECTION_REVIEW_PROMPT = """\
You are a meticulous article editor. Review the given section against the article plan, research, and persona requirements.

## Persona the article should follow
Name: {persona_name}
Tone: {persona_tone}
Style: {persona_style}
{style_guide}
## Output Format
Output valid JSON (no markdown fences):
{{
  "approved": true/false,
  "issues": ["issue 1", "issue 2"],
  "suggested_edits": ["edit suggestion 1", "edit suggestion 2"]
}}

## Review Criteria
- Plan adherence: does it cover the key points listed in the section plan and avoid what_not_to_cover?
- Factual plausibility: do the claims seem grounded and internally consistent?
- Persona consistency: does it match the specified tone and style?
- Quality: is the writing clear, engaging, and well-structured?
"""

TRANSITIONS_REVIEW_PROMPT = """\
You are an article editor reviewing the flow between sections. Check that sections connect logically, there are no abrupt topic changes, and the article reads as a cohesive whole.

## Persona
Tone: {persona_tone}
Style: {persona_style}
{style_guide}
## Output Format
Output valid JSON (no markdown fences):
{{
  "issues": [
    {{"between_sections": [1, 2], "issue": "description"}},
  ],
  "suggested_transitions": {{
    "1_to_2": "Suggested transition sentence or approach",
  }}
}}
"""

FINAL_ASSEMBLY_PROMPT = """\
You are an article editor doing final assembly. Combine the sections into a polished article. Apply any transition improvements, polish the introduction and conclusion, and ensure the article flows as one cohesive piece.

## Persona
Name: {persona_name}
Tone: {persona_tone}
Style: {persona_style}
Perspective: {persona_perspective}
{style_guide}
## Rules
- Preserve the factual content of each section — do NOT add new facts.
- Improve transitions between sections where noted.
- Ensure the introduction hooks the reader and the conclusion provides closure.
- Output ONLY the final article in markdown. No preamble.
"""


async def review_section(
    section_text: str,
    section_plan: dict,
    full_plan: dict,
    research_dump: str,
    persona: dict,
) -> dict:
    system = SECTION_REVIEW_PROMPT.format(
        persona_name=persona["name"],
        persona_tone=persona["tone"],
        persona_style=persona["style"],
        style_guide=MACIEK_STYLE_GUIDE,
    )
    prompt = f"""\
<plan>
{json.dumps(full_plan, indent=2)}
</plan>

<section_plan>
{json.dumps(section_plan, indent=2)}
</section_plan>

<section_text>
{section_text}
</section_text>

Review this section.
"""
    response = await run_agent_call(system=system, prompt=prompt, model=MODEL_EDITOR)
    return _extract_json(response)


async def review_transitions(
    section_texts: list[str],
    article_plan: dict,
    persona: dict,
) -> dict:
    system = TRANSITIONS_REVIEW_PROMPT.format(
        persona_tone=persona["tone"],
        persona_style=persona["style"],
        style_guide=MACIEK_STYLE_GUIDE,
    )
    sections_block = ""
    for i, text in enumerate(section_texts, 1):
        sections_block += f"\n--- Section {i} ---\n{text}\n"

    prompt = f"""\
<plan>
{json.dumps(article_plan, indent=2)}
</plan>

<sections>
{sections_block}
</sections>

Review the transitions and flow between sections.
"""
    response = await run_agent_call(system=system, prompt=prompt, model=MODEL_EDITOR)
    return _extract_json(response)


CONDENSER_PROMPT = """\
You are a ruthless but precise editor. Your job is to condense the article — make it tighter and sharper without losing any important ideas, arguments, or facts.

## Rules
- Cut redundant sentences, filler, and padding — if a sentence doesn't add new information, delete it.
- Remove repetitions: if the same point is made more than once, keep the sharpest version and cut the rest.
- For any bullet or numbered lists: keep only the strongest 2-3 examples. Drop the weakest ones. Never add new items.
- Preserve every distinct idea, argument, data point, and the author's voice and tone.
- Do NOT rewrite the substance — only cut. Do NOT add new content.
- Output ONLY the condensed article in markdown. No preamble or commentary.
"""


async def condense(article_text: str) -> str:
    from pipeline.agents import run_agent_call
    return await run_agent_call(
        system=CONDENSER_PROMPT,
        prompt=article_text,
        model=MODEL_EDITOR,
    )


async def assemble_final(
    section_texts: list[str],
    article_plan: dict,
    transitions_review: dict,
    persona: dict,
) -> tuple[str, dict]:
    system = FINAL_ASSEMBLY_PROMPT.format(
        persona_name=persona["name"],
        persona_tone=persona["tone"],
        persona_style=persona["style"],
        persona_perspective=persona["perspective"],
        style_guide=MACIEK_STYLE_GUIDE,
    )
    sections_block = ""
    for i, text in enumerate(section_texts, 1):
        sections_block += f"\n--- Section {i} ---\n{text}\n"

    prompt = f"""\
<plan>
{json.dumps(article_plan, indent=2)}
</plan>

<transitions_review>
{json.dumps(transitions_review, indent=2)}
</transitions_review>

<sections>
{sections_block}
</sections>

Assemble the final article.
"""
    final_text = await run_agent_call(system=system, prompt=prompt, model=MODEL_EDITOR)

    final_review = {
        "sections_count": len(section_texts),
        "title": article_plan.get("title", ""),
        "status": "assembled",
    }

    return final_text, final_review
