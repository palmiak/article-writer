from pipeline.agents import run_agent_call, _extract_json
from pipeline.config import MODEL_RESEARCH

RESEARCHER_SYSTEM_PROMPT = """\
You are a thorough research agent. Your job is to research a given topic deeply using web search and produce a comprehensive research package.

## Persona
You are writing research for an author whose voice is: {persona_tone}.
Their perspective: {persona_perspective}
Tailor your research angle and focus to support this voice.
{aim_section}
## Output Format
You MUST output valid JSON with exactly this structure (no markdown fences, no extra text):

{{
  "research_dump": "A comprehensive markdown string containing all research findings, sources, data points, quotes, and context gathered during research. Be thorough — this is the only material the writer will have access to.",
  "article_plan": {{
    "title": "Proposed article title",
    "angle": "The specific angle or thesis for the article",
    "target_audience": "Who this article is for",
    "sections": [
      {{
        "section_number": 1,
        "title": "Section title",
        "key_points": ["Point 1", "Point 2"],
        "key_facts": ["Specific fact or data point to include"],
        "what_not_to_cover": "What to explicitly avoid in this section"
      }}
    ]
  }}
}}

## Guidelines
- Research thoroughly using multiple sources
- Aim for 4-7 sections in the article plan
- Include specific data, statistics, and quotes in research_dump
- Each section should have a clear purpose and not overlap with others
- The plan should tell a coherent story from introduction to conclusion
"""


async def run_researcher(
    topic: str,
    persona: dict,
    aim: str = "",
    links: list[str] | None = None,
    notes: str = "",
) -> dict:
    aim_section = (
        f"\n## Article Aim\n{aim}\nKeep this goal in mind when framing the research angle and planning sections.\n"
        if aim
        else ""
    )
    system = RESEARCHER_SYSTEM_PROMPT.format(
        persona_tone=persona["tone"],
        persona_perspective=persona["perspective"],
        aim_section=aim_section,
    )

    prompt_parts = [f"Research this topic thoroughly and produce a research package:\n\n{topic}"]
    if notes:
        prompt_parts.append(f"\n\nAdditional context from the author:\n{notes}")
    if links:
        links_block = "\n".join(f"- {url}" for url in links)
        prompt_parts.append(
            f"\n\nThe following links MUST be fetched and included in your research:\n{links_block}"
        )
    prompt = "".join(prompt_parts)

    response = await run_agent_call(
        system=system,
        prompt=prompt,
        model=MODEL_RESEARCH,
        tools=["WebSearch", "WebFetch"],
    )
    return _extract_json(response)
