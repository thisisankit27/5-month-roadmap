# Retrieval in RAG

## What is Retrieval?

Retrieval is the process of finding the most relevant documents (or document chunks) from a Vector Database before sending them to the LLM.
Instead of asking the LLM to answer from its internal knowledge, Retrieval provides relevant external context.

---

## Why is Retrieval Needed?

LLMs have two major limitations:

- Limited context window
- Knowledge cutoff (or outdated knowledge)

Retrieval solves this by supplying the LLM with only the most relevant information.

Pipeline

```text
Documents

↓

Chunking

↓

Embeddings

↓

Vector Database

↓

Retriever

↓

Relevant Documents

↓

LLM

↓

Answer
```

The quality of retrieval directly impacts the quality of the final response.

> **Garbage Retrieval = Garbage Response**

---

## Retrieval Workflow

```text
User Query

↓

Embedding Model

↓

Query Embedding

↓

Vector Database

↓

Similarity Search

↓

Top-K Results

↓

Metadata Filtering (Optional)

↓

Score Threshold

↓

Relevant Chunks

↓

LLM
```

---

### Similarity Search

#### Definition

Similarity Search retrieves documents whose embeddings are **closest** to the query embedding. Unlike SQL, it searches based on **meaning**, not exact keywords.

Example

```
User Query

"Explain Dependency Injection"
```

Retrieved

```
IoC Container

Spring Beans

Constructor Injection
```

Even if the exact phrase

```
Dependency Injection
```

never appears.

---

#### Working

```text
User Query

↓

Embedding

↓

Nearest Neighbor Search

↓

Top Similar Chunks
```

Similarity is calculated using metrics such as

- Cosine Similarity
- Dot Product
- Euclidean Distance

---

#### Advantages

- Semantic understanding
- Handles synonyms
- Better retrieval quality
- Works well for natural language queries

---

### Top-K Retrieval

#### Definition

Top-K determines **how many** of the most similar documents should be returned.

Example

```
Top-K = 3

↓

Document A

Document B

Document C
```

---

#### Small Top-K

Advantages

- Faster retrieval
- Lower token cost
- Less irrelevant context

Disadvantages

- May miss useful information

---

#### Large Top-K

Advantages

- Better recall
- More contextual information

Disadvantages

- Higher token usage
- More irrelevant documents
- Can confuse the LLM

---

#### Typical Values

| Application | Top-K |
|-------------|-------|
| Basic RAG | 3–5 |
| Enterprise Search | 5–10 |
| Research Assistant | 10–20 |

---

### Metadata Filtering

#### Definition

Metadata Filtering narrows the search space **before similarity search** by applying structured conditions. Instead of searching every document, only matching documents participate in vector search.

---

#### Example

Metadata

```json
{
  "author": "Aristotle",
  "year": 2024,
  "department": "Finance"
}
```

User

```
Show me Finance reports.
```

Flow

```text
Entire Database

↓

Department = Finance

↓

Similarity Search

↓

Results
```

instead of

```text
Entire Database

↓

Similarity Search

↓

Results
```

---

#### Why Metadata Filtering?

Benefits

- Better retrieval precision
- Faster search
- Reduced token cost
- Better security
- Lower hallucination risk

---

#### Enterprise Metadata Filtering

In production systems, metadata is commonly used for **Access Control**.

Example

Employee A

↓

Can only retrieve

```
HR Documents
```

Employee B

↓

Can only retrieve

```
Engineering Documents
```

The Vector Database ensures users only retrieve documents they are authorized to access.

---

#### Dynamic Metadata Filtering (Self-Query Retrieval)

Instead of manually defining filters, an LLM generates metadata filters from the user's query.

Example

User

```
Show me Sales reports from Europe in 2024.
```

↓

LLM extracts

```json
{
    "department":"Sales",
    "region":"Europe",
    "year":2024
}
```

↓

Retriever applies filters automatically.

This approach is commonly known as **Self-Query Retrieval** or **Dynamic Filtering**.

