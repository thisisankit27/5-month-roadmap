# Java OOP: Constructor Chaining, Abstract Classes & Composition over Inheritance

------------------------------------------------------------------------

> **Goal of this Chapter**
> This is not "here's the `super` keyword's syntax." It's about what the compiler silently does for you at every constructor call, and why the most repeated advice in OOP — "favor composition over inheritance" — is a coupling argument, not a style preference.

## Crisp Definition

**Constructor chaining guarantees a fully-initialized parent before a child object exists; composition replaces "is-a" coupling to a parent class with "has-a" coupling to a swappable collaborator, wherever inheritance would model the relationship incorrectly.**

------------------------------------------------------------------------

## `super` — Referencing the Immediate Parent

### Engineering Problem

A child class often needs to reach a parent's field, method, or constructor — but a bare reference to a shadowed field or overridden method name resolves to the *child's* version. Something has to unambiguously mean "the parent's, not mine."

### Definition

`super` provides a reference to the **immediate superclass** and is used to access its members (fields, methods, or constructors).

```text
this  → current class
super → immediate parent class
```

### Engineering Insight

`this` and `super` are both *reference selectors*, not objects in their own right — they exist purely to disambiguate which version of a member the compiler should resolve, at the two points where ambiguity is possible: shadowing (fields/methods) and construction (constructors).

------------------------------------------------------------------------

## Constructor Chaining and the Default Constructor

### Engineering Problem

A child object's inherited state lives in the parent portion of the object. If the child's constructor ran before the parent's had initialized that portion, the child could read or mutate garbage/default values before the parent ever set them up.

### Definition

**Constructor chaining** is the process of calling constructors from child → parent, so the parent object is always fully initialized before the child's own constructor body runs.

### Case 1 — Parent Has a Default Constructor

If a parent class has a default (no-argument) constructor, and the child class does not define any constructor, the compiler:

- automatically creates a default constructor for the child, and
- that constructor implicitly calls `super()` as its first statement.

```java
class Parent {
    Parent() { }
}

class Child extends Parent {
    // implicit default constructor
    // Child() { super(); }
}
```

### Case 2 — Parent Has Only Parameterized Constructors

If the parent class defines only parameterized constructors (no default constructor):

- the compiler **cannot** insert `super()` automatically — there's no zero-argument parent constructor to call,
- the child class **must** explicitly define a constructor, and
- that constructor **must** explicitly call `super(arguments)`.

```java
class Parent {
    Parent(int x) { }
}

class Child extends Parent {
    Child(int x) {
        super(x);   // mandatory
    }
}
```

### Why `super(...)` Must Be the First Statement

If any code could run before `super(...)`, that code could read or modify inherited fields before the parent constructor has set them — the object would briefly exist in a state where its own parent portion isn't initialized yet. Forcing `super(...)` first guarantees the parent object is fully initialized before the child accesses or modifies inherited state.

### Rules to Remember

- Every constructor must call a parent constructor.
- If not written explicitly, the compiler inserts `super()`.
- `super(...)` must be the first statement in a constructor.
- This chain of calls, child → parent, is **constructor chaining**.

### Engineering Insight

This is the compiler enforcing an invariant you'd otherwise have to remember by hand: **base state before derived state**, every time, with no way to opt out. It's the same ordering guarantee RAII/initialization-list languages provide — Java just makes it a compile error to violate instead of a runtime bug.

------------------------------------------------------------------------

## Abstract Class vs. Interface

### Engineering Problem

Sometimes related classes need *both* a shared contract *and* shared implementation (e.g. every `Shape` needs `area()`, but they might all share the same `describe()` logic). A pure interface forces every implementer to rewrite that shared logic; a concrete base class forces single inheritance where multiple unrelated contracts might be needed.

### Definition

A **contract defines what must be provided, not how it is implemented.**

```text
Interface      → contract only
Abstract class → contract + partial implementation
```

### Abstract Class vs. Interface — When to Use Which

| Interface | Abstract Class |
|---|---|
| Pure contract, no shared implementation | Contract **plus** shared/common behavior |
| Class can implement many interfaces | Class can extend only one abstract class |
| Unrelated classes need the same capability | Related classes share real code, not just a signature |
| No shared state between implementers | Can hold shared fields and constructors |

