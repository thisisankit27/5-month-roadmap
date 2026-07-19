# Thinking Like a Senior Engineer

> These notes are not about AI or LangChain.
>
> They are lessons learned while designing the Knowledge Assistant project.
>
> The goal is to learn *how experienced engineers think* before writing code.

---

## Principle 1 — Design Before Code

Instead of immediately writing code, ask:

- What problem am I solving?
- What responsibilities exist?
- Which components should own those responsibilities?
- Can this design scale in the future?

Good software is designed first and implemented second.

---

## PR-1 Discussion

### Goal

Create a clean project foundation.

Not a RAG system.

Not a polished SaaS.

Simply a project that another engineer can clone and immediately understand.

---

### Why use separate modules instead of writing everything inside `app.py`?

#### My Answer

Separation of Concerns.

The architecture should be plug-and-play.

Each module exposes a contract, allowing implementations to change without affecting other modules.

Example

```
Today

FAISS

↓

Tomorrow

Qdrant
```

Only the implementation changes.

The rest of the application remains unaffected.

---

#### Better Interview Answer

Each module has a single responsibility and exposes a clear contract.

This allows implementations to be replaced (e.g., FAISS → Qdrant) without affecting the orchestration layer.

The application depends on abstractions rather than concrete implementations.

---

### If we replace FAISS with Qdrant, how many files should change?

#### My Initial Answer

```
embeddings.py

vectorstore.py
```

---

#### Discussion

Actually,

only

```
vectorstore.py
```

should change.

The embedding model has no knowledge of where vectors are stored.

Its responsibility is simply

```
Text

↓

Embedding Vector
```

Storage is someone else's responsibility.

This is true decoupling.

---

#### Lesson

Never let one module know unnecessary implementation details about another.

---

### Why create many small Pull Requests instead of one huge PR?

#### My Answer

Small PRs provide

- easier collaboration
- manageable reviews
- better testing
- incremental delivery
- quicker feedback
- sprint-based development

---

#### Additional Lesson

Imagine

```
7000 changed lines
```

versus

```
PR-09

↓

Introduced Guardrails
```

If a bug appears,

small PRs are

- easier to review
- easier to rollback
- easier to debug

---

#### Lesson

Each PR should represent one engineering milestone.

Not simply "more code."

---

### Module Responsibilities

Initial design

```
loaders.py
→ Load documents

splitter.py
→ Split documents

embeddings.py
→ Generate embeddings

vectorstore.py
→ Store and retrieve vectors

rag.py
→ Orchestrate everything
```

---

#### Discussion

Uploading documents and answering questions are two completely different workflows.

---

#### Workflow 1

Knowledge Ingestion

```
PDF

↓

Loader

↓

Splitter

↓

Embeddings

↓

Vector Store
```

---

#### Workflow 2

Question Answering

```
Question

↓

Retriever

↓

Prompt

↓

LLM

↓

Answer
```

---

### Architecture Discussion

#### Future Problem

Today

```
loaders.py
```

supports

```
PDF
```

Tomorrow

- PDF
- Word
- Markdown
- Website
- PowerPoint

Should we keep adding

```
if pdf

elif docx

elif md

elif website
```

?

Probably not.

---

#### My Initial Idea

Use

- Parent class
- Child classes
- Inversion of Control

The frontend determines the appropriate loader and passes it to the backend.

---

#### Discussion

The frontend should never know backend implementation details.

Instead,

the frontend simply uploads

```
resume.pdf
```

The backend decides

```
Extension

↓

LoaderFactory

↓

PdfLoader

↓

load()
```

The frontend only knows

```
Upload File
```

Everything else is backend responsibility.

---

#### Better Design

```
                  DocumentLoader
                         ▲
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
   PdfLoader      DocxLoader      WebLoader
                         ▲
                         │
                  LoaderFactory
                         ▲
                         │
                  Uploaded File
```

---

## Design Principles Accidentally Learned

Without studying design patterns, this discussion naturally introduced

- Separation of Concerns
- Single Responsibility Principle
- Dependency Inversion Thinking
- Open/Closed Principle
- Polymorphism
- Factory Pattern (conceptually)

This reinforced the idea that project-driven learning teaches design patterns naturally.

---

## Important Lesson

Don't memorize design patterns. Build enough projects and you'll rediscover them yourself. Later, when learning the official pattern names, they become recognition instead of memorization.

---

## Interview Insight

Question

Why use a Factory instead of writing

```
if extension == "pdf"
```

everywhere?

Answer

A Factory centralizes object creation.

Adding support for a new document type only requires creating a new implementation and registering it with the factory, rather than modifying multiple parts of the application.

