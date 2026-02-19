# Relevant Paper Extractor

A set of scripts to download, convert, and package all papers citing any paper (identified by DOI) into LLM-ready prompt files.

---

## Pipeline Overview

```
download_papers.py → pdfs_to_txt.py → build_prompt.py
```

---

## Scripts

### 1. `download_papers.py`
Downloads all papers citing a given paper (by DOI) from Semantic Scholar, sorted by recency and citation count.

- Tries multiple sources in order: **S2 OA → arXiv → bioRxiv → ACL → Unpaywall**
- Skips already-downloaded files (safe to re-run)
- Saves PDFs to `pdfs/` (or `--out-dir`) with filename format: `YYYY_YYYYMMDD_CCCCC_Title.pdf`

```bash
# TabPFN Nature paper
python download_papers.py --doi 10.1038/s41586-024-08328-6

# Any other paper
python download_papers.py --doi 10.1145/3292500.3330701

# With options
python download_papers.py --doi 10.1038/s41586-024-08328-6 --api-key YOUR_S2_KEY --top 50 --out-dir my_pdfs
```

---

### 2. `pdfs_to_txt.py`
Converts all PDFs in `pdfs/` to plain text using PyMuPDF.

- Saves `.txt` files to `pdfs_txt/` with the same filename
- Skips already-converted files

```bash
python pdfs_to_txt.py
```

---

### 3. `build_prompt.py`
Builds a single combined prompt file from the converted texts, with filtering and word limits.

**Arguments:**
| Argument | Description |
|---|---|
| `--n_words` | Words to take from each paper (required) |
| `--priority_date` | Papers on/after this date are always included (YYYY-MM-DD) |
| `--citations` | Min citations for non-priority papers (default: 0) |
| `--skip_percentage` | Randomly skip this % of selected papers (default: 0) |

Output is saved to `paper_prompts/` with a descriptive filename including token count.

```bash
python build_prompt.py --n_words 2350 --priority_date 2025-11-05 --citations 1
python build_prompt.py --n_words 2350 --priority_date 2025-11-05 --citations 1 --skip_percentage 10
```

**Example output filename:**
```
w2350_from20251105_cit1_276papers_993847tok.txt
```

---

### 4. `run_grid.sh`
Runs `build_prompt.py` over a full grid of parameter combinations.

```bash
zsh run_grid.sh
# Or to prevent sleep:
caffeinate -i zsh run_grid.sh
```

---

### 5. `download_specific.py`
Downloads a specific hardcoded list of papers by title via Semantic Scholar search.
Saves PDFs to `pdfs_specific/`.

```bash
python download_specific.py
```

---

## Installation

```bash
conda create -n paper-pipeline python=3.11
conda activate paper-pipeline
pip install requests pymupdf tiktoken
```

---

## Token Count Reference

| Model | Context Window | Notes |
|---|---|---|
| Claude 3.5 Sonnet | 200k | Very selective params needed |
| Gemini 1.5 Pro | 1M | Good coverage with ~276 papers @ 2350 words |
| Gemini 2.0 | 2M | Fits most combinations |

---

## Folder Structure

```
tabpfn-citation-pipeline/
├── download_papers.py      # Step 1: download PDFs
├── pdfs_to_txt.py          # Step 2: convert to text
├── build_prompt.py         # Step 3: build prompt file
├── run_grid.sh             # Step 3b: grid search over params
├── download_specific.py    # Download specific papers by title
└── README.md
```

Generated folders (not tracked in git):
```
pdfs/                       # Downloaded PDFs
pdfs_txt/                   # Converted text files
pdfs_specific/              # Specific downloaded PDFs
paper_prompts/              # Generated prompt files
```
