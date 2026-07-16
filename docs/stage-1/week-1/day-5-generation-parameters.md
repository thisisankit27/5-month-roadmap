# Generation Parameters

## What are Generation Parameters?

Generation parameters control **how a Large Language Model (LLM) generates text** after receiving a prompt.
Unlike Retrieval parameters (which determine *what information* reaches the LLM), Generation parameters determine *how the response is generated*.

Pipeline

```text
User Query

↓

Retriever (Optional)

↓

Retrieved Context

↓

Prompt

↓

LLM

↓

Generation Parameters

↓

Response
```

---

## Why are Generation Parameters Important?

The same prompt can produce very different outputs depending on the chosen parameters.

Example

Prompt

```
Write a story about a dragon.
```

Low Temperature

↓

```
A factual and predictable story.
```

High Temperature

↓

```
A creative, imaginative fantasy story.
```

Choosing the correct parameters improves:

- Response quality
- Creativity
- Consistency
- Reliability
- Token usage

---

## Temperature

### Definition

Temperature controls the **randomness** of token selection. Lower values make responses more deterministic. Higher values increase creativity.

---

### How it works

The LLM predicts probabilities for the next token.

Example

| Token | Probability |
|--------|------------:|
| Java | 60% |
| Spring | 25% |
| Python | 10% |
| Rust | 5% |

With

```
Temperature = 0
```

the model almost always chooses

```
Java
```

With

```
Temperature = 1
```

the model becomes more willing to choose

```
Spring

Python

Rust
```

---

#### Temperature = 0

Characteristics

- Deterministic
- Repeatable
- Fact-oriented

Best For

- RAG
- Coding
- Technical writing
- Legal
- Medical

Example

Question

```
Benefits of exercise?
```

Response

```
Exercise improves cardiovascular health, increases muscle strength, and reduces the risk of chronic diseases.
```

---

#### Temperature = 1

Characteristics

- Creative
- Diverse
- Less predictable

Best For

- Story writing
- Poetry
- Brainstorming
- Marketing

Example

```
Exercise is the ritual where determination transforms sweat into strength and every heartbeat becomes a celebration of life.
```

---

#### Typical Values

| Task | Temperature |
|------|------------:|
| Coding | 0–0.2 |
| RAG | 0.1–0.3 |
| Chatbot | 0.5 |
| Brainstorming | 0.7 |
| Creative Writing | 0.8–1.2 |

---

## Top-p (Nucleus Sampling)

### Definition

Top-p limits token selection to the **smallest set of tokens whose cumulative probability exceeds p**. Instead of controlling randomness, it controls **how many candidate tokens are considered**.

---

## Example

Token probabilities

| Token | Probability |
|--------|------------:|
| Java | 0.50 |
| Spring | 0.25 |
| Python | 0.15 |
| Rust | 0.07 |
| Go | 0.03 |

---

### Top-p = 0.75

Allowed

```
Java

Spring
```

because

```
0.50 + 0.25 = 0.75
```

Everything else is discarded.

---

### Top-p = 0.95

Allowed

```
Java

Spring

Python

Rust
```

The model now has more choices.

---

## Best Uses

Higher Top-p

- More diverse responses

Lower Top-p

- More focused responses

---

## Top-k Sampling
!!! Warning
    > **Note:** This is different from **Top-K Retrieval** in RAG.

---

### Definition

Top-k limits generation to the **k highest-probability tokens**.

Example

```
Top-k = 3
```

Only

```
Java

Spring

Python
```

can be selected.

Everything else is ignored.

---

### Difference

Top-k

↓

Fixed number of candidate tokens.

Top-p

↓

Variable number of candidate tokens based on cumulative probability.

---

## Top-k vs Top-p

| Top-k | Top-p |
|--------|--------|
| Fixed number of tokens | Dynamic candidate set |
| Easier to understand | More adaptive |
| Less commonly tuned | More commonly used |

---

## Temperature vs Top-p

| Temperature | Top-p |
|-------------|-------|
| Controls randomness | Controls candidate pool |
| Changes probability distribution | Filters candidate tokens |
| Higher = More creative | Higher = More diverse |

---

## Common Combinations

