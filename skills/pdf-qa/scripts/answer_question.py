#!/usr/bin/env python3
"""Answer questions using RAG retrieval from PDF knowledge base."""

import json
import argparse
import os
from pathlib import Path
from typing import List, Dict

try:
    from openai import OpenAI
    from anthropic import Anthropic
    import numpy as np
except ImportError as e:
    print(f"Installing missing dependencies...")
    import subprocess
    subprocess.run(["pip", "install", "openai", "anthropic", "numpy"], check=True)
    from openai import OpenAI
    from anthropic import Anthropic
    import numpy as np


def load_embeddings(kb_dir: str) -> List[Dict]:
    """Load embeddings from knowledge base directory."""
    embeddings_path = Path(kb_dir) / "embeddings.json"
    with open(embeddings_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate cosine similarity between two vectors."""
    a_array = np.array(a)
    b_array = np.array(b)
    return np.dot(a_array, b_array) / (np.linalg.norm(a_array) * np.linalg.norm(b_array))


def retrieve_chunks(question: str, chunks: List[Dict], top_k: int = 3) -> List[Dict]:
    """Retrieve most relevant chunks for the question."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    client = OpenAI(api_key=api_key)

    # Create embedding for question
    print("Creating embedding for question...")
    response = client.embeddings.create(
        input=[question],
        model="text-embedding-3-small"
    )
    question_embedding = response.data[0].embedding

    # Calculate similarities
    print("Retrieving relevant chunks...")
    for chunk in chunks:
        chunk["score"] = cosine_similarity(question_embedding, chunk["embedding"])

    # Sort by score and return top_k
    chunks.sort(key=lambda x: x["score"], reverse=True)
    return chunks[:top_k]


def generate_answer(question: str, chunks: List[Dict], model: str = "claude-sonnet-4-20250514") -> str:
    """Generate answer using Claude based on retrieved chunks."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable not set")

    client = Anthropic(api_key=api_key)

    # Build context from chunks
    context = "\n\n---\n\n".join([
        f"[Source: {c['metadata'].get('source', 'unknown')}, "
        f"Page: {c['metadata'].get('page', 'unknown')}]\n{c['text']}"
        for c in chunks
    ])

    prompt = f"""You are a helpful customer service assistant. Answer the user's question based on the provided context from the product documentation.

Context:
{context}

Question: {question}

Answer:"""

    print("Generating answer...")
    response = client.messages.create(
        model=model,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}]
    )

    return response.content[0].text


def main():
    parser = argparse.ArgumentParser(description="Answer question using RAG")
    parser.add_argument("kb_dir", help="Knowledge base directory with embeddings.json")
    parser.add_argument("question", help="Question to answer")
    parser.add_argument("--top-k", type=int, default=3,
                        help="Number of chunks to retrieve")
    parser.add_argument("--model", default="claude-sonnet-4-20250514",
                        help="Claude model to use")
    parser.add_argument("--show-sources", action="store_true",
                        help="Show source chunks used")

    args = parser.parse_args()

    # Load embeddings
    print(f"Loading knowledge base from {args.kb_dir}...")
    chunks = load_embeddings(args.kb_dir)
    print(f"Loaded {len(chunks)} chunks")

    # Retrieve relevant chunks
    retrieved = retrieve_chunks(args.question, chunks, top_k=args.top_k)

    # Show sources if requested
    if args.show_sources:
        print("\n=== Retrieved Chunks ===")
        for i, chunk in enumerate(retrieved, 1):
            print(f"\n[{i}] Score: {chunk['score']:.4f}")
            print(f"Source: {chunk['metadata'].get('source', 'unknown')}, "
                  f"Page: {chunk['metadata'].get('page', 'unknown')}")
            print(f"Text: {chunk['text'][:200]}...")

    # Generate answer
    print("\n=== Answer ===")
    answer = generate_answer(args.question, retrieved, model=args.model)
    print(answer)


if __name__ == "__main__":
    main()
