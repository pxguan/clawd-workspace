# PDF QA Scripts

## extract_pdf.py

Extracts text from PDF files and splits it into chunks for retrieval.

```bash
python3 extract_pdf.py <pdf_path> --output <chunks_json> [options]
```

**Options:**
- `--chunk-size`: Size of each chunk in characters (default: 1500)
- `--chunk-overlap`: Overlap between chunks (default: 300)
- `--code-aware`: Preserve code blocks when chunking
- `--min-chunk-size`: Minimum chunk size to keep (default: 100)

**Output:** JSON file with array of chunks:
```json
[
  {
    "id": "chunk_0",
    "text": "...",
    "metadata": {"source": "manual.pdf", "page": 1}
  }
]
```

## create_embeddings.py

Creates vector embeddings for text chunks using OpenAI API.

```bash
python3 create_embeddings.py <chunks_json> --output <embeddings_json>
```

**Output:** JSON file with embeddings:
```json
[
  {
    "id": "chunk_0",
    "text": "...",
    "embedding": [0.1, 0.2, ...],
    "metadata": {...}
  }
]
```

## answer_question.py

Answers a question by retrieving relevant chunks and generating an answer.

```bash
python3 answer_question.py <kb_directory> "<question>"
```

The `<kb_directory>` should contain:
- `embeddings.json`: Vector embeddings
- `chunks.json`: Original text chunks (optional, merged in embeddings.json)

**Options:**
- `--top-k`: Number of chunks to retrieve (default: 3)
- `--model`: Claude model to use (default: claude-sonnet-4-20250514)

## batch_process.py

Process multiple PDFs in a directory.

```bash
python3 batch_process.py <pdf_directory> --output <kb_directory>
```

Creates a unified knowledge base from all PDFs.
