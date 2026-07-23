# Structured Outputs in LLMs & RAG


## What are Structured Outputs?

### Crisp Definition

**Structured Output is a technique that forces an LLM to return responses that conform to a predefined schema instead of free-form natural language.**

The schema may be defined using:

- JSON Schema
- Pydantic Models
- Dataclasses
- Typed Objects

Instead of receiving:

```text
The vendor is Amazon.
Invoice date is 15 July.
Amount is ₹1,250.
```

we receive:

```json
{
  "vendor": "Amazon",
  "invoice_date": "2026-07-15",
  "amount": 1250
}
```

The output becomes directly usable by software.

---

## Why Do We Need Structured Outputs?

LLMs naturally generate text.

Software expects structured data.

Without structured outputs:

```text
LLM

↓

Random Text

↓

Developer writes fragile parsing logic
```

With structured outputs:

```text
LLM

↓

Validated JSON

↓

Database

↓

API

↓

Business Logic
```

No unreliable string parsing.

---

## Benefits of Structured Outputs

### Predictability

Applications always receive data in a known format.

Example

```json
{
    "vendor_name": "...",
    "invoice_date": "...",
    "total_amount": ...
}
```

instead of paragraphs.

---

### Reliability

Modern LLM APIs support schema-constrained generation.

If the model cannot satisfy the schema,

↓

validation fails

↓

application retries or handles the error.

---

### Type Safety

Each field has a defined data type.

Example

```python
amount: float
```

instead of

```text
"One Thousand Rupees"
```

---

### Easier API Integration

Structured output can directly populate

- REST APIs
- Databases
- Event Queues
- Microservices

---

### Source Traceability

Schemas can include

- document IDs
- citations
- confidence scores
- page numbers

Example

```json
{
  "answer": "...",
  "source": "page_15.pdf",
  "confidence": 0.94
}
```

Very useful in RAG.

---

## Pydantic

### Definition

Pydantic is a Python library for defining, validating and enforcing structured data models.

Instead of trusting an LLM,

Pydantic verifies:

- required fields
- data types
- constraints

before your application uses the response.

---

### Example

```python
from pydantic import BaseModel

class Invoice(BaseModel):
    vendor: str
    amount: float
    invoice_date: str
```

Now the LLM must produce something matching:

```json
{
    "vendor":"Amazon",
    "amount":1250,
    "invoice_date":"2026-07-15"
}
```

---

## How Structured Output Works

### Step 1

Developer defines

```python
class Invoice(BaseModel):
```

↓

---

### Step 2

Pydantic converts it into

JSON Schema

↓

---

### Step 3

Framework (LangChain/OpenAI/etc.)

adds instructions like

```text
Return ONLY valid JSON matching this schema.
```

↓

---

### Step 4

LLM generates

JSON

↓

---

### Step 5

Pydantic validates

↓

Success

↓

Python Object

OR

↓

Validation Error

---

## JSON Schema

### Definition

JSON Schema is a standard way of describing the expected structure of JSON data.

Example

```json
{
  "type": "object",
  "properties": {
      "vendor": {
          "type": "string"
      },
      "amount": {
          "type": "number"
      }
  }
}
```

Most frameworks generate this automatically from Pydantic models.

---

## JSON Repair

LLMs sometimes generate

```json
{
"name":"John",
}
```

or

```json
{
...
}
```

These are invalid.

Applications often

* remove markdown
* fix commas
* repair brackets
* retry generation

before parsing.

---

## Output Parser

### Definition

An Output Parser is responsible for converting raw LLM output into usable structured data.

Think of it as the bridge between

LLM

↓

Application

---

### Responsibilities

#### Prompt Injection

Adds formatting instructions automatically.

Example

```text
Return ONLY valid JSON.
```

---

#### Parsing

Converts

```text
{
...
}
```

↓

Python Object

---

#### Validation

Uses

Pydantic

↓

Check

* Required fields
* Types
* Constraints

---

### Repair

Some parsers automatically

* retry
* repair JSON
* ask the LLM to regenerate

if parsing fails.

---

## Overall Architecture

```text
         Pydantic Model
               │
               ▼
        JSON Schema
               │
               ▼
        Output Parser
               │
               ▼
    Prompt Instructions
               │
               ▼
             LLM
               │
               ▼
        Raw JSON/Text
               │
               ▼
        Output Parser
               │
        Parse + Validate
               │
               ▼
        Python Object
               │
               ▼
         Application
```