This follows the Open/Closed Principle.

---

## Homework

Think about the following architecture.

```
                  Loader
                    ▲
      ┌─────────────┼─────────────┐
      ▼             ▼             ▼
 PdfLoader     DocxLoader     WebLoader
```

Without writing code, answer the following questions.

---

### Question 1

What methods should the parent `Loader` define?

Should it expose only

```
load()
```

or should it define additional responsibilities?

---

### Question 2

Should `LoaderFactory` return

```
PdfLoader
```

or

```
Loader
```

Why?

---

### Question 3

Tomorrow we add

```
ExcelLoader
```

How many existing files should require modification?

If your answer is

```
One registration point
```

or close to it,

your architecture is becoming extensible.

---

## Biggest Takeaway

Before writing code, always ask

> "If the requirements change tomorrow, how much of my code will I need to rewrite?"

The best software is not the one that works today.

The best software is the one that is easiest to change tomorrow.

## PR-2 Discussion — Designing an Extensible Loader Architecture

> These answers are based on engineering principles such as **SOLID**, **Separation of Concerns**, and **Open/Closed Principle**, rather than simply making the code "work."

---

### Question 1

#### What methods should the parent `Loader` define?

Should it expose only

```text
load()
```

or should it define additional responsibilities?

---

##### Initial Thought

At first glance, it seems that every loader only needs one method:

```python
load()
```

After all,

- PDF Loader loads PDFs
- Word Loader loads Word documents
- Markdown Loader loads Markdown files

All of them ultimately return LangChain `Document` objects.

---

##### Better Design

The parent class should define **only the behavior that every loader is guaranteed to support**.

For our current project, that is simply

```python
load()
```

Example

```text
Loader
│
├── load()
│
├── PdfLoader
├── DocxLoader
├── MarkdownLoader
└── WebLoader
```

Every child loader knows **how** to load its own document type.

---

##### Why not define more methods?

Suppose we also define

```python
validate()

extract_images()

extract_tables()
```

Immediately we have a problem.

A WebLoader may not support image extraction.

A MarkdownLoader may not contain tables.

A TXTLoader may not require validation.

Now every child class is forced to implement methods that don't make sense.

This violates the **Interface Segregation Principle (ISP)**.

---

##### Engineering Principle

A parent class should define only the **common contract** shared by every implementation.

If every loader can only guarantee one operation,

then one operation is enough.

> **Don't force child classes to implement methods they don't need.**

---

### Question 2

#### What Should `LoaderFactory` return

```text
PdfLoader
```

or

```text
Loader
```

Why?

---

##### Correct Answer

The Factory should always return

```text
Loader
```

(the parent type)

not

```text
PdfLoader
```

---

##### ❌ Returning Concrete Classes

```text
                Uploaded File
                      │
                      ▼
              LoaderFactory.create()
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
    PdfLoader               DocxLoader
          │                       │
          ▼                       ▼
      Client Code          Client Code
```

Now the client needs to know:

```python
if isinstance(loader, PdfLoader):
    loader.load()

elif isinstance(loader, DocxLoader):
    loader.load()
```

The client is tightly coupled to every implementation.

Every time a new loader is introduced, the client code must change.

---

##### ✅ Returning the Parent Type

```text
                Uploaded File
                      │
                      ▼
              LoaderFactory.create()
                      │
                      ▼
                 Loader (Reference)
                      │
      ┌───────────────┼────────────────┐
      ▼               ▼                ▼
 PdfLoader      DocxLoader      ExcelLoader
      │               │                │
      └───────────────┴────────────────┘
                      │
                      ▼
                  load()
```

The client never knows the actual implementation.

It simply writes

```python
loader = LoaderFactory.create(file)
documents = loader.load()
```

without knowing the concrete implementation.

---

##### Why is this important?

Suppose tomorrow we replace/add

```text
PdfLoader
```

with

```text
BetterPdfLoader
```

Does the client code change?

```
No.
```

Does the Factory change?

```
Only enough to know about the new loader
(or not even that if loaders are auto-registered).
```

This is why we **program to abstractions, not implementations.**

---

##### Engineering Principle

Depend on **abstractions**, not concrete classes.

This is one of the core ideas behind the **Dependency Inversion Principle (DIP)**.

---

### Question 3

Tomorrow we add

```text
ExcelLoader
```

How many existing files should require modification?

---

#### Ideal Answer

As close to **one file** as possible.

---

#### Why?

If adding a new document type requires modifying

- loader.py
- rag.py
- app.py
- splitter.py
- embeddings.py

then the architecture is tightly coupled.

Instead,

adding a new feature should mostly involve

1. Creating a new implementation