### Engineering Insight

Use interfaces for pure contracts with no shared implementation, and abstract classes when you want to share common behavior while still enforcing subclass-specific implementations. The choice tracks a real design question — "do these types share *behavior*, or only a *shape*?" — not a syntax preference.

------------------------------------------------------------------------

## Prefer Composition over Inheritance

### Engineering Problem

Inheritance (**is-a**) makes the child depend on everything the parent does, forever:

- the child inherits *all* parent behavior, even behavior it doesn't want,
- the relationship creates tight coupling between child and parent,
- any change to the parent can silently break every child.

Extending a class is sometimes chosen purely for code reuse, without the "is-a" relationship actually being true.

### Example 1 — Inheritance Used Incorrectly

```java
class Engine {
    void start() {
        System.out.println("Engine started");
    }
}

class Car extends Engine {
}
```

**Problem:**

- `Car` is **not** an `Engine` — `Car` *has* an engine.
- `Car` now inherits all `Engine` behavior, wanted or not.
- If `Engine` changes, `Car` is affected, even though `Car` never asked for that dependency.
- ❌ Violates real-world modeling, ❌ tight coupling.

### The Same Problem Solved with Composition (has-a)

```java
class Engine {
    void start() {
        System.out.println("Engine started");
    }
}

class Car {
    private Engine engine = new Engine();   // has-a

    void startCar() {
        engine.start();
    }
}
```

**Why this is better:**

- `Car` **has an** `Engine` — an accurate model of the real relationship.
- The `Engine` implementation can be replaced later without touching `Car`'s public shape.
- No unnecessary inheritance, no unwanted behavior leaking through.
- ✔ Flexible, ✔ real-world accurate.

### Example 2 — Behavior Change at Runtime

**Inheritance (rigid):**

```java
class Bird {
    void fly() {
        System.out.println("Flying");
    }
}

class Penguin extends Bird {
    // Penguin cannot fly ❌
}
```

**Problem:** `Penguin` inherits `fly()` it shouldn't have. Fixing it needs hacks (throwing an exception, overriding to a no-op) — the design itself is broken, because "all birds fly" was never actually true.

**Composition (flexible) — the behavior becomes a swappable collaborator:**

```java
interface FlyBehavior {
    void fly();
}

class CanFly implements FlyBehavior {
    public void fly() {
        System.out.println("Flying");
    }
}

class CannotFly implements FlyBehavior {
    public void fly() {
        System.out.println("Cannot fly");
    }
}

class Bird {
    private FlyBehavior flyBehavior;

    Bird(FlyBehavior flyBehavior) {
        this.flyBehavior = flyBehavior;
    }

    void fly() {
        flyBehavior.fly();
    }
}

Bird sparrow = new Bird(new CanFly());
Bird penguin = new Bird(new CannotFly());
```

**Why this wins:**

- No incorrect inheritance — `Penguin` never falsely claims to be able to fly.
- Behavior is **pluggable** — injected at construction, per instance.
- Behavior changes without modifying the `Bird` class itself.

### Inheritance (is-a) vs. Composition (has-a)

| Inheritance (is-a) | Composition (has-a) |
|---|---|
| Child `extends` parent | Class **uses** another class via a field |
| Inherits all behavior, wanted or not | Only exposes the behavior it explicitly delegates to |
| Tight coupling — parent changes ripple to every child | Loose coupling — the collaborator can be swapped |
| Behavior fixed at compile time | Behavior can be changed/swapped at runtime |
| Breaks when the relationship isn't truly "is-a" | Models "has-a" / "uses-a" accurately |

### Engineering Insight

The `FlyBehavior` example *is* the **Strategy Pattern**: the algorithm (how to fly, or not) is extracted into its own interface and injected, so `Bird` depends on a contract rather than owning the decision itself. This is what "composition over inheritance" cashes out to concretely — not "avoid `extends`," but "don't let a parent class's total behavior leak into a child that only needed part of it, or none of it."

------------------------------------------------------------------------

## Interview Q&A

### What does `super` refer to, and how is it different from `this`?

`super` refers to the immediate superclass — used to access its fields, methods, or constructors. `this` refers to the current object. Both exist to disambiguate which version of a member the compiler should resolve when there's a naming conflict.

