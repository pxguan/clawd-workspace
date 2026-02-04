# RAG Implementation Guide

## How RAG Works

RAG (Retrieval-Augmented Generation) combines two powerful techniques:

1. **Retrieval**: Find relevant information from a knowledge base
2. **Generation**: Use an LLM to synthesize an answer from retrieved information

## Why RAG for Customer Service?

### Advantages over fine-tuning:
- **Up-to-date**: Just update the PDF, no retraining needed
- **Accurate**: Answers are grounded in actual documentation
- **Cost-effective**: No model training costs
- **Transparent**: Can show source pages for verification

### Ideal use cases:
- Product manuals and documentation
- FAQ knowledge bases
- Policy documents
- Technical support guides
- Legal/compliance documents

## Architecture Diagram

```
┌─────────────┐
│   PDF Docs  │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Text Extractor  │  (pypdf)
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│   Chunking      │  (Split into 1500 char chunks with overlap)
└──────┬──────────┘
       │
       ▼
┌─────────────────────┐
│  Embedding Creation │  (OpenAI text-embedding-3-small)
└──────┬──────────────┘
       │
       ▼
┌─────────────────┐
│  Vector Index   │  (JSON for simplicity, can upgrade to vector DB)
└──────┬──────────┘
       │
       ▼
┌──────────────────────────────────┐
│        Question Answering        │
│  ┌────────────────────────────┐ │
│  │ 1. Embed user question     │ │
│  │ 2. Find similar chunks     │ │
│  │ 3. Build context           │ │
│  │ 4. Ask Claude for answer   │ │
│  └────────────────────────────┘ │
└──────────────────────────────────┘
```

## Chunking Strategies

### Fixed-size chunking (default)
- Pros: Simple, predictable, good for general text
- Cons: May break at awkward spots

### Semantic chunking (advanced)
- Split by paragraphs, sections, or headings
- Preserves logical boundaries
- Better for technical docs

### Code-aware chunking
- Preserves code blocks intact
- Splits regular text between code
- Essential for programming docs

## Embedding Models

| Model | Dimensions | Cost | Speed | Best For |
|-------|-----------|------|-------|----------|
| text-embedding-3-small | 1536 | Low | Fast | General use |
| text-embedding-3-large | 3072 | Medium | Medium | Complex queries |
| text-embedding-ada-002 | 1536 | Low | Fast | Legacy |

## Improving Retrieval Quality

### 1. Hybrid Search (BM25 + Semantic)
Combine keyword search with semantic search for better results on specific terms.

### 2. Re-ranking
Retrieve more chunks (e.g., 20), then use a cross-encoder to re-rank by relevance.

### 3. Query Expansion
Rewrite user queries to be more explicit before embedding.

### 4. Metadata Filtering
Filter by source, page, or other metadata before retrieval.

## Scaling Considerations

### Small scale (< 10K chunks)
- JSON storage is fine
- Linear search is fast enough

### Medium scale (10K - 100K chunks)
- Consider SQLite with vector extension
- Or FAISS for faster search

### Large scale (> 100K chunks)
- Dedicated vector database (Pinecone, Weaviate, Milvus)
- Approximate nearest neighbor (ANN) search

## Common Pitfalls

### 1. Chunks too small
- Problem: Missing context
- Solution: Increase chunk size or overlap

### 2. Chunks too large
- Problem: Noisy retrieval, less precise
- Solution: Decrease chunk size

### 3. Missing overlap
- Problem: Relevant info split between chunks
- Solution: Add 10-20% overlap

### 4. Ignoring metadata
- Problem: Can't verify sources
- Solution: Always preserve and display metadata