```
ExcelLoader
```

2. Registering it with the Factory

Everything else should continue working.

---

#### Ideal Workflow

Before

```text
Loader
│
├── PdfLoader
├── DocxLoader
└── MarkdownLoader
```

Tomorrow

```text
Loader
│
├── PdfLoader
├── DocxLoader
├── MarkdownLoader
└── ExcelLoader
```

The rest of the system remains untouched.

---

#### Why is this valuable?

Imagine six months from now.

The product supports

- PDF
- Word
- Markdown
- PowerPoint
- Excel
- CSV
- HTML
- Websites

If every new loader requires changing five existing files, the project becomes difficult to maintain.

Instead,

each new feature should be

> **Add a class. Register it. Done.**

---

#### Engineering Principle

!!! tip ""This follows the **Open/Closed Principle**"
    > Software entities should be **open for extension** but **closed for modification**.

We extend the application by adding new classes, not by constantly modifying existing ones.

---

#### Visual Architecture

```text
                   Loader (Abstract)

                         ▲
                         │
      ┌──────────────────┼──────────────────┐
      ▼                  ▼                  ▼
 PdfLoader         DocxLoader        MarkdownLoader
                                              │
                                              ▼
                                        ExcelLoader
                                              ▲
                                              │
                                       LoaderFactory
                                              ▲
                                              │
                                       Uploaded File
```

The application communicates only with the parent type. Every concrete loader is hidden behind the Factory.

---

### Interview Takeaways

#### Why should the parent `Loader` expose only `load()`?

Because it should define only the behavior common to every loader. Adding unnecessary methods forces child classes to implement responsibilities they may not support, violating the Interface Segregation Principle.

---

#### Why should the Factory return `Loader` instead of `PdfLoader`?

Because client code should depend on abstractions rather than concrete implementations. This makes the system loosely coupled and easier to extend.

---

#### How many files should change when adding `ExcelLoader`?

Ideally:

- One new class (`ExcelLoader`)
- One registration/update in the Factory (or even zero if using auto-discovery)

Everything else should continue working without modification.

---

## Biggest Lesson

The goal of good architecture is **not** to reduce the amount of code.

The goal is to reduce the amount of **existing code that must change** when requirements evolve.

The easiest code to maintain is the code you don't have to touch.

## PR-3 Discussion - Chunking Engine

!!! note
    > These notes capture the engineering discussions, design decisions, interview answers, and architectural reasoning behind the Chunking Engine implementation.

---

### Project Pipeline Evolution

#### PR-2

```text
PDF
    │
    ▼
Loader
    │
    ▼
List<Document>
```

---

#### PR-3

```text
PDF
    │
    ▼
Loader
    │
    ▼
List<Document>
    │
    ▼
Chunking Engine
    │
    ▼
List<Document> (Chunks)
```

Notice something important:

The pipeline grows. We **never modify app.py**. Instead, `ingestion.py` orchestrates additional stages over time.

---

### Should app.py know about Chunking?

No. `app.py` should remain completely unaware of the internal pipeline.

Instead it should simply call

```python
documents = ingest_documents(uploaded_files)
```

Today

```text
Load
```

Tomorrow

```text
Load
↓

Chunk
```

Later

```text
Load
↓

Chunk
↓

Embed
```

Eventually

```text
Load
↓

Chunk
↓

Embed
↓

Vector Store
```

The caller never changes. This is one of the biggest responsibilities of an orchestration layer.

---

### Why have an Ingestion Pipeline?

Think of it as a workflow orchestrator.

```text
app.py

↓

"I have files."

↓

ingestion.py

↓

"I know exactly how to process them."
```

The orchestration layer coordinates all stages while keeping the UI completely decoupled from implementation details.

---

### Should we use Strategy Pattern for Chunking?

#### Initial Thought

We considered creating

```text
Splitter (Abstract)

        ▲

RecursiveSplitter
```

so different splitting algorithms could be swapped without affecting the rest of the application.

Possible future strategies

- RecursiveCharacterTextSplitter
- MarkdownHeaderTextSplitter
- PythonCodeTextSplitter
- HTMLHeaderTextSplitter
- SemanticChunker

All share the same goal:

```text
List<Document>

↓

Chunks
```

Only the algorithm changes. This is the Strategy Pattern.

---

#### Why NOT use Strategy today?

Current project supports only

```text
RecursiveCharacterTextSplitter
```

There is no runtime decision. Adding an abstraction now would increase complexity without solving an existing problem.

Instead we follow

> Design for extension.
> Implement for today's requirements.

Current implementation

```text
splitter.py

↓

split_documents(documents)
```

