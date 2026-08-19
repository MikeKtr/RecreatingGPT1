"""
IMS 15.6 docs TXT cleaner — final edition
Strategy:
  1. Split into per-publication chunks (by PUBLICATION: marker).
  2. For each publication, drop everything before the first real content
     paragraph (i.e., skip the title page + TOC).
  3. Apply line-level noise removal (page nums, legal, separators).
  4. Merge and write.

Input:  ims15_6_docs.txt
Output: ims15_6_clean.txt
"""

import re
from pathlib import Path

INPUT  = Path(__file__).parent / "ims15_6_docs.txt"
OUTPUT = Path(__file__).parent / "ims15_6_clean.txt"

# ── Split marker ─────────────────────────────────────────────────────────────

RE_PUB_HDR = re.compile(
    r'^={10,}\s*\nPUBLICATION:\s*(.+?)\nFILE:\s*(.+?)\n={10,}',
    re.MULTILINE,
)

# ── TOC detection ─────────────────────────────────────────────────────────────
# A TOC block starts right after the cover page.
# We detect the end of TOC as: the first paragraph of ≥3 consecutive
# non-empty lines that do NOT match a TOC entry pattern.

RE_TOC_ENTRY = re.compile(
    r'(?:'
    r'\.{4,}'                           # dot leader
    r'|^\s*Chapter\s+\d'                # "Chapter N."
    r'|^\s*Part\s+\d'                   # "Part N."
    r'|^\s*Appendix'                    # Appendix
    r'|\s{3,}\d{1,4}\s*$'              # trailing page number
    r')',
)

# Lines that are purely cover / title page noise (drop before TOC too)
RE_COVER_NOISE = re.compile(
    r'^\s*('
    r'IMS\s*$'
    r'|15\.\d[\.\d]*\s*$'
    r'|\(\d{4}-\d{2}-\d{2} edition\)'
    r'|IBM\s*$'
    r'|Contents\s*$'
    r')\s*$',
    re.IGNORECASE,
)

# ── Line-level noise ─────────────────────────────────────────────────────────

RE_PAGE_NUM  = re.compile(r'^\s*(?:\d{1,4}|[ivxlcdmIVXLCDM]{1,8})\s*$', re.I)
RE_SEPARATOR = re.compile(r'^[=\-]{8,}\s*$')
RE_META      = re.compile(r'^\s*(PUBLICATION:|FILE:\s+IMS_|IBM IMS 15\.6)\s*', re.I)
RE_LEGAL     = re.compile(
    r'^\s*(©\s*Copyright|US Government Users|GSA ADP Schedule'
    r'|IBM Corp\.|© Copyright IBM|\d{4}-\d{2}-\d{2} edition)\s*',
    re.I,
)

# Boilerplate section headings — entire section is dropped
BOILERPLATE_HEADINGS = re.compile(
    r'^\s*('
    r'How to read syntax diagrams'
    r'|Accessibility features for IMS'
    r'|How to send your comments'
    r'|Notices'
    r'|Trademarks'
    r'|Terms and conditions for product documentation'
    r'|IBM Online Privacy Statement'
    r')\s*$',
    re.I,
)
# Heading pattern to end a boilerplate skip block
RE_ANY_HEADING = re.compile(r'^[A-Z][A-Za-z0-9 ,\'\-]{10,}$')


# Running page headers (top of page): "Chapter N. Some title  <page_num>"
RE_RUNNING_HEADER = re.compile(
    r'^(Chapter\s+\d+\.|Part\s+\d+\.|Appendix\s+[A-Z]\.)\s+.{5,}\s{2,}\d{1,4}\s*$',
    re.IGNORECASE,
)

# Running footers (bottom of page): "<page_num>  IMS: Publication Name"
# e.g. "2  IMS: Application Programming"  or  "40  IMS: Application Programming"
RE_RUNNING_FOOTER = re.compile(
    r'^\d{1,4}\s{2,}IMS:\s+\S',
    re.IGNORECASE,
)

# Also catch "IMS: Publication Name  <page_num>" variant
RE_RUNNING_HEADER2 = re.compile(
    r'^IMS:\s+.{5,}\s{2,}\d{1,4}\s*$',
    re.IGNORECASE,
)


