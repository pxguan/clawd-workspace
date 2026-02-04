#!/usr/bin/env python3
"""Extract text from PDF and chunk for retrieval."""

import json
import argparse
import re
from pathlib import Path
from typing import List, Dict

try:
    import pypdf
except ImportError:
    print("Installing pypdf...")
    import subprocess
    subprocess.run(["pip", "install", "pypdf"], check=True)
    import pypdf


def extract_text_from_pdf(pdf_path: str) -> List[Dict]:
    """Extract text from PDF with page metadata."""
    chunks = []
    pdf_reader = pypdf.PdfReader(pdf_path)

    for page_num, page in enumerate(pdf_reader.pages, start=1):
        text = page.extract_text()
        if text.strip():
            chunks.append({
                "id": f"page_{page_num}",
                "text": text.strip(),
                "metadata": {
                    "source": Path(pdf_path).name,
                    "page": page_num
                }
            })

    return chunks


def chunk_text(chunks: List[Dict], chunk_size: int = 1500,
               chunk_overlap: int = 300, min_chunk_size: int = 100,
               code_aware: bool = False) -> List[Dict]:
    """Split text into smaller chunks with overlap."""
    result = []
    chunk_id = 0

    for page_chunk in chunks:
        text = page_chunk["text"]
        metadata = page_chunk["metadata"]

        if code_aware:
            # Preserve code blocks when chunking
            parts = re.split(r'(```[\s\S]*?```)', text)
        else:
            parts = [text]

        current_chunk = ""
        current_start = 0

        for part in parts:
            if part.startswith("```"):
                # Code block - try to keep it whole or split carefully
                if len(current_chunk) + len(part) > chunk_size and current_chunk:
                    # Save current chunk first
                    if len(current_chunk) >= min_chunk_size:
                        result.append({
                            "id": f"chunk_{chunk_id}",
                            "text": current_chunk.strip(),
                            "metadata": {**metadata, "chunk_start": current_start}
                        })
                        chunk_id += 1
                    current_chunk = part[chunk_overlap:] if chunk_overlap > 0 else part
                    current_start += len(current_chunk) + chunk_overlap
                else:
                    current_chunk += part
            else:
                # Regular text - split by chunk_size
                i = 0
                while i < len(part):
                    remaining = chunk_size - len(current_chunk)
                    if remaining <= 0:
                        if len(current_chunk) >= min_chunk_size:
                            result.append({
                                "id": f"chunk_{chunk_id}",
                                "text": current_chunk.strip(),
                                "metadata": {**metadata, "chunk_start": current_start}
                            })
                            chunk_id += 1
                        overlap_text = current_chunk[-chunk_overlap:] if chunk_overlap > 0 else ""
                        current_chunk = overlap_text
                        current_start += len(part[:i]) - len(overlap_text)
                        remaining = chunk_size - len(current_chunk)

                    piece = part[i:i+remaining]
                    current_chunk += piece
                    i += len(piece)

        # Don't forget the last chunk
        if len(current_chunk.strip()) >= min_chunk_size:
            result.append({
                "id": f"chunk_{chunk_id}",
                "text": current_chunk.strip(),
                "metadata": {**metadata, "chunk_start": current_start}
            })

    return result


def main():
    parser = argparse.ArgumentParser(description="Extract and chunk PDF text")
    parser.add_argument("pdf", help="Path to PDF file")
    parser.add_argument("--output", required=True, help="Output JSON file")
    parser.add_argument("--chunk-size", type=int, default=1500,
                        help="Chunk size in characters")
    parser.add_argument("--chunk-overlap", type=int, default=300,
                        help="Overlap between chunks")
    parser.add_argument("--min-chunk-size", type=int, default=100,
                        help="Minimum chunk size to keep")
    parser.add_argument("--code-aware", action="store_true",
                        help="Preserve code blocks when chunking")

    args = parser.parse_args()

    # Extract text
    print(f"Extracting text from {args.pdf}...")
    page_chunks = extract_text_from_pdf(args.pdf)
    print(f"Extracted {len(page_chunks)} pages")

    # Chunk text
    print("Chunking text...")
    chunks = chunk_text(
        page_chunks,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        min_chunk_size=args.min_chunk_size,
        code_aware=args.code_aware
    )
    print(f"Created {len(chunks)} chunks")

    # Save to JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"Saved chunks to {args.output}")


if __name__ == "__main__":
    main()