Later, if multiple chunking algorithms are supported, refactor to Strategy Pattern.

---

#### Factory vs Strategy

Factory answers

> Which object should I create?

Example

```text
UploadedFile

↓

LoaderFactory

↓

PdfLoader
```

Strategy answers

> Which algorithm should I execute?

Example

```text
Documents

↓

Chunk Strategy

↓

Recursive Splitter
```

Factory creates objects.
Strategy chooses algorithms.

---

### Why RecursiveCharacterTextSplitter?

Many developers think it simply splits by character count. It actually tries to preserve semantic boundaries.

Order of separators

```text
Paragraph (\n\n)

↓

Line (\n)

↓

Space (" ")

↓

Character
```

Only when larger boundaries fail does it move to smaller ones. Therefore it minimizes broken sentences and incomplete thoughts.

---

### Why not split by Pages?

Initially page splitting appears attractive because pages usually contain related information. However pages are presentation boundaries, not semantic boundaries.

Example

```text
Page 17

Spring Boot provides dependency...

-------------------------

Page 18

...Injection and IoC...
```

Now one logical concept spans two pages.

Retrieval quality decreases.

Similarly

- One page may contain many unrelated topics.
- One topic may span multiple pages.

Therefore page boundaries should not define chunk boundaries.

---

### Why Chunk at all?

Embedding the entire document creates a single semantic representation.

Problems

- Retrieval becomes coarse.
- Embedding represents an "average meaning" of the document.
- Context window may overflow.
- Entire document must be sent to the LLM.
- Higher token cost.
- Lower answer precision.

Chunking solves this.

Instead of retrieving

```text
Entire Book
```

RAG retrieves only

```text
Relevant Sections
```

This produces

- Smaller prompts
- Lower token usage
- Better retrieval precision
- More focused answers

---

### Why Overlap?

Imagine

```text
Chunk 1

Spring Boot provides dependency

-----------------------------

Chunk 2

injection, allowing loose coupling...
```

The concept

```text
dependency injection
```

has been split. Similarity search may fail.

Overlap duplicates a small portion of adjacent chunks.

Example

```text
Chunk 1

...dependency injection

Chunk 2

dependency injection allows...
```

Now either chunk contains sufficient context. Overlap preserves semantic continuity across chunk boundaries.

---

### How should Chunk Size be chosen?

There is no universally correct value. Chunk size depends on several tradeoffs.

#### LLM Context Window

Smaller chunks reduce prompt size.

---

#### Embedding Model

Different embedding models capture semantic meaning differently. Some perform better with shorter chunks. Others preserve context better with larger chunks.

---

#### Retrieval Precision

Large chunks

- More context
- Less precise retrieval

Small chunks

- Better retrieval precision
- Risk of insufficient context

---

#### Token Cost

Large chunks

- Higher token usage

Small chunks

- Lower prompt cost

---

#### Nature of Documents

Different document types require different chunking strategies.

Examples

##### Python Code

Split after

- classes
- methods
- functions

Not inside methods.

---

##### Markdown

Split after

- headings
- sections

---

##### HTML

Split after

- DOM sections
- headers

---

##### Plain Text

RecursiveCharacterTextSplitter is generally suitable.

---

### Metadata after Chunking

Before chunking

```python
Document(
    page_content="...",
    metadata={
        "source": "...",
        "page": 5
    }
)
```

After chunking

```python
Document(
    page_content="Smaller chunk...",
    metadata={
        "source": "...",
        "page": 5
    }
)
```

The **Document type does not change**. Only `page_content` becomes smaller. Metadata is inherited.

---

### Can Metadata become richer?

Yes. Additional metadata may be introduced.

Example

```json
{
  "source": "spring.pdf",
  "page": 5,
  "chunk": 3,
  "section": "Dependency Injection",
  "language": "en"
}
```

This enables

- filtering
- tracing
- debugging
- citation
- advanced retrieval

---

### Important Design Principle

Throughout the pipeline we continue passing

```python
Document
```

Objects. 

Only the contents evolve.

```text
Document

↓

Loaded Document

↓

Chunked Document

↓

Embedded Document

↓

Stored Vector
```

The type remains consistent. This greatly simplifies downstream pipeline stages.

---

### Interview Questions

#### Why RecursiveCharacterTextSplitter?

It attempts to preserve semantic boundaries by recursively trying progressively smaller separators before finally splitting by character count. This creates more meaningful chunks than fixed-size character splitting.

---

#### Why overlap?

Overlap ensures important context near chunk boundaries is duplicated into adjacent chunks, preventing semantic information from being lost during retrieval.

---

#### How do you choose chunk size?

