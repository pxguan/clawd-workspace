#!/usr/bin/env python3
"""Batch process multiple PDFs into a unified knowledge base."""

import argparse
import json
import subprocess
from pathlib import Path
from typing import List, Dict


def extract_all_pdfs(pdf_dir: Path, output_dir: Path) -> List[Dict]:
    """Extract text from all PDFs in directory."""
    all_chunks = []
    extract_script = Path(__file__).parent / "extract_pdf.py"

    for pdf_path in pdf_dir.glob("*.pdf"):
        print(f"\nProcessing {pdf_path.name}...")
        chunks_file = output_dir / f"{pdf_path.stem}_chunks.json"

        subprocess.run([
            "python3", str(extract_script),
            str(pdf_path),
            "--output", str(chunks_file)
        ], check=True)

        with open(chunks_file, 'r') as f:
            chunks = json.load(f)
            all_chunks.extend(chunks)
            print(f"  Extracted {len(chunks)} chunks")

    return all_chunks


def create_unified_embeddings(chunks: List[Dict], output_dir: Path):
    """Create embeddings for all chunks."""
    chunks_file = output_dir / "all_chunks.json"
    embeddings_file = output_dir / "embeddings.json"

    # Save unified chunks
    with open(chunks_file, 'w') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    print(f"\nSaved {len(chunks)} chunks to {chunks_file}")

    # Create embeddings
    embed_script = Path(__file__).parent / "create_embeddings.py"
    subprocess.run([
        "python3", str(embed_script),
        str(chunks_file),
        "--output", str(embeddings_file)
    ], check=True)

    print(f"Created embeddings: {embeddings_file}")


def main():
    parser = argparse.ArgumentParser(description="Batch process PDFs")
    parser.add_argument("pdf_dir", help="Directory containing PDF files")
    parser.add_argument("--output", required=True, help="Output directory for knowledge base")

    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir)
    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract all PDFs
    print("Extracting text from PDFs...")
    all_chunks = extract_all_pdfs(pdf_dir, output_dir)

    # Create embeddings
    print("\nCreating embeddings...")
    create_unified_embeddings(all_chunks, output_dir)

    print(f"\n✅ Knowledge base created at {output_dir}")
    print(f"   - {len(all_chunks)} chunks")
    print(f"   - Ready to answer questions!")


if __name__ == "__main__":
    main()
