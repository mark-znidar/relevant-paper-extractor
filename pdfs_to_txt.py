"""
Convert all PDFs in the 'pdfs/' folder to plain text using PyMuPDF.
Output goes to 'pdfs_txt/' with the same filename but .txt extension.

Usage:
    pip install pymupdf
    python pdfs_to_txt.py
    python pdfs_to_txt.py --pdf-dir pdfs --txt-dir pdfs_txt
"""

import argparse
from pathlib import Path

import fitz  # pymupdf


def pdf_to_text(pdf_path: Path) -> str:
    doc = fitz.open(pdf_path)
    pages = []
    for page in doc:
        pages.append(page.get_text())
    doc.close()
    return "\n".join(pages)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pdf-dir", default="pdfs",     help="Folder containing PDFs")
    parser.add_argument("--txt-dir", default="pdfs_txt", help="Folder to write .txt files")
    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir)
    txt_dir = Path(args.txt_dir)
    txt_dir.mkdir(exist_ok=True)

    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in '{pdf_dir}/'.")
        return

    print(f"Converting {len(pdfs)} PDFs from '{pdf_dir}/' → '{txt_dir}/'\n")

    ok = fail = skip = 0
    for i, pdf_path in enumerate(pdfs, 1):
        txt_path = txt_dir / (pdf_path.stem + ".txt")

        if txt_path.exists():
            print(f"[{i:>4}/{len(pdfs)}] ⏭  {txt_path.name}")
            skip += 1
            continue

        try:
            text = pdf_to_text(pdf_path)
            txt_path.write_text(text, encoding="utf-8")
            print(f"[{i:>4}/{len(pdfs)}] ✅  {txt_path.name}")
            ok += 1
        except Exception as e:
            print(f"[{i:>4}/{len(pdfs)}] ❌  {pdf_path.name}  ({e})")
            fail += 1

    print(f"\n{'─'*60}")
    print(f"✅ Converted : {ok}")
    print(f"❌ Failed    : {fail}")
    print(f"⏭  Skipped  : {skip}")
    print(f"📁 Saved to  : {txt_dir.resolve()}")


if __name__ == "__main__":
    main()