Chunk size is a tradeoff between retrieval precision, context preservation, embedding quality, LLM context window, token cost, and the structure of the underlying documents.

!!! success "Note"
    There is no universally optimal value.

---

### Biggest Takeaway

A production RAG pipeline is not about LangChain APIs. It is about information flowing through multiple well-separated stages.

```text
Upload

↓

Load

↓

Chunk

↓

Embed

↓

Store

↓

Retrieve

↓

Generate
```

Each stage should have a single responsibility and expose a stable interface to the next stage.

### Design Patterns in our RAG Project (PR-3)

> These notes capture the engineering decisions behind introducing the **Strategy Pattern** and **Flyweight Pattern** while building our RAG ingestion pipeline.

The goal is **not** to memorize design patterns. The goal is to understand **why** they naturally emerge while solving software engineering problems.

---

#### Project Evolution

##### PR-1

```text
User

↓

UI
```

---

##### PR-2

```text
User

↓

Upload

↓

Loader Factory

↓

PdfLoader

↓

Documents
```

Introduced:

- Factory Pattern
- Polymorphism
- Abstract Classes

---

##### PR-3

```text
User

↓

Upload

↓

Loader

↓

Documents

↓

Chunk Service

↓

Chunk Strategy

↓

Chunks
```

Introduced:

- Strategy Pattern
- Flyweight Pattern
- Better Separation of Concerns

---

#### Why did we need Strategy Pattern?

Initially our project only supported PDFs.

```text
PDF

↓

RecursiveCharacterTextSplitter
```

Everything seemed simple.

---

Then requirements changed.

The application should support

```text
PDF

Markdown

Python

HTML

TXT
```

Question:

Should every file use

```text
RecursiveCharacterTextSplitter
```

?

Answer:

No.

Different document types require different chunking algorithms.

Examples

| Document Type | Preferred Chunking |
|---------------|--------------------|
| PDF | RecursiveCharacterTextSplitter |
| Markdown | MarkdownHeaderTextSplitter |
| Python | PythonCodeTextSplitter |
| HTML | HTMLHeaderTextSplitter |

The **behavior varies**. This is exactly what Strategy Pattern solves.

---

#### Strategy Pattern

Instead of writing

```python
if extension == ".pdf":
    ...

elif extension == ".py":
    ...

elif extension == ".md":
    ...
```

throughout the project, we encapsulate each algorithm inside its own class.

```text
                 Strategy (Abstract)

                        ▲

      ┌─────────────────┼─────────────────┐

      │                 │                 │

      ▼                 ▼                 ▼

RecursiveStrategy  PythonStrategy  MarkdownStrategy
```

Every strategy exposes exactly the same interface.

```python
chunk(document)
```

The caller never knows which implementation is executed.

---

#### Why is this better?

Without Strategy

```text
Chunk Service

↓

if PDF

↓

Recursive

↓

else if Python

↓

Python Splitter

↓

else if Markdown
```

Every new algorithm modifies existing code.

---

With Strategy

```text
Chunk Service

↓

Strategy Factory

↓

Correct Strategy

↓

chunk(document)
```

The Chunk Service never changes.

---

#### Factory vs Strategy

This project uses **both**. They solve different problems.

---

##### Factory

Question:

> Which object should I create?

Example

```text
Uploaded File

↓

LoaderFactory

↓

PdfLoader
```

Factory is responsible for object creation.

---

##### Strategy

Question:

> Which algorithm should execute?

Example

```text
Document

↓

StrategyFactory

↓

RecursiveChunkStrategy

↓

chunk(document)
```

Strategy is responsible for behavior.

---

#### They work together

Our architecture

```text
Chunk Service

↓

Strategy Factory

↓

Strategy

↓

LangChain
```

The factory chooses the appropriate strategy.
The strategy executes the algorithm.

---

#### Chunk Service

Responsibility

- Iterate over Documents
- Ask Factory for appropriate strategy
- Aggregate chunks

It should **never**

- know chunking algorithms
- perform splitting
- inspect file types

Its only job is orchestration.

---

#### Strategy Factory

Responsibility

Given

```python
Document
```

Return

```python
Correct Chunk Strategy
```

Example

```text
.pdf

↓

RecursiveChunkStrategy

----------------------

.py

↓

PythonChunkStrategy

----------------------

.md

↓

RecursiveChunkStrategy
```

Notice

Multiple document types may reuse the same strategy. The factory chooses algorithms, not document types.

---

#### Why choose strategy per Document?

Suppose user uploads

```text
resume.pdf

main.py

README.md
```

Every document requires a different chunking algorithm.

Therefore

```text
ChunkService

↓

for each Document

↓

StrategyFactory

↓

Correct Strategy
```

