"""
Download papers citing TabPFN, sorted by citation count.
Filename format: YYYY_YYYYMMDD_CITATIONS_Title.pdf

Waterfall: S2 openAccessPdf → arXiv → ACL → Unpaywall

Usage:
    pip install requests
    python download_citing_papers.py
    python download_citing_papers.py --api-key YOUR_S2_KEY --email your@email.com
"""

import re
import time
import argparse
import requests
from pathlib import Path

# ── Config ─────────────────────────────────────────────────────────
PDF_FOLDER      = Path("pdfs")
DELAY           = 1.0   # seconds between downloads
PRIORITY_YEAR   = 2026  # shown first regardless of citation count

FIELDS = "title,authors,year,publicationDate,citationCount,externalIds,venue,openAccessPdf"

# ── Helpers ────────────────────────────────────────────────────────

def safe_name(title: str, max_len: int = 60) -> str:
    slug = re.sub(r"[^\w\s-]", "", title or "untitled")
    slug = re.sub(r"\s+", "_", slug).strip("_")
    return slug[:max_len]


def make_filename(paper: dict) -> str:
    year     = paper.get("year") or "0000"
    date     = (paper.get("publicationDate") or f"{year}-00-00").replace("-", "")
    cites    = paper.get("citationCount", 0)
    title    = safe_name(paper.get("title", "untitled"))
    return f"{year}_{date}_{cites:05d}_{title}.pdf"


def fetch_all_citations(paper_id: str, headers: dict) -> list[dict]:
    papers, offset, limit = [], 0, 1000
    base = "https://api.semanticscholar.org/graph/v1"
    while True:
        r = requests.get(
            f"{base}/paper/{paper_id}/citations",
            params={"fields": FIELDS, "limit": limit, "offset": offset},
            headers=headers,
        )
        if r.status_code == 429:
            print("Rate limited, waiting 15s..."); time.sleep(15); continue
        r.raise_for_status()
        data  = r.json()
        batch = data.get("data", [])
        if not batch:
            break
        for item in batch:
            papers.append(item["citingPaper"])
        total  = data.get("total", 0)
        offset += len(batch)
        print(f"  Fetched {len(papers)}/{total}...", end="\r")
        if offset >= total:
            break
        time.sleep(0.5)
    print()
    return papers


def try_download(url: str, dest: Path) -> bool:
    """Attempt download; return True if a valid PDF was saved."""
    if not url:
        return False
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        if r.status_code == 200 and r.content[:4] == b"%PDF":
            dest.write_bytes(r.content)
            return True
    except Exception:
        pass
    return False


def unpaywall_url(doi: str, email: str) -> str:
    if not doi or not email:
        return ""
    try:
        r = requests.get(
            f"https://api.unpaywall.org/v2/{doi}",
            params={"email": email}, timeout=10
        )
        if r.status_code == 200:
            best = r.json().get("best_oa_location") or {}
            return best.get("url_for_pdf") or ""
    except Exception:
        pass
    return ""


def biorxiv_url(doi: str) -> str:
    """Return a bioRxiv PDF URL if the DOI looks like a bioRxiv/medRxiv preprint."""
    if not doi:
        return ""
    if doi.startswith("10.1101/"):
        return f"https://www.biorxiv.org/content/{doi}v1.full.pdf"
    if doi.startswith("10.1101/") or "medrxiv" in doi:
        return f"https://www.medrxiv.org/content/{doi}v1.full.pdf"
    return ""


def download_paper(paper: dict, dest: Path, email: str) -> tuple[bool, str]:
    """Waterfall: S2 OA → arXiv → bioRxiv → ACL → Unpaywall. Returns (success, source)."""
    oa    = (paper.get("openAccessPdf") or {}).get("url", "")
    arxiv = paper.get("externalIds", {}).get("ArXiv", "")
    acl   = paper.get("externalIds", {}).get("ACL", "")
    doi   = paper.get("externalIds", {}).get("DOI", "")

    candidates = [
        (oa,                                        "S2"),
        (f"https://arxiv.org/pdf/{arxiv}.pdf" if arxiv else "", "arXiv"),
        (biorxiv_url(doi),                          "bioRxiv"),
        (f"https://aclanthology.org/{acl}.pdf" if acl   else "", "ACL"),
        (unpaywall_url(doi, email),                 "Unpaywall"),
    ]

    for url, source in candidates:
        if url and try_download(url, dest):
            return True, source

    return False, "none"


# ── Main ───────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Download all papers citing a given paper (identified by DOI)."
    )
    parser.add_argument("--doi",     required=True, help="DOI of the seed paper, e.g. 10.1038/s41586-024-08328-6")
    parser.add_argument("--api-key", default="")
    parser.add_argument("--email",   default="ma007zni@gmail.com", help="Your email for Unpaywall")
    parser.add_argument("--top",     type=int, default=None)
    parser.add_argument("--out-dir", default="pdfs",  help="Folder to save PDFs (default: pdfs)")
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    headers = {"x-api-key": args.api_key} if args.api_key else {}
    out_dir.mkdir(exist_ok=True)

    # Step 1: resolve paper
    base = "https://api.semanticscholar.org/graph/v1"
    r = requests.get(f"{base}/paper/DOI:{args.doi}",
                     params={"fields": "paperId,title,citationCount"}, headers=headers)
    r.raise_for_status()
    meta = r.json()
    print(f"📖 {meta['title']}")
    print(f"📊 Total citations: {meta['citationCount']}\n")

    # Step 2: fetch all citing papers
    papers = fetch_all_citations(meta["paperId"], headers)

    # Step 3: sort — priority year first, then citation count descending
    papers.sort(key=lambda p: (
        p.get("year") == PRIORITY_YEAR,
        p.get("citationCount", 0)
    ), reverse=True)

    if args.top:
        papers = papers[:args.top]

    print(f"\nDownloading {len(papers)} papers to '{out_dir}/'...\n")

    # Step 4: download
    ok = fail = skip = 0
    for i, paper in enumerate(papers, 1):
        filename = make_filename(paper)
        dest     = out_dir / filename

        if dest.exists():
            print(f"[{i:>4}/{len(papers)}] ⏭  {filename}")
            skip += 1
            continue

        success, source = download_paper(paper, dest, args.email)

        if success:
            print(f"[{i:>4}/{len(papers)}] ✅ ({source:<10}) {filename}")
            ok += 1
        else:
            print(f"[{i:>4}/{len(papers)}] 🔒 (no OA)     {filename}")
            fail += 1

        time.sleep(DELAY)

    # Step 5: summary
    print(f"\n{'─'*60}")
    print(f"✅ Downloaded : {ok}")
    print(f"🔒 No OA found: {fail}")
    print(f"⏭  Skipped   : {skip}")
    print(f"📁 Saved to   : {out_dir.resolve()}")


if __name__ == "__main__":
    main()