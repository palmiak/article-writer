from pipeline.agents import run_agent_call, _extract_json
from pipeline.config import MODEL_EDITOR

FACT_CHECKER_PROMPT = """\
You are a rigorous fact-checker with web search access. Your job is to verify factual claims in an article section.

## Process
1. Read the section and identify all concrete factual claims: statistics, dates, event histories, organization facts, named studies, quotes, product details.
2. For each claim, search the web to verify it against real sources.
3. Flag any claim that:
   - Cannot be confirmed by a credible source
   - Contradicts what you find on the web
   - Contains specific numbers or dates that don't match real data
   - Describes an event history (e.g. "first time", "launched in X") that turns out to be inaccurate
4. Do NOT flag opinions, subjective assessments, or claims you simply cannot find (only flag if you find contradicting evidence or if the claim is suspiciously specific with no traceable source at all).

## Output Format
Output valid JSON (no markdown fences):
{{
  "flagged_claims": [
    {{
      "claim": "exact quote of the problematic claim",
      "issue": "contradicts sources | unverifiable statistic | inaccurate event history | fabricated data",
      "what_was_found": "brief summary of what the web search actually shows",
      "suggestion": "remove | correct to: <corrected version> | rewrite as opinion | add source citation"
    }}
  ],
  "verdict": "clean | needs_attention"
}}
"""


async def check_facts(section_text: str, research_dump: str, section_title: str) -> dict:
    prompt = f"""\
<research_context>
{research_dump}
</research_context>

<section title="{section_title}">
{section_text}
</section>

Identify all factual claims in this section, search the web to verify them, and flag anything inaccurate or unverifiable.
"""
    response = await run_agent_call(
        system=FACT_CHECKER_PROMPT,
        prompt=prompt,
        model=MODEL_EDITOR,
        tools=["WebSearch", "WebFetch"],
    )
    return _extract_json(response)