### What happens if a child class defines no constructor at all, and the parent has a no-arg constructor?

The compiler generates a default constructor for the child that implicitly calls `super()` as its first statement — constructor chaining happens automatically.

### What happens if the parent class only has parameterized constructors?

The compiler cannot auto-insert `super()`, since there's no no-arg parent constructor to call. The child must explicitly define a constructor that calls `super(arguments)` itself, or the code fails to compile.

### Why must `super(...)` be the first statement in a constructor?

To guarantee the parent portion of the object is fully initialized before the child constructor body can read or modify any inherited state — otherwise the child could act on a half-constructed parent.

### What's the difference between an interface and an abstract class?

An interface is a pure contract with no shared implementation, and a class can implement many of them. An abstract class can hold shared implementation and state alongside its contract, but a class can only extend one.

### Why is "Car extends Engine" a bad design?

Because `Car` is not a kind of `Engine` — it *has* one. Modeling it as inheritance forces `Car` to inherit all of `Engine`'s behavior unconditionally and couples `Car` to every future change in `Engine`, when the real relationship is "uses," not "is."

### Why can't `Penguin extends Bird` model flightless birds cleanly?

Because it inherits `fly()` regardless of whether flying is true for that subclass — fixing it requires overriding to a no-op or throwing, which is a symptom that the hierarchy encodes something that isn't actually universally true of all `Bird`s.

### What pattern does injecting `FlyBehavior` into `Bird` implement?

The Strategy Pattern — the varying behavior (fly or don't) is extracted into its own interface and supplied to `Bird` at construction, instead of being hardcoded into the class hierarchy.

### Is "prefer composition over inheritance" an absolute rule?

No — it's a coupling argument: use inheritance when "is-a" is genuinely true and shared implementation makes sense; use composition when you only need to reuse or vary a piece of behavior without genuinely being a subtype of the thing providing it.

------------------------------------------------------------------------

❌ `super()` is optional — you only need it if you want to call the parent's constructor.

✔ Every constructor calls a parent constructor, always — either explicitly, or via a compiler-inserted `super()`. It's never actually optional; it's sometimes just invisible.

------------------------------------------------------------------------

❌ If the parent class has *any* constructor, the compiler will auto-generate the child's default constructor.

✔ Auto-generation only works if the parent has a **no-argument** constructor. A parent with only parameterized constructors forces the child to write an explicit constructor calling `super(arguments)`.

------------------------------------------------------------------------

❌ Abstract classes and interfaces are interchangeable — pick whichever is convenient.

✔ They answer different questions: interface = "what capability, no shared code"; abstract class = "what capability, plus shared implementation." The choice should follow whether real behavior is actually shared.

------------------------------------------------------------------------

❌ "Favor composition over inheritance" means never use `extends`.

✔ It means don't use inheritance just for code reuse when the "is-a" relationship isn't actually true — inheritance is still correct when the subtype relationship genuinely holds.

------------------------------------------------------------------------

## What You Should Remember Forever

```text
super              → immediate parent's fields/methods/constructor
this               → current object

Constructor chaining → child constructor always calls a parent
                        constructor first, explicit or compiler-inserted

super(...)          → must be the first statement, always

Interface            → contract only
Abstract class       → contract + shared implementation

Car extends Engine   → wrong: Car HAS an engine, isn't one
Penguin extends Bird → wrong: not every Bird can fly

Composition          → swap behavior via injected collaborators
                        (Strategy Pattern), instead of baking it
                        into a rigid class hierarchy
```

------------------------------------------------------------------------

## Stage 2 · Week 1 Checklist

- [x] Explain what `super` refers to and how it differs from `this`
- [x] Explain constructor chaining and when the compiler auto-inserts `super()`
- [x] Explain why `super(...)` must be the first statement in a constructor
- [x] Explain the difference between an abstract class and an interface, and when to use each
- [x] Explain why `Car extends Engine` is a modeling mistake
- [x] Explain why `Penguin extends Bird` breaks down for flightless birds
- [x] Explain how composition fixes both examples, and name the pattern it implements
- [x] Explain "prefer composition over inheritance" as a coupling argument, not a blanket rule