If we selected strategy only once,

mixed uploads would become impossible.

---

#### Why use split_documents() instead of split_text()?

Initially

```python
split_text(document.page_content)
```

was considered.

Problem

Metadata would be lost.

Instead

```python
split_documents([document])
```

returns

```python
List[Document]
```

Each chunk inherits

```python
metadata
```

Example

Before

```python
Document(
    page_content="...",
    metadata={
        "source":"spring.pdf",
        "page":7
    }
)
```

After chunking

```python
Document(
    page_content="Smaller chunk",
    metadata={
        "source":"spring.pdf",
        "page":7
    }
)
```

Metadata survives automatically.

---

#### Flyweight Pattern

After Strategy was implemented,

we noticed

```python
StrategyFactory.create(document)
```

created

```python
RecursiveChunkStrategy()
```

for every document.

Example

```text
Document 1

↓

RecursiveChunkStrategy()

Document 2

↓

RecursiveChunkStrategy()

Document 3

↓

RecursiveChunkStrategy()
```

This is unnecessary. The strategy stores no state.

---

#### Flyweight Solution

The Factory owns reusable strategy instances.

```text
StrategyFactory

│

├── RecursiveChunkStrategy

├── PythonChunkStrategy

└── MarkdownChunkStrategy
```

Whenever requested

```text
PDF

↓

same RecursiveChunkStrategy object
```

Multiple documents share *one* strategy object.

---

#### Why Flyweight works

Our Strategy stores no mutable state.

```python
chunk(document)
```

instead of

```python
self.document
```

Therefore

the same object can safely process

```text
PDF A

↓

PDF B

↓

PDF C
```

---

#### When would Flyweight NOT work?

Suppose Strategy stores

```python
self.chunk_size = 500
```

and another request changes it to

```python
1000
```

Now, all users share the same mutable object. Unexpected behaviour appears. Flyweight requires shared objects to remain effectively immutable or stateless.

---

#### Why we still implemented Flyweight

Production?
Probably unnecessary. Creating one Strategy object is extremely cheap.

However, this project is primarily for learning.
Implementing Flyweight helped understand
- object sharing
- stateless services
- object lifecycle
- memory optimisation patterns

---

#### Future Improvement

Currently

```text
.pdf

↓

Recursive Strategy
```

is hardcoded.

Future

```yaml
chunking:

  pdf: recursive

  md: recursive

  py: python

  html: html
```

The Factory could read configuration instead of hardcoding mappings. No source code changes required.

---

### Design Principles Learned

#### Single Responsibility Principle

Chunk Service orchestrates.
Strategy chunks.
Factory creates strategies.
Every class has one reason to change.

---

#### Open/Closed Principle

Adding

```text
SemanticChunkStrategy
```

requires

- creating one new class
- modifying only the Factory

Existing strategies remain untouched.

---

#### Dependency Inversion

Chunk Service depends on

```python
Strategy
```

not

```python
RecursiveChunkStrategy
```

Concrete implementations remain hidden.

---

### Final Architecture

```text
                 Upload

                    │

                    ▼

          Loader Factory

                    │

                    ▼

               Documents

                    │

                    ▼

             Chunk Service

                    │

                    ▼

          Strategy Factory

                    │

      ┌─────────────┴─────────────┐

      ▼                           ▼

RecursiveChunkStrategy    PythonChunkStrategy

      │                           │

      └─────────────┬─────────────┘

                    ▼

             LangChain Splitters

                    ▼

                 Chunks
```

---

### Biggest Takeaways

- Factory creates objects.
- Strategy encapsulates algorithms.
- Flyweight reuses stateless objects.
- Services orchestrate workflows.
- The pipeline continues carrying `Document` objects.
- Metadata should never be discarded.
- Choose the strategy at the **smallest unit where behaviour varies**.
- Design patterns are not interview topics—they naturally emerge while solving engineering problems.

---

### Interview Questions

#### Why did you introduce Strategy Pattern?

Different document types require different chunking algorithms. Strategy encapsulates each algorithm behind a common interface, allowing the Chunk Service to remain independent of implementation details.

---

#### Why use a Factory with Strategy?

The Factory selects the appropriate strategy based on document metadata. The Strategy performs the chunking algorithm. Factory chooses **which object**, Strategy defines **what behaviour**.

---

#### Why process one Document at a time?

Different uploaded documents may require different chunking strategies. Selecting the strategy per Document allows mixed uploads (PDF, Markdown, Python) to be handled correctly.

---

#### Why use split_documents()?

It preserves LangChain `Document` objects along with metadata, enabling traceability, filtering, and downstream retrieval.

---

#### Why implement Flyweight?

