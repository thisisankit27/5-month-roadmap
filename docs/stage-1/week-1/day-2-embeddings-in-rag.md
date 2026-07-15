# Embeddings in RAG

## What is an Embedding?

An embedding is a dense numerical vector that represents the semantic meaning of text.

The goal of an embedding model is to place semantically similar pieces of text close together in a high-dimensional vector space.

Example

```
"I love Java"

↓

[0.24, -0.81, 0.17, ...]
```

Every text chunk becomes one embedding vector.

---

# How are Embeddings Generated?

> Note: This explanation is simplified to build intuition.

## Step 1 — Tokenization

Input text

```
Spring Boot is awesome
```

↓

Tokenizer

↓

```
["Spring", "Boot", "is", "awesome"]
```

↓

Each token receives a unique Token ID.

Example

```
Spring → 1548

Boot → 8271

is → 41

awesome → 9382
```

---

## Step 2 — Embedding Matrix Lookup

The model contains a huge matrix called the **Embedding Matrix**.

Think of it as a lookup table.

```
Token ID

↓

Embedding Vector
```

Example

| Token ID | Vector |
|-----------|----------------|
| 1548 | [0.23, 0.11, ...] |
| 8271 | [-0.81, 0.44, ...] |
| 41 | [0.03, -0.92, ...] |

Initially these vectors are random.

During training, the neural network gradually adjusts them so that semantically related words and phrases move closer together in the vector space.

> The embedding matrix becomes "smarter" during training.

---

# Semantic Vector Space

Imagine representing words as points in space.

## 2D Example (Analogy)

Suppose we manually define

```
X = Age

Y = Gender
```

Then

```
Grandfather

↓

(1,9)

Man

↓

(1,7)

Boy

↓

(1,2)
```

Boy is closer to Man than Grandfather.

This represents semantic similarity.

---

## 3D Example (Analogy)

Add another feature

```
Z = Royalty
```

Now

```
King

↓

(1,8,8)

Man

↓

(1,7,0)

Woman

↓

(9,7,0)

Queen

↓

(9,8,8)
```

This allows the famous relationship

```
King

− Man

+ Woman

≈ Queen
```

---

### Important Note ⭐

The dimensions above are **only an analogy**.

In real embedding models,

there are **hundreds of dimensions** (384, 768, 1536, etc.), and **no individual dimension has a human-readable meaning**.

The model learns these representations automatically during training.

---

# Embedding Dimensionality

## Definition

Embedding dimensionality is the number of values in each embedding vector.

Example

```
384-dimensional embedding

↓

[
0.24,
-0.13,
...
384 numbers
]
```

Each chunk produces exactly one vector of this size.

---

## Higher Dimensions

Advantages

- Capture richer semantic relationships
- Better represent complex meanings

Disadvantages

- More storage
- Higher computation cost
- Slower similarity search
- Risk of overfitting (model becomes too tailored to the training data and performs poorly on unseen data)

---

## Lower Dimensions

Advantages

- Faster
- Less storage
- Lower computational cost

Disadvantages

- May lose subtle semantic information
- Lower retrieval quality

---

# Vector Store Representation

A vector database stores much more than just embeddings.

Conceptually

| Chunk ID | Chunk Text | Embedding | Metadata |
|-----------|------------|-----------|----------|
| 101 | "Spring Boot..." | [384 values] | source=PDF1 |
| 102 | "Dependency Injection..." | [384 values] | page=5 |

Notice

Only the **text** is embedded.

Metadata is stored separately and used for filtering.

---

# Embeddings in RAG

Pipeline

```
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

User Query

↓

Query Embedding

↓

Similarity Search

↓

Relevant Chunks

↓

LLM

↓

Answer
```

Notice

The **user query is embedded using the SAME embedding model** as the documents.

Only then can similarity search work correctly.

---

# Why Re-indexing is Required

Suppose

Document embeddings were created using

```
BAAI/bge-small

↓

384 dimensions
```

