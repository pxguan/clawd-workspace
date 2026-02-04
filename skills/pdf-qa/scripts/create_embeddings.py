#!/usr/bin/env python3
"""Create embeddings for text chunks using OpenAI API."""

import json
import argparse
import os
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("Installing openai...")
    import subprocess
    subprocess.run(["pip", "install", "openai"], check=True)
    from openai import OpenAI


def load_chunks(chunks_path: str) -> list:
    """Load chunks from JSON file."""
    with open(chunks_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_embeddings(chunks: list, model: str = "text-embedding-3-small") -> list:
    """Create embeddings for all chunks."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    client = OpenAI(api_key=api_key)

    result = []
    batch_size = 100

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        texts = [chunk["text"] for chunk in batch]

        print(f"Creating embeddings for chunks {i+1}-{i+len(batch)}...")

        response = client.embeddings.create(
            input=texts,
            model=model
        )

        for chunk, embedding in zip(batch, response.data):
            result.append({
                "id": chunk["id"],
                "text": chunk["text"],
                "embedding": embedding.embedding,
                "metadata": chunk.get("metadata", {})
            })

    return result


def main():
    parser = argparse.ArgumentParser(description="Create embeddings for chunks")
    parser.add_argument("chunks", help="Path to chunks JSON file")
    parser.add_argument("--output", required=True, help="Output JSON file")
    parser.add_argument("--model", default="text-embedding-3-small",
                        help="Embedding model to use")

    args = parser.parse_args()

    # Load chunks
    print(f"Loading chunks from {args.chunks}...")
    chunks = load_chunks(args.chunks)
    print(f"Loaded {len(chunks)} chunks")

    # Create embeddings
    print("Creating embeddings...")
    chunks_with_embeddings = create_embeddings(chunks, model=args.model)
    print(f"Created {len(chunks_with_embeddings)} embeddings")

    # Save to JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks_with_embeddings, f, ensure_ascii=False, indent=2)

    print(f"Saved embeddings to {args.output}")


if __name__ == "__main__":
    main()
