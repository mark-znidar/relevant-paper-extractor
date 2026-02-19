"""
Build a single prompt file from paper texts in 'pdfs_txt/'.

Selection logic:
  - Papers with publicationDate >= --priority_date are always included.
  - All other papers are included only if citationCount >= --citations.
  - If --priority_date is omitted, all papers need citations >= --citations.
  - If --citations is omitted it defaults to 0 (no citation filter).

Output:
  paper_prompts/<params>_<tokens>tok.txt

Usage:
    python build_prompt.py --n_words 300
    python build_prompt.py --n_words 500 --priority_date 2026-01-01
    python build_prompt.py --n_words 300 --priority_date 2025-06-01 --citations 10
"""

import re
import random
import argparse
from pathlib import Path
from datetime import date

import tiktoken

TXT_FOLDER    = Path("pdfs_txt")
OUTPUT_FOLDER = Path("paper_prompts")
SEPARATOR     = "\n\n" + "=" * 5 + "\nNEW PAPER\n" + "=" * 5 + "\n\n"
ENCODING      = "cl100k_base"   # GPT-4 / GPT-4o encoding; good Claude approximation too


# ── Filename parsing ────────────────────────────────────────────

def parse_filename(name: str) -> tuple[str, int]:
    """
    Extract (YYYYMMDD date string, citation count) from filenames like:
        2026_20260215_00042_Title_words.txt
    Returns ("00000000", 0) on parse failure.
    """
    parts = name.split("_")
    if len(parts) < 3:
        return "00000000", 0
    try:
        date_str = parts[1]          # YYYYMMDD
        citations = int(parts[2])
        return date_str, citations
    except (ValueError, IndexError):
        return "00000000", 0


def date_str_to_date(s: str) -> date:
    """Convert YYYYMMDD string to a date object; fall back to date.min."""
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except Exception:
        return date.min


# ── Core logic ──────────────────────────────────────────────────

def select_papers(
    txt_dir: Path,
    priority_date: date | None,
    min_citations: int,
) -> list[Path]:
    """Return sorted list of .txt files that pass the selection criteria."""
    selected = []
    for p in sorted(txt_dir.glob("*.txt")):
        date_str, cites = parse_filename(p.name)
        pub_date = date_str_to_date(date_str)

        if priority_date and pub_date >= priority_date:
            selected.append(p)
        elif cites >= min_citations:
            selected.append(p)

    return selected


def truncate_words(text: str, n_words: int) -> str:
    words = text.split()
    return " ".join(words[:n_words])


def build_output_name(n_words: int, priority_date: date | None, min_citations: int, tokens: int, n_papers: int, skip_pct: float) -> str:
    parts = [f"w{n_words}"]
    if priority_date:
        parts.append(f"from{priority_date.strftime('%Y%m%d')}")
    parts.append(f"cit{min_citations}")
    if skip_pct > 0:
        parts.append(f"skip{int(skip_pct)}pct")
    parts.append(f"{n_papers}papers")
    parts.append(f"{tokens}tok")
    return "_".join(parts) + ".txt"


# ── Main ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n_words",       type=int,  required=True,
                        help="Words to take from each paper")
    parser.add_argument("--priority_date", type=str,  default=None,
                        help="Auto-select papers on or after this date (YYYY-MM-DD)")
    parser.add_argument("--citations",     type=int,  default=0,
                        help="Min citation count for non-priority papers (default 0)")
    parser.add_argument("--txt-dir",        default="pdfs_txt",
                        help="Folder with .txt papers (default: pdfs_txt)")
    parser.add_argument("--skip_percentage", type=float, default=0.0,
                        help="Randomly skip this %% of selected papers (0-100)")
    args = parser.parse_args()

    txt_dir = Path(args.txt_dir)
    if not txt_dir.exists():
        print(f"Error: '{txt_dir}' not found. Run pdfs_to_txt.py first.")
        return

    priority_date = None
    if args.priority_date:
        try:
            priority_date = date.fromisoformat(args.priority_date)
        except ValueError:
            print(f"Error: --priority_date must be YYYY-MM-DD, got '{args.priority_date}'")
            return

    # Select
    papers = select_papers(txt_dir, priority_date, args.citations)
    if not papers:
        print("No papers matched the given filters.")
        return

    print(f"Selected {len(papers)} papers (priority_date={priority_date}, min_citations={args.citations})")

    # Random skip
    if args.skip_percentage > 0:
        keep_ratio = 1.0 - args.skip_percentage / 100.0
        papers = random.sample(papers, max(1, int(len(papers) * keep_ratio)))
        print(f"After {args.skip_percentage}% random skip: {len(papers)} papers remain")

    # Build combined text
    enc = tiktoken.get_encoding(ENCODING)
    chunks = []
    for p in papers:
        raw  = p.read_text(encoding="utf-8", errors="ignore")
        chunk = truncate_words(raw, args.n_words)
        chunks.append(chunk)

    combined = SEPARATOR.join(chunks)

    # Count tokens
    tokens = len(enc.encode(combined))
    print(f"Total tokens: {tokens:,}")

    # Save
    OUTPUT_FOLDER.mkdir(exist_ok=True)
    out_name = build_output_name(args.n_words, priority_date, args.citations, tokens, len(papers), args.skip_percentage)
    out_path = OUTPUT_FOLDER / out_name
    out_path.write_text(combined, encoding="utf-8")

    print(f"Saved → {out_path.resolve()}")
    print(f"  Papers  : {len(papers)}")
    print(f"  Tokens  : {tokens:,}")
    print(f"  Words/paper: {args.n_words}")


if __name__ == "__main__":
    main()
