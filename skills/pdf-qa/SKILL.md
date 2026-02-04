---
name: pdf-qa
description: PDF-based customer service Q&A using RAG (Retrieval-Augmented Generation). Extracts content from PDFs, chunks text, creates embeddings, and answers questions by retrieving relevant passages. Use when the user wants to build a customer service bot or QA system that answers questions based on PDF documentation, manuals, FAQs, or knowledge bases.
---

# PDF QA - Customer Service Q&A from PDFs

Build a RAG-based customer service system that answers questions using PDF content as the knowledge source.

## Quick Start

### 1. Prepare your PDF knowledge base

Place your PDF files in a working directory:
```bash
mkdir -p /tmp/pdf-qa-kb
cp /path/to/your/manual.pdf /tmp/pdf-qa-kb/
```

### 2. Extract and chunk PDF content

```bash
scripts/extract_pdf.py /tmp/pdf-qa-kb/manual.pdf --output /tmp/pdf-qa-kb/chunks.json
```

This extracts text from the PDF and splits it into semantic chunks for retrieval.

### 3. Create embeddings (first time only)

```bash
scripts/create_embeddings.py /tmp/pdf-qa-kb/chunks.json --output /tmp/pdf-qa-kb/embeddings.json
```

Uses OpenAI embeddings to vectorize each chunk for semantic search.

### 4. Answer questions

```bash
scripts/answer_question.py "/tmp/pdf-qa-kb" "How do I reset the device?"
```

Retrieves relevant chunks and generates an answer using Claude.

## Architecture

```
PDF → Text Extraction → Chunking → Embeddings → Vector Index
                                              ↓
                     User Question → Embed → Retrieve → Claude → Answer
```

## Configuration

Create a `.env` file in your workspace:

```bash
# Required for embeddings
OPENAI_API_KEY=sk-xxx

# Required for answering (Claude)
ANTHROPIC_API_KEY=sk-ant-xxx

# Optional: Embedding model (default: text-embedding-3-small)
EMBEDDING_MODEL=text-embedding-3-small

# Optional: LLM for answers (default: claude-sonnet-4-20250514)
LLM_MODEL=claude-sonnet-4-20250514

# Optional: Number of chunks to retrieve (default: 3)
TOP_K=3
```

## Scripts Reference

See [scripts/README.md](scripts/README.md) for detailed documentation of each script.

## Advanced Usage

### Custom chunking strategies

For technical documents, you may want code-aware chunking:
```bash
scripts/extract_pdf.py manual.pdf --chunk-size 1000 --chunk-overlap 200 --code-aware
```

### Multiple PDFs

Process entire directories:
```bash
scripts/batch_process.py /path/to/pdfs/ --output /tmp/kb/
```

### Integration with Claude Code

This skill works seamlessly with Claude Code sessions. The QA function can be called directly from conversations to answer questions based on your PDF knowledge base.

## Troubleshooting

**Poor retrieval quality:**
- Increase `TOP_K` to retrieve more chunks
- Adjust chunk size - smaller chunks = more precise retrieval
- Use `--chunk-overlap` to preserve context boundaries

**Slow embedding creation:**
- Use `text-embedding-3-small` for faster processing
- Batch process multiple PDFs overnight

**Generic answers:**
- Add system prompts tailored to your domain in `.env`
- Include examples in your PDF for few-shot learning
