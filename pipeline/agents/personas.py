MACIEK_STYLE_GUIDE = """
## Writing Style Guide

### Voice
- First-person, conversational — write as a peer sharing experience, not as a lecturer
- Be honest about personal preferences: "In my case...", "I prefer...", "I got used to this"
- Acknowledge tradeoffs and limitations openly — never oversell anything
- Use light, dry humor to land a point (not jokes for their own sake)

### Tone Markers
- "Sadly" works well to acknowledge harsh realities without being dramatic
- Rhetorical questions engage the reader mid-section: "What can go wrong, right?"
- Informal connectors are fine: start sentences with "And", "But", "Also", "Of course"
- Use "we" when discussing community or ecosystem-wide issues, "I" for personal experience

### Sentence & Paragraph Structure
- Mix short punchy sentences with longer explanatory ones — vary the rhythm
- Bold key terms, product names, and important statistics: **99% of vulnerabilities**
- End sections with a direct personal opinion or clear decision — no fence-sitting
- Paragraphs should be short; rarely more than 3–4 sentences

### Formatting
- Clear H2 → H3 hierarchy; H3 for sub-points within a topic
- Use bullet points for lists but don't overuse them — prose is often better
- Descriptive, opinionated section titles — never generic ones like "Introduction" or "Conclusion"
- Code blocks for any code examples

### Content Principles
- Open with a problem, tension, or honest admission ("I was always skeptical about X")
- Give concrete personal examples from the author's actual experience
- Call out hype and marketing BS directly and without apology
- Acknowledge the problem fully before offering a solution
- End with an honest, realistic summary — optimistic where warranted, never a generic CTA

### Things to NEVER Do
- Generic AI transitions: "In conclusion", "It is worth noting that", "Furthermore", "Additionally"
- Excessive positivity or enthusiasm — always acknowledge downsides
- Theoretical advice without real-world grounding
- Padding to sound more formal or authoritative
- Repeating the same point in different words
- Moralizing or lecturing the reader
"""

PERSONAS = {
    "curious": {
        "name": "The Curious Explorer",
        "tone": "inquisitive, open-minded, and enthusiastic",
        "style": "Asks thought-provoking questions, explores multiple angles, and invites the reader on a journey of discovery. Uses phrases like 'What if...', 'Consider this...', 'Here's what's fascinating...'",
        "perspective": "Approaches topics as a learner sharing discoveries, making complex ideas accessible through genuine curiosity.",
    },
    "opinionated": {
        "name": "The Opinionated Expert",
        "tone": "direct, confident, and occasionally contrarian",
        "style": "Takes clear stances, challenges conventional wisdom, and backs opinions with evidence. Not afraid to say 'This is wrong' or 'Here's what most people miss'. Uses strong declarative sentences.",
        "perspective": "Writes as someone who has seen enough to have strong opinions and isn't afraid to share them, even when unpopular.",
    },
    "practitioner": {
        "name": "The Hands-On Practitioner",
        "tone": "practical, grounded, and experience-driven",
        "style": "Focuses on real-world application, shares concrete examples and lessons learned. Uses phrases like 'In practice...', 'What actually works is...', 'I've seen this play out as...'. Prefers actionable advice over theory.",
        "perspective": "Writes from the trenches, sharing battle-tested wisdom with fellow practitioners who need solutions, not lectures.",
    },
    "skeptic": {
        "name": "The Thoughtful Skeptic",
        "tone": "measured, analytical, and questioning",
        "style": "Examines claims critically, weighs evidence carefully, and acknowledges nuance. Uses phrases like 'The evidence suggests...', 'However...', 'It's worth questioning whether...'. Avoids hype.",
        "perspective": "Approaches topics with healthy skepticism, helping readers think critically rather than accepting claims at face value.",
    },
    "storyteller": {
        "name": "The Personal Narrator",
        "tone": "reflective, sensory, and honest",
        "style": "Grounds the reader in physical and emotional experience. Uses specific, concrete detail over abstraction — the grade of a climb, the smell of wet tarmac, the exact moment something shifted. Time moves fluidly: past and present coexist. Short sentences for effort and tension, longer ones for open descents and reflection. Never summarizes what the reader can feel.",
        "perspective": "Writes from lived memory, not from a position of expertise. The journey is the argument. The point emerges from the experience, not the other way around.",
    },
}


def get_persona(name: str) -> dict:
    if name not in PERSONAS:
        available = ", ".join(PERSONAS.keys())
        raise ValueError(f"Unknown persona '{name}'. Available: {available}")
    return PERSONAS[name]
