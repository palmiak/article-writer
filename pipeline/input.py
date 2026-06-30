"""Parse frontmatter markdown input files for the article pipeline."""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ArticleInput:
    topic: str
    persona: str
    slug: str
    aim: str = ""
    links: list[str] = field(default_factory=list)
    notes: str = ""           # markdown body after frontmatter
    # Journey-specific optional fields
    gpx_files: list[str] = field(default_factory=list)
    reflection: str = ""      # path to a reflection/motivation markdown file
    photos_dir: str = ""      # path to directory of geotagged photos
    base_dir: Path = field(default_factory=Path)  # directory of the input file


def parse_input_file(path: str | Path) -> ArticleInput:
    path = Path(path).resolve()
    text = path.read_text()

    match = re.match(r"^---\n(.*?)\n---\n?(.*)", text, re.DOTALL)
    if not match:
        raise ValueError(f"No valid YAML frontmatter found in {path}")

    fm_text = match.group(1)
    body = match.group(2).strip()

    fm = _parse_yaml(fm_text)

    topic = fm.get("topic", "").strip()
    persona = fm.get("persona", "").strip()
    slug = fm.get("slug", "").strip()

    if not topic:
        raise ValueError("Frontmatter must include 'topic'")
    if not persona:
        raise ValueError("Frontmatter must include 'persona'")
    if not slug:
        raise ValueError("Frontmatter must include 'slug'")

    return ArticleInput(
        topic=topic,
        persona=persona,
        slug=slug,
        aim=fm.get("aim", "").strip() if isinstance(fm.get("aim"), str) else "",
        links=fm.get("links", []),
        notes=body,
        gpx_files=fm.get("gpx_files", []),
        reflection=fm.get("reflection", "").strip() if isinstance(fm.get("reflection"), str) else "",
        photos_dir=fm.get("photos_dir", "").strip() if isinstance(fm.get("photos_dir"), str) else "",
        base_dir=path.parent,
    )


def _parse_yaml(text: str) -> dict:
    """Minimal YAML parser for frontmatter. Handles strings and string lists."""
    result = {}
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        m = re.match(r"^(\w+):\s*(.*)", line)
        if m:
            key = m.group(1)
            val = m.group(2).strip()
            if val == "":
                # Collect list items on the following indented lines
                items = []
                i += 1
                while i < len(lines) and re.match(r"^\s*-\s+", lines[i]):
                    items.append(re.sub(r"^\s*-\s+", "", lines[i]).strip().strip("\"'"))
                    i += 1
                result[key] = items
                continue
            else:
                result[key] = val.strip("\"'")
        i += 1
    return result
