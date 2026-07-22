# Chunking in RAG

## Why Do We Need Chunking?

Large Language Models (LLMs) have a limited context window and cannot process an entire document efficiently.

Instead of embedding an entire document, we split it into smaller chunks. Each chunk is embedded separately, allowing retrieval of only the most relevant information during querying.

Chunking is not just about splitting text—it is about optimizing embedding quality and retrieval accuracy.

---

## Types of Chunking Strategies

### 1. Character Text Splitter

#### Definition

Splits text after a fixed number of characters.

#### Working

- Splits purely based on character count.
- Uses:
  - `chunk_size`
  - `chunk_overlap`

Example

```text
Chunk 1: 1000 chars
Chunk 2: Next 1000 chars (with overlap)
```

#### Advantages

- Very simple
- Fast

#### Disadvantages

- Can break words or sentences.
- Produces unnatural chunks.

#### Best Use Case

Simple documents where structure is not important.

---

### 2. Token Text Splitter

#### Definition

Splits text based on tokens instead of characters.

#### Working

Instead of

```text
1000 characters
```

it uses

```text
500 tokens
```

Since LLMs process tokens rather than characters, this approach is usually more accurate.

#### Advantages

- Respects model context limits.
- More accurate than character splitting.

#### Disadvantages

- Still ignores sentence and paragraph boundaries.

---

### 3. Recursive Character Text Splitter ⭐ Recommended

#### Definition

Attempts to split text intelligently using multiple separators before falling back to character limits.

#### Working

```text
Paragraph (\n\n)
      ↓
Line (\n)
      ↓
Space (" ")
      ↓
Character
```

If a paragraph exceeds the chunk size, it recursively tries the next separator.

Still uses:

- `chunk_size`
- `chunk_overlap`

#### Advantages

- Preserves paragraphs.
- Preserves sentences.
- Produces natural chunks.
- Default choice for most RAG applications.

#### Best Use Case

General-purpose RAG systems.

---

### 4. Document-Specific Splitters

#### Definition

Specialized splitters for structured documents.

Examples

- MarkdownTextSplitter
- HTMLTextSplitter
- JSONSplitter
- CodeTextSplitter
- Language-specific splitters (Python, Java, JS, etc.)

#### Why?

They preserve the natural document structure.

Instead of splitting inside a Java method, they split around:

- Classes
- Methods
- Functions

---

### 5. Semantic Chunking ⭐⭐⭐

#### Definition

Splits text based on semantic meaning instead of size.

#### Working

1. Convert sentences into embeddings.
2. Compare neighboring sentence embeddings.
3. Split whenever similarity falls below a threshold.

Example

```text
Sentence A
Sentence B
Sentence C

Similarity(A,B) = High
Similarity(B,C) = Low

↓

Split before Sentence C
```

LangChain commonly uses

```python
breakpoint_threshold_type="percentile"
```
Where differences between sentence embeddings are calculated, and chunks are split when the difference exceeds a chosen percentile threshold.

#### Advantages

- Produces meaningful chunks.
- Better retrieval quality.

#### Disadvantages

- Slower
- More expensive (requires embeddings during chunking)

---

### 6. Agentic Chunking

Uses an LLM to determine chunk boundaries.

#### Proposition-Based Chunking

---
The LLM converts text into independent factual propositions.

Example

Original paragraph

↓

```
Fact 1

Fact 2

Fact 3
```

Each chunk is meaningful on its own.

Example models

- GPT-3.5
- GPT-4
- Claude

#### Grouping Similar Propositions

---
After generating propositions,

another LLM groups related propositions into larger meaningful chunks.

Flow

```
Document

↓

Facts

↓

Group Related Facts

↓

Final Chunks
```

This often produces the highest quality chunks but is computationally expensive.

### 7. Parent Document Retriever ⭐⭐⭐

#### Problem

Small chunks improve retrieval but lose context.

Large chunks preserve context but reduce embedding quality.

Parent Document Retriever solves both.

#### Working

```text
Large Parent Document
        ↓
Child Chunks
        ↓
Embeddings
        ↓
Similarity Search
        ↓
Return Parent Document
```
The LLM ultimately receives the larger parent document, preserving context.

#### Advantages

- Better retrieval accuracy
- Richer context
- Production-ready approach

---

## Comparison

| Strategy | Preserves Meaning | Speed | Best Use Case |
|-----------|------------------|-------|---------------|
| Character | ❌ | ⭐⭐⭐⭐⭐ | Simple text |
| Token | ❌ | ⭐⭐⭐⭐ | Token-aware splitting |
| Recursive Character | ✅ | ⭐⭐⭐⭐ | General-purpose RAG |
| Document Splitters | ✅ | ⭐⭐⭐⭐ | Structured documents |
| Semantic | ⭐⭐⭐⭐⭐ | ⭐⭐ | High-quality retrieval |
| Agentic | ⭐⭐⭐⭐⭐ | ⭐ | Enterprise systems |

---

## Interview Questions

### Why do we perform chunking?

**Answer**

LLMs have limited context windows, and embedding an entire document produces generalized embeddings. Chunking creates smaller, focused pieces of text that improve retrieval accuracy and reduce token usage.

---

### Why do we use chunk overlap?

**Answer**

Overlap preserves context between adjacent chunks. Without overlap, important information spanning two chunks may be lost, reducing retrieval quality.

---

### What happens if chunks are too small?

**Answer**

- Context is lost.
- Information becomes fragmented.
- The LLM may retrieve incomplete information.
- More chunks are generated, increasing storage and retrieval cost.

---

### What happens if chunks are too large?

**Answer**

- Embeddings become too generalized.
- Retrieval precision decreases.
- More irrelevant information is sent to the LLM.
- Higher token usage and inference cost.

---

### Which chunking strategy would you choose?

**Answer**

- **Recursive Character Splitter** for most RAG applications.
- **Semantic Chunking** when retrieval quality is critical.
- **Parent Document Retriever** when maintaining context is important.
- **Agentic Chunking** for enterprise-grade applications where retrieval quality outweighs computational cost.

---
## Key Takeaways

- Chunking improves retrieval quality by creating focused embeddings.
- Recursive Character Splitter is the default choice for most applications.
- Semantic Chunking groups text based on meaning rather than size.
- Agentic Chunking uses an LLM to create semantically meaningful chunks.
- Parent Document Retriever combines accurate retrieval with rich contextual information.