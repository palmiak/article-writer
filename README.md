# Multi-Agent Content Pipeline

A multi-stage content creation pipeline using the Anthropic Agent SDK. Each stage is a standalone CLI script that reads a frontmatter markdown file as input.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=your_key_here
```

## Input Format

All scripts take a single `--input` flag pointing to a frontmatter markdown file:

```markdown
---
topic: "Why CMSs are fragmenting"
persona: maciek
slug: cms-fragmentation
aim: "Convince developers it's worth exploring alternatives to WordPress"
links:
  - https://example.com/relevant-source
---

Optional author notes or additional context go here.
```

**Required fields:** `topic`, `persona`, `slug`
**Optional fields:** `aim` (article goal), `links` (URLs to fetch during research), body text (author notes)

Templates are available in `templates/` (`article-template.md` and `journey-template.md`). Put your article input files in `articles/`.

## Full Pipeline (one command)

Run all stages end-to-end in yolo mode (no interactive prompts, edits applied automatically):

```bash
python run_all.py --input article.md
```

For journey/travel articles:

```bash
python run_all.py --input trip/article.md --journey
```

## Stage by Stage

### Stage 1: Research

```bash
python run_research.py --input article.md
```

Creates `workspace/<slug>/research.json` with a research dump and article plan. Review and edit before proceeding.

**Journey alternative** — uses GPX files, geotagged photos, and a reflection note instead of web research:

```bash
python run_journey_prep.py --input trip/article.md
```

Additional frontmatter fields for journey articles:

```yaml
gpx_files:
  - ride.gpx
photos_dir: photos/
reflection: reflection.md
```

### Stage 2: Writing

```bash
python run_writing.py --input article.md
```

Writes sections to `workspace/<slug>/draft/section_N.md`. Pauses after each section for review.

Resume from a specific section:

```bash
python run_writing.py --input article.md --start-from 3
```

### Stage 3: Editing

```bash
python run_editing.py --input article.md                   # interactive
python run_editing.py --input article.md --yolo            # fully automatic
python run_editing.py --input article.md --yolo --condense # include condenser pass
```

Four editing passes (five with `--condense`):

| Pass | What it does |
|------|-------------|
| **0 — Fact check** | Searches the web to verify every factual claim. Flags contradictions, unsourced statistics, and inaccurate event histories. |
| **1 — Section review** | Each section reviewed against the plan and research. Rejected sections are rewritten (up to 3 attempts). Approved sections with suggestions have those suggestions applied in yolo mode. |
| **2 — Transitions** | Checks flow between sections, suggests transition fixes. |
| **3 — Final assembly** | Combines all sections into `final_article.md`. |
| **4 — Humanizer** | Removes AI writing patterns, outputs `final_article_humanized.md`. |
| **5 — Condenser** _(opt-in: `--condense`)_ | Cuts filler and repetition, trims lists to the strongest examples, outputs `final_article_condensed.md`. |

## Personas

| Persona | Voice |
|---------|-------|
| `maciek` | First-person, opinionated, dry humor, calls out hype directly |
| `curious` | Inquisitive, open-minded, explores multiple angles |
| `opinionated` | Direct, confident, challenges conventional wisdom |
| `practitioner` | Practical, experience-driven, actionable advice |
| `skeptic` | Measured, analytical, questions claims critically |
| `storyteller` | Narrative-driven, vivid, suited to travel and journey articles |

## Workspace Structure

```
workspace/<slug>/
  research.json                   # Research dump + article plan
  journey_brief.md                # (journey only) GPX + photo brief
  draft/
    section_1.md
    section_2.md
    ...
  reviews/
    section_1_facts.json          # Fact-check results per section
    section_1_review.json         # Editor review per section
    ...
    transitions_review.json
    final_review.json
  final_article.md                # Assembled article
  final_article_humanized.md      # After humanizer pass
  final_article_condensed.md      # After condenser pass
```

## Standalone tools

Run just the condenser on any markdown file:

```bash
python run_condenser.py --input workspace/<slug>/final_article_humanized.md
```

Output saves alongside the input as `*_condensed.md`.

## Models Used

| Role | Model |
|------|-------|
| Research | claude-opus-4-6 (web search) |
| Writing | claude-sonnet-4-6 |
| Editing / Fact-checking | claude-sonnet-4-6 (web search for fact checker) |
| Facts summarizer | claude-haiku-4-5-20251001 |