Chunking strategies are stateless. Reusing a single strategy instance avoids unnecessary object creation and demonstrates efficient object sharing, although the optimization is primarily educational in this project.

---

### Biggest Engineering Lesson

Design patterns should never be introduced because they are famous. They should emerge naturally when solving real software engineering problems.

In this project:
- Factory solved object creation.
- Strategy solved algorithm variation.
- Flyweight solved object reuse.

## PR-4 Discussion — Embedding Pipeline & Designing for PR-5

> These notes capture the engineering decisions behind designing the Embedding Pipeline and how it naturally connects to the upcoming Vector Database layer.

The objective is **not** simply generating embeddings. The objective is understanding **how responsibilities are distributed across services** in a scalable RAG architecture.

---

### Current Architecture

After PR-3, the pipeline looks like:

```text
Upload

↓

Loader Factory

↓

Documents

↓

Chunk Service

↓

Chunks (List<Document>)
```

PR-4 extends it to:

```text
Upload

↓

Loader Factory

↓

Documents

↓

Chunk Service

↓

Chunks

↓

Embedding Service

↓

Embeddings
```

Notice that we still haven't introduced the Vector Database. Embeddings exist **before** they are stored.

---

### Why EmbeddingService?

Question:

Should `ingestion.py` directly call the embedding model?

Example

```python
embedding_model.embed_documents(...)
```

Answer

No.

`ingestion.py` is an orchestration layer. It should coordinate the workflow but never know implementation details.

Its responsibility is simply

```text
Load

↓

Chunk

↓

Embed

↓

Store

↓

Retrieve
```

This keeps the application extensible and follows the Single Responsibility Principle.

---

### Responsibility of EmbeddingService

EmbeddingService is responsible for

- selecting the embedding model
- generating embeddings
- batching requests (future)
- measuring embedding performance
- hiding LangChain implementation details

It should **not**

- know about Vector Databases
- know about FAISS
- know about retrieval
- know about UI

Its only job is

```text
Text

↓

Vectors
```

---

### Should Strategy Pattern be used?

Initially the answer seems yes because embedding models can vary.

Examples

```text
BAAI/bge-small-en-v1.5

↓

384 dimensions

-------------------------

OpenAI text-embedding-3-small

↓

1536 dimensions

-------------------------

Nomic Embed

↓

768 dimensions
```

Different models.
Different dimensions.
Different retrieval quality.

However

today, our application supports exactly one model.

Introducing Strategy now would create unnecessary abstraction.

!!!success "Engineering lesson"
    > Design for extension.
    >
    > Implement for today's requirements.

Therefore

PR-4 intentionally keeps

```text
Embedding Service

↓

Embedding Model
```

without introducing Strategy.

---

### When Strategy becomes useful

Suppose

Premium users

↓

OpenAI Embeddings

Free users

↓

HuggingFace Embeddings

Now

behavior varies.

At this point, Strategy Pattern naturally emerges.

The variation is

```text
User Tier
```

not

```text
Document Type
```

This is a key architectural insight. Always identify **what actually varies** before introducing Strategy.

---

### Why Factory is unnecessary here

During loading, different document types required different loader objects.

Factory solved

```text
Which object should I create?
```

During embedding, every document is already represented as

```python
Document
```

No object creation decision exists.

Therefore

Factory provides little value here.

---

### Service Contract

Question

What should EmbeddingService accept?

Answer

```python
List[Document]
```

Question

What should it return?

EmbeddingService returns only

```python
List[List[float]]
```

Its responsibility ends once vectors are produced.

---

### Why not return Vector Objects?

Suppose EmbeddingService returned

```python
EmbeddingResult

{

document,

chunk,

metadata,

embedding

}
```

Question

Who actually needs this structure?

Answer

Only the Vector Database.

Therefore

EmbeddingService would be performing work that belongs elsewhere.

This violates proper responsibility allocation.

---

### Service Responsibilities

ChunkService

Input

```python
List[Document]
```

Output

```python
List[Document]
```

EmbeddingService

Input

```python
List[Document]
```

Output

```python
List[List[float]]
```

VectorStore

Input

```python
documents,
embeddings
```

Output

*Storage*

Every service owns exactly one transformation.

---

### Relationship between Documents and Embeddings

Question

If EmbeddingService returns only vectors, how does the application know which embedding belongs to which Document?

Answer

Ordering.

Example

Documents

```text
Chunk1

Chunk2

Chunk3
```

Embeddings

```text
Vector1

Vector2

Vector3
```

Both lists preserve the same order.

Therefore

```text
Chunk2

↓

Vector2
```

The relationship is naturally maintained.

---

