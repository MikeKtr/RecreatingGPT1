"""
IMS 15.6 PDF → TXT converter
Reads all PDFs from IMS_15.6_all_PDFs/ and merges them into ims15_6_docs.txt

Requirements:
    pip3 install pymupdf
"""

import re
import sys
from pathlib import Path

import pymupdf  # PyMuPDF

# ── Config ────────────────────────────────────────────────────────────────────

PDF_DIR    = Path(__file__).parent / "IMS_15.6_all_PDFs"
OUTPUT     = Path(__file__).parent / "ims15_6_docs.txt"

# ── Helpers ───────────────────────────────────────────────────────────────────

def clean(text: str) -> str:
    """Light cleanup: collapse excessive blank lines, strip trailing spaces."""
    # Remove lines that are only page numbers (lone digit(s))
    text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", text)
    # Collapse 3+ consecutive blank lines → 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Strip trailing whitespace per line
    lines = [l.rstrip() for l in text.splitlines()]
    return "\n".join(lines).strip()


def pdf_to_text(path: Path) -> str:
    """Extract full text from a PDF using PyMuPDF."""
    doc = pymupdf.open(str(path))
    pages = []
    for page in doc:
        pages.append(page.get_text("text"))
    doc.close()
    return "\n".join(pages)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    pdfs = sorted(PDF_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDF files found in {PDF_DIR}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(pdfs)} PDF(s) in {PDF_DIR}")
    print(f"Output → {OUTPUT}\n")

    total_chars = 0

    with OUTPUT.open("w", encoding="utf-8") as out:
        out.write("IBM IMS 15.6 Documentation\n")
        out.write("=" * 80 + "\n\n")

        for i, pdf_path in enumerate(pdfs, 1):
            print(f"[{i:>2}/{len(pdfs)}] {pdf_path.name} …", end=" ", flush=True)

            raw   = pdf_to_text(pdf_path)
            text  = clean(raw)
            chars = len(text)
            total_chars += chars

            title = pdf_path.stem.replace("_", " ")

            out.write(f"\n{'=' * 80}\n")
            out.write(f"PUBLICATION: {title}\n")
            out.write(f"FILE:        {pdf_path.name}\n")
            out.write(f"{'=' * 80}\n\n")
            out.write(text)
            out.write("\n")

            print(f"{chars:,} chars", flush=True)

    size_mb = OUTPUT.stat().st_size / 1_048_576
    print(f"\nDone. Total: {total_chars:,} chars → {OUTPUT.name} ({size_mb:.1f} MB)")


if __name__ == "__main__":
    main()