Later you switch to

```
OpenAI text-embedding-3-small

↓

1536 dimensions
```

Now

Documents

↓

Old Vector Space

Question

↓

New Vector Space

The vectors no longer represent the same coordinate system.

Similarity calculations become meaningless.

Therefore,

all documents must be embedded again.

This process is called **Re-indexing**.

---

# Similarity Metrics

Similarity search determines how "close" two vectors are.

Three common metrics are used.

---

# 1. Dot Product

## Definition

The dot product measures similarity using both

- direction
- magnitude

Formula

```
A · B
```

### Important

The dot product is **NOT limited to [-1, 1]**.

Larger values generally indicate greater similarity. Because magnitude affects the score, larger vectors may produce larger dot products.

The dot product of vectors A and B reflects how closely they point in the same direction, but without normalizing magnitudes. This factor makes it sensitive to scale: vectors with large values can appear more similar even if their direction differs.

Use Cases

- Hybrid Search
- Recommendation Systems
- Some embedding models

---

# 2. Cosine Similarity ⭐ (Most Common)

## Definition

Measures the angle between two vectors.

Ignores vector magnitude.

Formula

```
(A · B)

────────────

|A||B|
```

Range

```
1

↓

Same Direction

0

↓

Orthogonal

-1

↓

Opposite Direction
```

Advantages

- Independent of vector length
- Excellent for semantic search
- Widely used for document retrieval

Applications

- Search Engines
- RAG
- Recommendation Systems
- NLP

---

# 3. Euclidean Distance

## Definition

Measures the straight-line distance between two vectors.

Smaller distance

↓

Higher similarity.

Advantages

- Simple
- Intuitive

Disadvantages

- Sensitive to vector magnitude
- Less suitable for high-dimensional text embeddings

Applications

- Clustering
- Computer Vision
- Spatial Analysis

---

# Comparison

| Metric | Measures | Range | Common Use |
|----------|----------|-------|------------|
| Dot Product | Direction + Magnitude | Unbounded | Hybrid Search |
| Cosine Similarity | Direction Only | -1 to 1 | Semantic Search |
| Euclidean Distance | Straight-line Distance | 0 to ∞ | Clustering |

---

# Interview Questions

## 1. What is an embedding?

**Answer**

An embedding is a dense numerical vector that captures the semantic meaning of text. Similar text is represented by vectors that are close together in a high-dimensional vector space.

---

## 2. Why do we need embeddings in RAG?

**Answer**

Embeddings allow semantic search instead of keyword search. Both documents and user queries are converted into vectors, enabling retrieval of contextually similar information even when exact words differ.

---

## 3. What is embedding dimensionality?

**Answer**

Embedding dimensionality is the number of numerical values in an embedding vector. Higher dimensions capture richer semantic information but require more storage and computation.

---

## 4. Why can't we compare embeddings generated by different models?

**Answer**

Different embedding models learn different vector spaces. Even if they represent the same text, the coordinates are incompatible, making similarity calculations invalid. Therefore, changing embedding models requires re-indexing all stored documents.

---

## 5. Why is Cosine Similarity preferred over Dot Product?

**Answer**

Cosine Similarity ignores vector magnitude and compares only direction, making it more robust for semantic similarity. Dot Product is affected by both magnitude and direction, which can bias results toward larger vectors.

---

## 6. What does a vector database store?

**Answer**

A vector database stores:

- Embedding vectors
- Original text
- Metadata
- Document IDs

During retrieval, similarity search is performed on embeddings, while the original text and metadata are returned to the application.

---

# Key Takeaways

- Every text chunk is converted into one embedding vector.
- Embeddings place semantically similar text close together in vector space.
- Higher dimensions capture richer semantic meaning but increase computational cost.
- The vector database stores embeddings along with original text and metadata.
- Cosine Similarity is the most common metric for semantic search.
- Changing the embedding model requires regenerating all document embeddings (re-indexing).