### Where should mapping occur?

One proposal was introducing

```python
EmbeddingResult
```

to combine

- Document
- Metadata
- Chunk
- Embedding

Although reasonable, only one component actually requires this information.

The Vector Database.

Therefore, the mapping responsibility belongs to

```text
VectorStore
```

rather than EmbeddingService.

---

### Why VectorStore should perform mapping

VectorStore receives

```python
documents
```

and

```python
embeddings
```

Example

```python
store(
    documents,
    embeddings
)
```

Internally

```python
for document, embedding in zip(
    documents,
    embeddings
):
```

Store them together. This keeps EmbeddingService completely independent of storage implementation.

---

#### Why use zip()?

Python provides

```python
zip()
```

which iterates over two collections simultaneously.

Example

```python
for document, embedding in zip(documents, embeddings):
```

Each embedding automatically corresponds to its respective Document. No intermediate DTO is required.

---

### Why doesn't EmbeddingService know FAISS?

EmbeddingService should not know

- FAISS
- Chroma
- Pinecone
- Qdrant

It simply converts

```text
Chunk

↓

Vector
```

Storage concerns belong exclusively to the Vector Database layer.

---

### Does the Vector Database determine dimensions?

Embedding models determine vector dimensionality.

Examples

```text
BAAI

↓

384

------------------

OpenAI

↓

1536

------------------

Nomic

↓

768
```

The Vector Database simply validates that every inserted vector has the expected dimension. It does not choose it.

!!!alert "Rule"
    > One Vector Database index should contain vectors generated by a single embedding model (or models with the same output dimensionality and representation).

---

### Why don't we directly embed PDFs?

Embedding models operate on `text` not `binary document` formats.

Therefore, the pipeline becomes

```text
PDF

↓

Loader

↓

Text

↓

Chunking

↓

Embeddings
```

Chunking is essential because embedding an entire document would

- produce generic embeddings
- reduce retrieval precision
- increase token usage
- waste context window
- reduce answer quality

Instead, only semantically relevant chunks are retrieved during RAG.

---

### Future Pipeline (PR-5)

After EmbeddingService

the architecture becomes

```text
Chunks

↓

Embedding Service

↓

Embeddings

↓

Vector Store

↓

Similarity Search

↓

Retrieved Chunks

↓

LLM
```

Notice, EmbeddingService finishes before retrieval begins.

---

### Information Expert Principle

A major design discussion occurred around who should combine Documents and Embeddings.

Conclusion: The component that owns storage should combine them.

This follows the GRASP principle Information Expert.

Give responsibility to the component that possesses the required knowledge.

---

### Final Architecture

```text
Upload

↓

Loader Factory

↓

Documents

↓

Chunk Service

↓

Chunks

↓

Embedding Service

↓

Embeddings

↓

Vector Store

↓

Retriever

↓

LLM
```

---

### Design Principles Learned

#### Single Responsibility

Each service performs one transformation.

---

#### Separation of Concerns

Embedding generation remains independent from storage.

---

#### Open/Closed Principle

New embedding models can later be introduced without changing orchestration.

---

#### Information Expert (GRASP)

Responsibilities belong to the component that owns the required knowledge.

---

### Future Improvements

When multiple embedding providers are supported

introduce

```text
Embedding Strategy
```

Example

```text
Embedding Service

↓

Embedding Strategy

↓

OpenAI Strategy

↓

HuggingFace Strategy

↓

Nomic Strategy
```

Only then does Strategy become justified.

---

### Interview Questions

#### Why introduce EmbeddingService?

To isolate embedding logic from orchestration, making the application extensible while hiding implementation details.

---

#### Why doesn't ingestion.py directly call LangChain?

Because ingestion is responsible only for coordinating pipeline stages, not implementing them.

---

#### Why not use Strategy immediately?

Only one embedding model currently exists. Strategy should be introduced when multiple interchangeable algorithms exist.

---

#### Why not return Vector Objects?

EmbeddingService should only transform text into vectors.

Storage structures belong to the Vector Database.

---

#### Why preserve ordering?

The nth embedding always corresponds to the nth Document. The Vector Database can combine them using

```python
zip(documents, embeddings)
```

without additional mapping objects.

---

#### Why shouldn't EmbeddingService know FAISS?

Embedding generation and storage are independent responsibilities. This keeps the architecture modular and allows swapping Vector Databases without changing embedding logic.

---

### Biggest Engineering Lesson

During this PR we realized that software architecture is not about creating more classes.

It is about giving every component exactly one responsibility.

The cleanest architecture often emerges by asking

> **"Who actually owns this responsibility?"**

instead of

> **"Where can I put this code?"**