---

### Score Threshold

#### Definition

Each retrieved document receives a similarity score. The Score Threshold specifies the minimum score a document must achieve to be considered relevant.

---

#### Example

| Document | Similarity Score |
|-----------|----------------:|
| Doc A | 0.95 |
| Doc B | 0.88 |
| Doc C | 0.73 |
| Doc D | 0.41 |

Threshold

```
0.80
```

↓

Only

```
Doc A

Doc B
```

are passed to the LLM.

---

#### Why Score Threshold?

Without a threshold, the retriever may return documents that are only weakly related to the user's query.

Benefits

- Better precision
- Cleaner context
- Reduced hallucinations
- Higher answer quality

---

### Top-K vs Score Threshold

!!! danger "These two are often confused"

#### Top-K

```
Always return K documents.
```

Even if the last document has poor similarity.

---

#### Score Threshold

```
Return only documents above the minimum similarity score.
```

Even if fewer than K documents are returned.

---

Example

```
Top-K = 5

Score Threshold = 0.85
```

Retrieved Scores

```
0.97

0.92

0.81

0.74

0.61
```

Returned

```
0.97

0.92
```

Only two documents satisfy the threshold.

---

## Retrieval Strategies

| Strategy | Purpose |
|----------|---------|
| Similarity Search | Basic semantic retrieval |
| Top-K Retrieval | Control number of returned documents |
| Metadata Filtering | Restrict search space |
| Dynamic Filtering | LLM-generated metadata filters |
| Score Threshold | Remove low-confidence documents |

---

## Retrieval Best Practices

- Use **Recursive Character Chunking** for general-purpose RAG.
- Choose an appropriate **Top-K** (typically 3–5).
- Apply **Metadata Filtering** whenever structured information is available.
- Use **Score Threshold** to remove noisy documents.
- Combine retrieval techniques (Hybrid Search, Metadata Filtering, Reranking) for production-grade systems.

---

## Interview Questions

### What is Retrieval in RAG?

**Answer**

Retrieval is the process of finding the most relevant document chunks from a Vector Database before passing them to the LLM. It enables the model to answer questions using external knowledge.

---

### What is Similarity Search?

**Answer**

Similarity Search retrieves documents based on semantic similarity by comparing embedding vectors rather than matching exact keywords.

---

### What is Top-K?

**Answer**

Top-K specifies the maximum number of highest-ranked documents returned by the retriever.

---

### What happens if Top-K is too small?

**Answer**

Relevant documents may be missed, reducing recall and causing incomplete answers.

---

### What happens if Top-K is too large?

**Answer**

The retriever may return unnecessary documents, increasing token usage, latency, and the chance of confusing the LLM.

---

### What is Metadata Filtering?

**Answer**

Metadata Filtering limits the search space using structured fields such as author, department, year, or access level before performing similarity search.

---

### What is Dynamic Metadata Filtering?

**Answer**

Dynamic Metadata Filtering uses an LLM to automatically convert the user's natural language query into metadata filters, which are then applied during retrieval.

---

### What is Score Threshold?

**Answer**

Score Threshold specifies the minimum similarity score a document must achieve before being considered relevant enough to pass to the LLM.

---

### Difference between Top-K and Score Threshold?

**Answer**

Top-K controls **how many** documents are returned.

Score Threshold controls **how relevant** those documents must be.

---

### Why is Retrieval important in RAG?

**Answer**

The LLM can only generate answers based on the context it receives. Poor retrieval leads to poor context, which directly reduces answer quality, regardless of how powerful the LLM is.

---

## Key Takeaways

- Retrieval supplies relevant external knowledge to the LLM.
- Similarity Search retrieves semantically similar documents.
- Top-K determines the maximum number of retrieved documents.
- Metadata Filtering improves retrieval precision and security.
- Dynamic Filtering automatically generates metadata filters using an LLM.
- Score Threshold removes low-confidence retrieval results.
- Retrieval quality is often more important than choosing a larger LLM.