#!/usr/bin/env python3
"""
Enhanced PDF Extractor - Generates both RAG chunks and human-readable Markdown

This is a hybrid approach that combines:
1. RAG chunks for AI semantic retrieval (high accuracy)
2. Structured Markdown for human reference (readable)

Output structure:
├── embeddings.json      # For RAG (AI only)
├── knowledge_base/      # Human-readable Markdown
│   ├── index.md
│   ├── 装备管理平台.md
│   └── ...
"""

import json
import argparse
import re
from pathlib import Path
from typing import List, Dict

try:
    import pypdf
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "pypdf"], check=True)
    import pypdf


def extract_text_from_pdf(pdf_path: str) -> List[Dict]:
    """Extract text with page metadata."""
    chunks = []
    pdf_reader = pypdf.PdfReader(pdf_path)
    source_name = Path(pdf_path).stem

    for page_num, page in enumerate(pdf_reader.pages, start=1):
        text = page.extract_text()
        if text.strip():
            chunks.append({
                "id": f"{source_name}_page_{page_num}",
                "text": text.strip(),
                "metadata": {
                    "source": source_name,
                    "page": page_num
                }
            })

    return chunks


def detect_headers(text: str) -> List[tuple]:
    """Detect markdown-style headers (第X章, X.X.X, etc)."""
    headers = []

    # Common Chinese doc patterns
    patterns = [
        r'^第[一二三四五六七八九十\d]+章\s+.+$',  # 第X章 标题
        r'^\d+\.\d+\.\d+\s+.+$',                 # X.X.X 标题
        r'^\d+\.\s*\d*\s+.+$',                   # X. 或 X.X 标题
        r'^[一二三四五六七八九十]+[、.\s]\s*.+$',  # 一、标题
        r'^\[.+\]$',                             # [标题]
    ]

    for line in text.split('\n'):
        for pattern in patterns:
            if re.match(pattern, line.strip()):
                headers.append((line.strip(), text.index(line)))
                break

    return headers


def chunk_semantic(chunks: List[Dict], chunk_size: int = 1500,
                   overlap: int = 300) -> List[Dict]:
    """Split into semantic chunks with overlap."""
    result = []
    chunk_id = 0

    for page_chunk in chunks:
        text = page_chunk["text"]
        metadata = page_chunk["metadata"]

        # Detect headers for semantic boundaries
        headers = detect_headers(text)
        header_positions = {pos: title for title, pos in headers}

        # Prefer splitting at headers
        if len(headers) > 3:  # Has structured headers
            for i, (title, pos) in enumerate(headers):
                end_pos = headers[i+1][1] if i+1 < len(headers) else len(text)
                section_text = text[pos:end_pos].strip()

                if len(section_text) > 50:  # Skip tiny sections
                    result.append({
                        "id": f"{metadata['source']}_section_{chunk_id}",
                        "text": f"## {title}\n\n{section_text}",
                        "metadata": {
                            **metadata,
                            "section_title": title,
                            "section_index": i
                        }
                    })
                    chunk_id += 1
        else:
            # Fallback to fixed-size chunking
            current = ""
            start = 0
            while start < len(text):
                piece = text[start:start+chunk_size]
                if current:
                    result.append({
                        "id": f"{metadata['source']}_chunk_{chunk_id}",
                        "text": current.strip(),
                        "metadata": {**metadata, "char_start": start}
                    })
                    chunk_id += 1
                current = piece[-overlap:] if overlap else ""
                start += chunk_size

            if current.strip():
                result.append({
                    "id": f"{metadata['source']}_chunk_{chunk_id}",
                    "text": current.strip(),
                    "metadata": metadata
                })

    return result


def generate_markdown(chunks: List[Dict], output_dir: Path):
    """Generate human-readable Markdown files."""
    kb_dir = output_dir / "knowledge_base"
    kb_dir.mkdir(parents=True, exist_ok=True)

    # Group by source
    by_source = {}
    for chunk in chunks:
        source = chunk["metadata"]["source"]
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(chunk)

    # Write each source as a markdown file
    for source, source_chunks in by_source.items():
        # Sort by page/section
        source_chunks.sort(key=lambda x: (
            x["metadata"].get("page", 0),
            x["metadata"].get("section_index", 0)
        ))

        md_path = kb_dir / f"{source}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(f"# {source}\n\n")
            f.write(f"*Automatically extracted from PDF*\n\n---\n\n")

            for chunk in source_chunks:
                f.write(chunk["text"] + "\n\n---\n\n")

        print(f"  → {md_path.name} ({len(source_chunks)} sections)")

    # Generate index
    index_path = kb_dir / "index.md"
    with open(index_path, 'w', encoding='utf-8') as f:
        f.write("# 知识库索引\n\n")
        f.write(f"**文档数量:** {len(by_source)}\n")
        f.write(f"**总章节数:** {len(chunks)}\n\n---\n\n")

        for source in sorted(by_source.keys()):
            f.write(f"## [{source}]({source}.md)\n\n")
            # List sections
            sections = [c for c in by_source[source] if "section_title" in c["metadata"]]
            if sections:
                f.write("**章节目录:**\n")
                for s in sections[:20]:  # Limit to first 20
                    title = s["metadata"]["section_title"]
                    f.write(f"- {title}\n")
                if len(sections) > 20:
                    f.write(f"- ... 等 {len(sections)} 个章节\n")
            f.write("\n")

    print(f"  → index.md")


def main():
    parser = argparse.ArgumentParser(
        description="Extract PDF to both RAG chunks and Markdown"
    )
    parser.add_argument("pdf", help="PDF file or directory")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--chunk-size", type=int, default=1500)
    parser.add_argument("--overlap", type=int, default=300)

    args = parser.parse_args()
    output_dir = Path(args.output)

    # Collect PDFs
    pdf_path = Path(args.pdf)
    if pdf_path.is_dir():
        pdfs = list(pdf_path.glob("*.pdf"))
    else:
        pdfs = [pdf_path]

    all_chunks = []

    for pdf in pdfs:
        print(f"\n📄 Processing {pdf.name}...")
        page_chunks = extract_text_from_pdf(str(pdf))
        print(f"   Extracted {len(page_chunks)} pages")

        semantic_chunks = chunk_semantic(
            page_chunks,
            chunk_size=args.chunk_size,
            overlap=args.overlap
        )
        print(f"   Created {len(semantic_chunks)} chunks")
        all_chunks.extend(semantic_chunks)

    # Save RAG chunks
    chunks_file = output_dir / "chunks.json"
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    print(f"\n✅ Saved {len(all_chunks)} chunks to {chunks_file}")

    # Generate Markdown
    print(f"\n📝 Generating Markdown...")
    generate_markdown(all_chunks, output_dir)
    print(f"\n✅ Knowledge base: {output_dir}/knowledge_base/")


if __name__ == "__main__":
    main()