---

## Pydantic vs JSON vs Output Parser

| Pydantic       | JSON             | Output Parser       |
| -------------- | ---------------- | ------------------- |
| Defines schema | Data format      | Converts LLM output |
| Validates data | Stores data      | Parses & validates  |
| Python library | Universal format | Framework component |

Easy way to remember:

> **Pydantic defines.**

> **JSON transports.**

> **Output Parser converts and validates.**

---

## Structured Outputs in RAG

Instead of

```text
LLM

↓

Answer
```

RAG applications often return

```json
{
  "answer":"...",
  "source":"doc1.pdf",
  "page":18,
  "confidence":0.92
}
```

This allows applications to

* display citations
* audit responses
* verify sources
* integrate with downstream APIs

---

## Interview Q&A

### What are Structured Outputs?

Structured outputs force an LLM to generate responses that conform to a predefined schema such as JSON or a Pydantic model, making the output reliable for software systems.

---

### Why are Structured Outputs needed?

Because LLMs naturally produce free-form text, while applications require predictable, machine-readable data.

---

### What is Pydantic?

Pydantic is a Python library that defines and validates structured data models, ensuring the LLM output satisfies the expected schema before it is used.

---

### What is JSON Schema?

JSON Schema is a specification that describes the structure, required fields and data types of JSON documents.

---

### Does the LLM understand Python?

Not directly.

Frameworks convert Pydantic models into JSON Schema, which is then used to guide generation.

---

### What happens if validation fails?

The application can:

* retry generation
* repair JSON
* return an error
* ask the LLM to regenerate

---

### What does an Output Parser do?

It injects formatting instructions, parses the response, validates it and may repair malformed outputs.

---

### Why not parse text manually?

Manual parsing is fragile.

Small wording changes can break the application.

Structured outputs provide a stable contract.

---

### Can Structured Outputs eliminate hallucinations?

No.

They guarantee **structure**, not **truthfulness**.

A perfectly structured JSON response can still contain incorrect facts.

---

### Why are Structured Outputs useful in RAG?

They allow answers to include structured citations, confidence scores, document IDs and other metadata that downstream systems can consume.

---

## Common Interview Traps

❌ Structured Output guarantees factual correctness.

✔ Incorrect.

It guarantees format, not correctness.

---

❌ JSON and Pydantic are the same.

✔ JSON is a data format.

Pydantic is a Python validation library.

---

❌ Output Parser is Pydantic.

✔ Output Parser uses Pydantic but also injects prompts, parses and validates.

---

❌ LLM returns Python objects.

✔ LLM returns text.

Frameworks convert that text into Python objects.

---

## Remember These Forever

Structured Output

↓

Predictable Responses

---

Pydantic

↓

Defines & validates schema

---

JSON

↓

Data exchange format

---

Output Parser

↓

Prompts

↓

Parses

↓

Validates

↓

Repairs

---

Structured Output guarantees

**format**

NOT

**truthfulness**

---

Most modern GenAI applications use Structured Outputs for:

* APIs
* Databases
* Agents
* Tool Calling
* Enterprise Workflows

---

## Stage 1 · Week 2 Checklist

You should now be able to explain:

- Structured Outputs
- Why they are needed
- Pydantic
- JSON Schema
- JSON Repair
- Output Parser
- Pydantic vs JSON vs Output Parser
- Complete Structured Output Architecture
- RAG use cases
- Common interview questions

---

## ⭐ One interview insight that almost no tutorial mentions

People often confuse **Structured Outputs**, **Function Calling**, and **Tool Calling**.

Think of them like this:

| Feature | Purpose |
| --- | --- |
| **Structured Output** | Force the LLM to return data in a predefined format (JSON, Pydantic, etc.). |
| **Function Calling** | Let the LLM decide which predefined function to invoke and with what arguments. |
| **Tool Calling** | A broader concept where the LLM can interact with external capabilities (functions, APIs, databases, calculators, search, etc.). |


An easy mental model is:

```text
Structured Output
        │
        ▼
Produces clean data

Function Calling
        │
        ▼
Chooses which function to execute

Tool Calling
        │
        ▼
Interacts with external systems
```

Many engineers mix these up in interviews. Being able to clearly distinguish them is a strong signal that you understand modern AI application architectures rather than just individual libraries.