def is_noise_line(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if RE_SEPARATOR.match(s): return True
    if RE_META.match(s):      return True
    if RE_LEGAL.match(s):     return True
    if RE_PAGE_NUM.match(s):  return True
    if RE_COVER_NOISE.match(s): return True
    if RE_RUNNING_HEADER.match(s): return True
    if RE_RUNNING_HEADER2.match(s): return True
    if RE_RUNNING_FOOTER.match(s): return True
    return False


# ── TOC / cover skip ──────────────────────────────────────────────────────────

# Chapter/Part heading pattern
RE_CHAPTER_HEADING = re.compile(
    r'^\s*(Chapter\s+\d+\.\s+\S|Part\s+\d+\.\s+\S|Appendix\s+[A-Z]\.\s+\S)',
    re.IGNORECASE,
)


def skip_front_matter(text: str) -> str:
    """
    Drop cover page, TOC and all pre-chapter boilerplate.

    The TOC contains lines like:
        "Chapter 1. Designing an application........ 3"
    Real chapter headings look like:
        "Chapter 1. Designing an application: Introductory concepts"
    followed by actual paragraph text (no trailing dots/page numbers).

    Strategy: find the first Chapter/Part heading where the NEXT non-empty
    line is NOT a TOC entry (dots / trailing number).
    """
    lines = text.splitlines()
    n = len(lines)

    for i, line in enumerate(lines):
        if not RE_CHAPTER_HEADING.match(line.strip()):
            continue
        # Look ahead: find the next non-empty line
        for j in range(i + 1, min(i + 6, n)):
            next_line = lines[j].strip()
            if not next_line:
                continue
            # If next non-empty line has dot-leaders or trailing page number → TOC
            if RE_TOC_ENTRY.search(next_line):
                break
            # Otherwise this is real content
            return "\n".join(lines[i:])

    # Fallback: return everything
    return text


def drop_boilerplate_sections(lines: list[str]) -> list[str]:
    """Remove boilerplate sections (Notices, How to read syntax diagrams…)."""
    result = []
    skipping = False
    depth = 0

    for line in lines:
        s = line.strip()
        if not skipping:
            if BOILERPLATE_HEADINGS.match(s):
                skipping = True
                depth = 0
            else:
                result.append(line)
        else:
            depth += 1
            if depth > 3 and s and RE_ANY_HEADING.match(s) and not is_noise_line(line):
                skipping = False
                result.append(line)

    return result


# ── Main ──────────────────────────────────────────────────────────────────────

def split_publications(text: str) -> list[tuple[str, str]]:
    """Return list of (title, body) for each publication."""
    parts = RE_PUB_HDR.split(text)
    # parts[0] is content before first publication (global header) → discard
    # then groups of (title, file, body) repeat
    publications = []
    for i in range(1, len(parts), 3):
        title = parts[i].strip()
        # file  = parts[i+1]  (not needed)
        body  = parts[i+2] if i + 2 < len(parts) else ""
        publications.append((title, body))
    return publications


def clean_publication(title: str, body: str) -> str:
    # Step 1: skip cover + TOC
    body = skip_front_matter(body)

    # Step 2: line-level noise removal
    lines = body.splitlines()
    lines = [l for l in lines if not is_noise_line(l)]

    # Step 3: drop boilerplate sections
    lines = drop_boilerplate_sections(lines)

    result = "\n".join(l.rstrip() for l in lines)
    result = re.sub(r'\n{3,}', '\n\n', result)
    return result.strip()


def main() -> None:
    print(f"Reading {INPUT} …")
    raw = INPUT.read_text(encoding="utf-8")
    raw = raw.replace('\xa0', ' ').replace('\u200b', '').replace('\ufeff', '')

    print("Splitting publications …")
    pubs = split_publications(raw)
    print(f"  Found {len(pubs)} publications")

    chunks = []
    for title, body in pubs:
        print(f"  Cleaning: {title[:70]} …", end=" ", flush=True)
        cleaned = clean_publication(title, body)
        chunks.append(f"{'=' * 60}\n{title}\n{'=' * 60}\n\n{cleaned}")
        print(f"{len(cleaned):,} chars")

    full = "\n\n".join(chunks)
    full = re.sub(r'\n{3,}', '\n\n', full)

    OUTPUT.write_text(full, encoding="utf-8")

    in_mb  = INPUT.stat().st_size  / 1_048_576
    out_mb = OUTPUT.stat().st_size / 1_048_576
    reduction = 100 * (1 - out_mb / in_mb)

    print(f"\nDone.")
    print(f"  Input:  {in_mb:.1f} MB  ({raw.count(chr(10)):,} lines)")
    print(f"  Output: {out_mb:.1f} MB  ({full.count(chr(10)):,} lines)  —  {reduction:.1f}% smaller")
    print(f"  Saved → {OUTPUT}")

    print("\n── First 40 non-empty lines of output ──")
    count = 0
    for line in full.splitlines():
        if line.strip():
            print(f"  {line[:120]}")
            count += 1
            if count >= 40:
                break


if __name__ == "__main__":
    main()
