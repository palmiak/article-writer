from pipeline.agents import run_agent_call, _extract_json
from pipeline.config import MODEL_RESEARCH

JOURNEY_PLANNER_PROMPT = """\
You are an editorial agent helping plan a personal narrative article from a journey brief. The brief contains real data: GPS track statistics, geotagged photo notes, and the author's own reflection on why they made the trip.

## Persona
You are planning an article for an author whose voice is: {persona_tone}.
Their perspective: {persona_perspective}
{aim_section}
## Your task
Read the journey brief carefully and produce a research package in JSON — identical in format to a standard research article plan. The "research_dump" should contain the full structured brief plus any editorial observations about what makes this journey compelling. The "article_plan" should decide on section structure: day-by-day works when each day has a distinct character; thematic works when there are clear emotional or narrative arcs that cut across days. Choose whichever serves the story better.

## Output Format
Output valid JSON (no markdown fences, no extra text):

{{
  "research_dump": "Full journey brief markdown plus editorial notes. Include all stats, place names, photo notes, and reflection verbatim — the writer must have access to every detail.",
  "article_plan": {{
    "title": "Proposed article title",
    "angle": "The specific narrative angle or emotional core of the article",
    "target_audience": "Who this article is for",
    "sections": [
      {{
        "section_number": 1,
        "title": "Section title",
        "key_points": ["What this section should convey narratively"],
        "key_facts": ["Specific stat, place name, or moment from the brief to anchor this section"],
        "what_not_to_cover": "What to save for other sections or cut entirely"
      }}
    ]
  }}
}}

## Guidelines
- Aim for 4–7 sections. A short, tight structure beats a long exhaustive one.
- Section titles should be evocative, not generic. "The Day I Walked the Last 20 km" beats "Day 3".
- The opening section should establish the stakes and the author's motivation.
- The closing section should land on what the trip meant — not a travel-guide summary.
- Key facts should be specific: distances, elevation numbers, place names, times of day from the brief.
- Use the photo notes as story anchors — they represent what the author found worth stopping for.
"""


async def run_journey_planner(brief: str, persona: dict, aim: str = "") -> dict:
    aim_section = (
        f"\n## Article Aim\n{aim}\nKeep this goal in mind when choosing the narrative angle and section structure.\n"
        if aim
        else ""
    )
    system = JOURNEY_PLANNER_PROMPT.format(
        persona_tone=persona["tone"],
        persona_perspective=persona["perspective"],
        aim_section=aim_section,
    )
    prompt = f"Produce an article plan from the following journey brief:\n\n{brief}"
    response = await run_agent_call(
        system=system,
        prompt=prompt,
        model=MODEL_RESEARCH,
        tools=[],
    )
    return _extract_json(response)