| Temperature | Top-p | Result |
|-------------|------:|--------|
| Low | Low | Very deterministic |
| Low | High | Accurate with richer vocabulary |
| High | Low | Slightly unusual wording |
| High | High | Highly creative and unpredictable |

---

## Max Tokens

### Definition

Specifies the maximum number of tokens the model may generate.

Example

```
Max Tokens = 100
```

↓

The response stops after approximately 100 generated tokens.

---

### Why?

- Control API cost
- Reduce latency
- Prevent extremely long responses

---

## Frequency Penalty

### Definition

Discourages the model from repeating the same tokens frequently.

Example

Without Penalty

```
Java is powerful.

Java is popular.

Java is scalable.

Java...
```

With Frequency Penalty

```
Java is powerful.

It is widely used in enterprise applications and supports scalable software development.
```

---

### Best Uses

- Long-form writing
- Summarization
- Chatbots

---

## Presence Penalty

### Definition

Encourages the model to introduce **new topics or vocabulary**. Unlike Frequency Penalty, it rewards discussing concepts that haven't appeared yet.

---

### Example

Without Presence Penalty

```
Spring Boot

Spring Boot

Spring Boot
```

With Presence Penalty

```
Spring Boot

Dependency Injection

Microservices

REST APIs
```

---

### Difference

Frequency Penalty

↓

Avoid repeating the same words.

Presence Penalty

↓

Encourage introducing new concepts.

---

## Stop Sequences

### Definition

A Stop Sequence tells the model where to stop generating.

Example

```
Stop = "END"
```

Generated

```
Hello

END

Ignored Text...
```

Final Output

```
Hello
```

---

### Applications

- JSON generation
- Structured outputs
- Tool calling
- Multi-agent workflows

---

## Recommended Settings

| Task | Temperature | Top-p | Max Tokens |
|------|------------:|------:|-----------:|
| RAG | 0.1–0.3 | 0.9–1.0 | Moderate |
| Coding | 0–0.2 | 1.0 | Moderate |
| Chatbot | 0.5 | 0.9 | Medium |
| Creative Writing | 0.8–1.2 | 0.95–1.0 | High |
| Brainstorming | 0.9 | 1.0 | High |

---

## Interview Questions

### What is Temperature?

**Answer**

Temperature controls the randomness of token generation. Lower values produce deterministic and factual responses, while higher values increase creativity and diversity.

---

### What is Top-p?

**Answer**

Top-p (Nucleus Sampling) limits token selection to the smallest set of tokens whose cumulative probability exceeds a threshold, balancing diversity and coherence.

---

### Difference between Temperature and Top-p?

**Answer**

Temperature modifies the probability distribution, making token selection more or less random.
Top-p filters the candidate tokens before sampling by keeping only the most probable cumulative set.

---

### What is Top-k Sampling?

**Answer**

Top-k limits generation to the k highest-probability candidate tokens. Unlike Top-p, the number of candidate tokens is fixed.

---

### Difference between Top-k Retrieval and Top-k Sampling?

**Answer**

Top-k Retrieval is a **RAG retrieval parameter** that determines how many documents are returned from the Vector Database.

Top-k Sampling is an **LLM generation parameter** that limits how many candidate tokens the model can choose from while generating text.

---

### What is Max Tokens?

**Answer**

Max Tokens limits the maximum length of the generated response, helping control latency and API cost.

---

### Difference between Frequency Penalty and Presence Penalty?

**Answer**

Frequency Penalty discourages repeated words or phrases.

Presence Penalty encourages the model to introduce new topics and vocabulary.

---

### Which settings would you choose for a RAG application?

**Answer**

Typically:

- Temperature: 0.1–0.3
- Top-p: 0.9–1.0
- Moderate Max Tokens

The goal is to generate factual, grounded responses while allowing enough flexibility for natural language generation.

---

## Key Takeaways

- Generation parameters control **how** the LLM generates text.
- Temperature controls randomness.
- Top-p controls the candidate token pool.
- Top-k sampling limits generation to a fixed number of candidate tokens.
- Max Tokens limits response length.
- Frequency Penalty reduces repetition.
- Presence Penalty encourages introducing new concepts.
- Stop Sequences provide explicit stopping points for generation.
- For RAG systems, low Temperature with a high Top-p is a common and effective configuration.