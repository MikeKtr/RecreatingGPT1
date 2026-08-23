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
import unicodedata
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


def clean_unicode_and_normalize(s: str) -> str:
    """Normalize unicode and convert non-ASCII noise into clean printable ASCII."""
    # Step 1: NFKC normalization (expands ligatures ﬀ -> ff, superscripts ¹ -> 1, etc.)
    s = unicodedata.normalize('NFKC', s)

    # Step 2: Explicit symbol & punctuation mapping
    mapping = {
        # Spaces & hidden formatting
        '\u2009': ' ', '\u2008': ' ', '\u2007': ' ', '\u2006': ' ', '\u2005': ' ',
        '\u2004': ' ', '\u2003': ' ', '\u2002': ' ', '\u2000': ' ', '\u2001': ' ',
        '\xa0': ' ', '\u200b': '', '\ufeff': '', '\u200e': '', '\u200f': '',

        # Smart quotes & apostrophes
        '‘': "'", '’': "'", '‚': "'", '‛': "'",
        '“': '"', '”': '"', '„': '"', '‟': '"',

        # Hyphens & Dashes
        '–': '-', '—': '-', '−': '-', '‐': '-',

        # Ellipses, Slashes & Arrows
        '…': '...', '⋮': '...', '⁄': '/', '→': '->', '←': '<-',

        # Math & Symbols
        '≤': '<=', '≥': '>=', '≠': '!=', '±': '+/-', '×': '*', '÷': '/',
        '►': '>', '◄': '<', '•': '-', '─': '-', '│': '|', '¦': '|',
        '¬': 'NOT', '¢': 'c', '·': '.', 'Ø': 'O', 'ß': 'ss',
        'ç': 'c', 'í': 'i', 'ÿ': 'y', 'Œ': 'OE', 'μ': 'u',

        # PDF font extraction homoglyphs (Cyrillic/Greek glitches)
        'Β': 'B', 'В': 'B', 'Е': 'E', 'Р': 'R', 'С': 'C', 'х': 'x', ';': ';',

        # IBM diagram symbols
        '␢': ' ', '␠': ' ', '␣': ' ',

        # Legal
        '©': '(C)', '®': '(R)', '™': '(TM)',
    }

    for k, v in mapping.items():
        s = s.replace(k, v)

    # NFD decomposition to remove any floating non-spacing mark (accents)
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = unicodedata.normalize('NFC', s)

    # Keep newline and standard printable ASCII chars (32..126)
    cleaned_chars = []
    for c in s:
        if c == '\n' or (32 <= ord(c) <= 126):
            cleaned_chars.append(c)
        else:
            ascii_c = c.encode('ascii', 'ignore').decode('ascii')
            if ascii_c:
                cleaned_chars.append(ascii_c)

    return ''.join(cleaned_chars)


def clean_publication(title: str, body: str) -> str:
    # Step 0: Unicode normalization & character sanitization
    body = clean_unicode_and_normalize(body)

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


PDF_DIR = Path(__file__).parent / "IMS_15.6_all_PDFs"


def convert_pdfs_if_needed() -> None:
    """If ims15_6_docs.txt does not exist, extract text from PDFs in IMS_15.6_all_PDFs/."""
    if INPUT.exists():
        return

    if not PDF_DIR.exists():
        raise FileNotFoundError(f"Neither {INPUT.name} nor directory {PDF_DIR.name} exists!")

    try:
        import pymupdf
    except ImportError:
        raise ImportError("pymupdf is required to extract text from PDFs. Run 'pip install pymupdf'.")

    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"No PDF files found in {PDF_DIR}")

    print(f"[{INPUT.name} not found. Converting {len(pdfs)} PDFs from {PDF_DIR.name} ...]")
    with INPUT.open("w", encoding="utf-8") as out:
        out.write("IBM IMS 15.6 Documentation\n")
        out.write("=" * 80 + "\n\n")

        for i, pdf_path in enumerate(pdfs, 1):
            print(f"  [{i:>2}/{len(pdfs)}] {pdf_path.name} …", flush=True)
            doc = pymupdf.open(str(pdf_path))
            pages = [page.get_text("text") for page in doc]
            doc.close()

            raw_text = "\n".join(pages)
            raw_text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", raw_text)
            raw_text = re.sub(r"\n{3,}", "\n\n", raw_text)
            lines = [l.rstrip() for l in raw_text.splitlines()]
            text = "\n".join(lines).strip()

            title = pdf_path.stem.replace("_", " ")
            out.write(f"\n{'=' * 80}\n")
            out.write(f"PUBLICATION: {title}\n")
            out.write(f"FILE:        {pdf_path.name}\n")
            out.write(f"{'=' * 80}\n\n")
            out.write(text)
            out.write("\n")

    print(f"Created {INPUT.name} ({INPUT.stat().st_size / 1_048_576:.1f} MB)\n")


def main() -> None:
    convert_pdfs_if_needed()
    print(f"Reading {INPUT} …")
    raw = INPUT.read_text(encoding="utf-8")
    raw = clean_unicode_and_normalize(raw)

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
