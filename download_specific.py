"""
Download specific papers by title using Semantic Scholar search.
Saves PDFs to 'pdfs_specific/' folder.

Waterfall: S2 openAccessPdf → arXiv → bioRxiv → ACL → Unpaywall

Usage:
    python download_specific.py
    python download_specific.py --api-key YOUR_S2_KEY --email your@email.com
"""

import re
import time
import argparse
import requests
from pathlib import Path

PDF_FOLDER = Path("pdfs_specific")
EMAIL      = "ma007zni@gmail.com"
DELAY      = 1.0
FIELDS     = "title,authors,year,publicationDate,citationCount,externalIds,openAccessPdf"

TITLES = [
    "Do-PFN: In-Context Learning for Causal Effect Estimation",
    "CausalPFN: Amortized Causal Effect Estimation via In-Context Learning",
    "Foundation Models for Causal Inference via Prior-Data Fitted Networks",
    "FairPFN: A Tabular Foundation Model for Causal Fairness",
    "MapPFN: Learning Causal Perturbation Maps in Context",
    "Use What You Know: Causal Foundation Models with Partial Graphs",
    "Amortized Causal Discovery with Prior-Fitted Networks",
    "Integrating Causal Foundation Model in Prescriptive Maintenance Framework",
    "Position: Foundation Models for Tabular Data within Systemic Contexts Need Grounding",
]


# ── Helpers ────────────────────────────────────────────────────

def safe_name(title: str, max_len: int = 80) -> str:
    slug = re.sub(r"[^\w\s-]", "", title or "untitled")
    slug = re.sub(r"\s+", "_", slug).strip("_")
    return slug[:max_len]


def try_download(url: str, dest: Path) -> bool:
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
    if doi and doi.startswith("10.1101/"):
        return f"https://www.biorxiv.org/content/{doi}v1.full.pdf"
    return ""


def download_paper(paper: dict, dest: Path, email: str) -> tuple[bool, str]:
    oa    = (paper.get("openAccessPdf") or {}).get("url", "")
    arxiv = paper.get("externalIds", {}).get("ArXiv", "")
    acl   = paper.get("externalIds", {}).get("ACL", "")
    doi   = paper.get("externalIds", {}).get("DOI", "")

    candidates = [
        (oa,                                         "S2"),
        (f"https://arxiv.org/pdf/{arxiv}.pdf" if arxiv else "", "arXiv"),
        (biorxiv_url(doi),                           "bioRxiv"),
        (f"https://aclanthology.org/{acl}.pdf" if acl else "", "ACL"),
        (unpaywall_url(doi, email),                  "Unpaywall"),
    ]
    for url, source in candidates:
        if url and try_download(url, dest):
            return True, source
    return False, "none"


def search_paper(title: str, headers: dict) -> dict | None:
    """Search Semantic Scholar for a paper by title, return best match or None."""
    base = "https://api.semanticscholar.org/graph/v1"
    while True:
        r = requests.get(
            f"{base}/paper/search",
            params={"query": title, "fields": FIELDS, "limit": 3},
            headers=headers,
        )
        if r.status_code == 429:
            print("  Rate limited, waiting 15s..."); time.sleep(15); continue
        if r.status_code != 200:
            return None
        data = r.json().get("data", [])
        if not data:
            return None
        return data[0]


# ── Main ───────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", default="")
    parser.add_argument("--email",   default=EMAIL)
    args = parser.parse_args()

    headers = {"x-api-key": args.api_key} if args.api_key else {}
    PDF_FOLDER.mkdir(exist_ok=True)

    print(f"Searching & downloading {len(TITLES)} papers to '{PDF_FOLDER}/'\n")

    ok = fail = skip = not_found = 0
    for i, title in enumerate(TITLES, 1):
        dest = PDF_FOLDER / f"{safe_name(title)}.pdf"

        if dest.exists():
            print(f"[{i:>2}/{len(TITLES)}] ⏭  {dest.name}")
            skip += 1
            continue

        print(f"[{i:>2}/{len(TITLES)}] 🔍 {title}")
        paper = search_paper(title, headers)

        if not paper:
            print(f"           ❌ Not found on Semantic Scholar")
            not_found += 1
            continue

        found_title = paper.get("title", "")
        print(f"           → Found: {found_title}")

        success, source = download_paper(paper, dest, args.email)
        if success:
            print(f"           ✅ ({source}) saved as {dest.name}")
            ok += 1
        else:
            print(f"           🔒 No open-access PDF found")
            fail += 1

        time.sleep(DELAY)

    print(f"\n{'─'*60}")
    print(f"✅ Downloaded  : {ok}")
    print(f"🔒 No OA found : {fail}")
    print(f"❌ Not found   : {not_found}")
    print(f"⏭  Skipped    : {skip}")
    print(f"📁 Saved to    : {PDF_FOLDER.resolve()}")


if __name__ == "__main__":
    main()
