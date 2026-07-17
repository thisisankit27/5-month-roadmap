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

## Homework Discussion — Designing an Extensible Loader Architecture

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