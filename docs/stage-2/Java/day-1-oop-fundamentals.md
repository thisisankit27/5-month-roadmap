# Java OOP: Access Control, Static, Final & Polymorphism

------------------------------------------------------------------------

> **Goal of this Chapter**
> This is not a keyword glossary — `private`, `static`, and `final` are not syntax to memorize, they're the compiler's answer to specific engineering problems (data integrity, shared state, thread safety, dispatch ambiguity). The goal is to be able to say *why* each rule exists, not just *what* it does.

## Crisp Definition

**Encapsulation, access control, `static`, `final`, and polymorphism are the mechanisms Java gives a class to control who can see its state, who can change it, and which implementation runs when a call is ambiguous.**

------------------------------------------------------------------------

## Encapsulation and Access Modifiers

### Engineering Problem

Without any access control, every field is directly mutable from anywhere in the codebase. Any caller can set an object into an invalid state — a negative balance, a null required field — with no chance for the class to reject it.

### Definition

**Data Hiding** makes fields `private` and exposes controlled access through public `getters()`/`setters()`. The setter is the enforcement point — it can validate before mutating state.

### Why Access Modifiers Are for Data Integrity, Not Security

A `private` field is not a security boundary — anyone with the source (or reflection) can read it. What it *does* guarantee is that all mutation goes through one method, so the class can enforce its own invariants. That's an integrity guarantee, not a confidentiality one.

### Engineering Insight

This is **Information Hiding** (Parnas) applied at the field level: the class exposes *what* callers can do (`setBalance(amount)`), not *how* state is stored — so the internal representation can change without breaking callers.

------------------------------------------------------------------------

## The `protected` Modifier

### Engineering Problem

`public` exposes a member everywhere; `private` hides it everywhere. Neither models the common case of "a subclass should inherit this, but strangers shouldn't touch it" — that needs a modifier aware of the *inheritance relationship*, not just the package boundary.

### Definition

`protected` accessibility depends on both package and class relationship:

```text
Same Package
├── Any class   → ✔ access
└── Subclass    → ✔ access

Different Package
├── Subclass    → ✔ access
└── Non-child   → ✘ no access
```

### Why the Split?

Within the same package, Java already trusts every class equally (that's what package-private means), so `protected` behaves like `public` there. Across packages, the only trust relationship left is inheritance — so access narrows to subclasses only.

### Engineering Insight

`protected` is Java's way of saying "this is part of the extension contract, not the public API" — it's for framework/base-class authors who want subclasses to reach into state that outside callers shouldn't.

------------------------------------------------------------------------

## `final` — Immutability and Thread Safety

### Engineering Problem

A **race condition** occurs when multiple threads access and modify shared data concurrently, and the final outcome depends on the timing or order of execution of those threads. Mutable shared state is what makes a race condition possible in the first place.

### Definition

`final` prevents a variable from being reassigned after initialization (for references: the reference is fixed, not necessarily the referenced object's internal state).

### Why `final` Prevents Race Conditions

If a field can never be reassigned after construction, there's no write for a second thread to race against — reads from multiple threads of a value that never changes are inherently safe. `final` promotes immutability, making shared objects **thread-safe by design**.

### Engineering Insight

This is the same reasoning behind favoring immutable value objects generally: the cheapest way to make code thread-safe isn't better locking, it's removing the mutation that needed locking in the first place.

------------------------------------------------------------------------

## `static` — Class-Level State and Behavior

### Engineering Problem

Some data and behavior belongs to the *class*, not to any one instance — a counter of how many objects exist, a utility calculation that needs no object state. Forcing every caller to instantiate an object just to run a stateless calculation is unnecessary coupling.

### Definition

A `static` member belongs to the class itself; it exists and can be accessed without creating an object.

### Why a Static Method Can't Access Non-Static Members

A static method runs without any object — it's invoked as `ClassName.method()`, not `instance.method()`. Instance members only exist *because* an object was constructed, so there is no guaranteed instance for the static method to read from.

```java
class Test {
    int x = 10;      // instance variable
    static int y = 20;

    static void show() {
        System.out.println(x);        // compile-time error — no instance to read x from
        Test obj = new Test();
        System.out.println(obj.x);    // OK — object exists
        System.out.println(y);        // OK — y belongs to the class, not an instance
    }
}
```

### Engineering Insight

This is the same distinction as class-level vs. instance-level data anywhere: `static` is appropriate exactly when the data/behavior has no dependency on per-instance state. Reach for it too often, though, and you end up with global mutable state under a different name — the same coupling and testability problems as any other global.

------------------------------------------------------------------------

## Interfaces and Polymorphism

### Engineering Problem

Different classes need to be usable interchangeably by code that only cares about *what* they can do, not *how* they do it — e.g. any `PaymentProcessor`, regardless of whether it's Stripe or PayPal underneath. Without a shared contract, calling code has to know every concrete type it might receive.

### Definition

An **Interface** is a skeleton for classes — it specifies *what* a class must do, not *how*. A class `implements` one or more interfaces and must `@Override` and provide implementations for every abstract method the interface declares. This is enforced **at compile time**.

You cannot instantiate an interface directly — only hold a reference to an object of an implementing class.

### Class vs. Interface — When to Use Which

| Use a Class | Use an Interface |
|---|---|
| You need shared implementation/state between related types | You only need to guarantee a contract/capability |
| The "is-a" relationship is a true hierarchy | Unrelated classes need the same capability (e.g. `Comparable`) |
| Single inheritance is sufficient | A type needs to satisfy multiple contracts at once |

### Engineering Insight

Interfaces are what make **polymorphism** possible without inheritance: two classes with nothing in common except implementing the same interface can still be swapped for each other by any code that programs against the interface type.

------------------------------------------------------------------------

## Inheritance — Reference Type vs. Object Type

### Engineering Problem

When a parent-class reference points at a child-class object, which method set is the caller allowed to see — the parent's, or the (possibly extended) child's? Getting this wrong either breaks encapsulation or breaks the compiler's ability to catch mistakes early.

### Definition

When a parent class reference refers to a child class object, the reference can only call methods **declared in the parent class**. (If a method is *declared* in the parent and *overridden/defined* in the child, this works fine — that's normal polymorphism.)

### Why: Compile-Time Reference vs. Runtime Object

Method accessibility is checked at **compile time**, and the compiler looks at the **reference type**, not the object type:

```text
Reference type → what methods you can call     (compile time)
Object type    → which implementation runs     (runtime)
```

```text
➡ Compile-time : method must exist on the declared (reference) type
➡ Runtime      : the overridden method is dispatched dynamically
```

### Why This Split Exists

If the compiler checked against the object's *runtime* type, it couldn't verify method calls until the program actually ran — defeating the point of static typing. Checking against the *reference* type lets the compiler catch invalid calls immediately, while dynamic dispatch still lets the correct override run.

### Engineering Insight

This is exactly **why you code against interfaces/abstract types**: the reference type is a contract the compiler enforces early, while the object type is free to vary — which is what makes polymorphism substitutable and testable (swap the object, keep the contract).

------------------------------------------------------------------------

## Visibility Rules for Top-Level Types

### Engineering Problem

`private` works for fields and methods — but does "private to what?" even make sense for an entire top-level `class` or `interface`? Getting this wrong would mean either types can be hidden from their own package (breaking normal package-level collaboration) or the concept of "private type" is meaningless and shouldn't compile at all.

### Why Java Disallows `private` on Top-Level Types

A top-level type (class or interface) is already a package member — it lives directly inside a package, and the package boundary is already the *minimum* visibility scope Java offers. So Java asks: **"private to what?"** There is no enclosing class to hide it inside, so the modifier has nothing to attach to.

### Where `private` *Is* Allowed

`private` is legal only **inside a class** — on a nested type, because a nested type has an enclosing scope to be private *to*.

```java
class Outer {
    private interface InnerContract {
        void doWork();
    }

    class InnerImpl implements InnerContract {
        public void doWork() {}
    }
}
```

`InnerContract` is private to `Outer` — this makes sense because `Outer` *is* the enclosing scope.

### Visibility Matrix

| Modifier | Top-Level Types (class / interface) | Members Inside a Class |
|---|---|---|
| `public` | ✔ | ✔ |
| *(nothing)* — package-private | ✔ | ✔ |
| `protected` | ✘ | ✔ |
| `private` | ✘ | ✔ |

The gap is the point: `protected` and `private` are both meaningless at the top level because both need something narrower than "the package" to be relative to, and a top-level type has nothing narrower available.

### Why Outer Classes Can't Be `private`

- A top-level class already belongs to a package.
- Marking it `private` would make it inaccessible to **every** other class, including ones in its own package — there's no enclosing scope for "private" to mean anything less extreme than that.
- Hence Java disallows `private` for outer classes.

### Private Inner Classes (the Exception That Proves the Rule)

A private inner class *can* exist — because it has an enclosing class to be private to. It is accessible only within the enclosing class, and completely hidden from outside code:

```java
public class PublicOuterClass {
    private class PrivateInnerClass {
        public String name;
        public String id;
    }
}
```

### Engineering Insight

The rule generalizes: **an access modifier is only meaningful relative to some enclosing scope.** A package is the outermost scope Java has, so no modifier can be more restrictive than "the package" at that level — restriction requires something to be restricted *within*.

------------------------------------------------------------------------

## `Object` — The Root Class in Java

### Definition

`java.lang.Object` is the superclass of all classes in Java. Every class implicitly extends `Object`; if a class does not explicitly extend another class, it automatically extends `Object`.

### Engineering Insight

This is what guarantees every Java object — regardless of type — has a baseline contract (`equals`, `hashCode`, `toString`, `getClass`, ...). Collections, reflection, and logging all lean on this guarantee; without a universal root type, generic containers like `ArrayList` couldn't hold arbitrary objects uniformly.

------------------------------------------------------------------------

## Why `main()` Is `static`

### Engineering Problem

The JVM has to invoke your program's entry point before any of your code has run — which means before any object of your class exists. Something has to be callable with zero prior state.

### Core Reason

`main()` is `static` so the JVM can invoke it without creating an object of the class first (`Main.main(args)`).

### What If `main()` Were Not Static?

The JVM would have to construct an instance first, and immediately hit unanswerable questions:

- Which constructor should it call?
- What if the constructor needs arguments?
- What if object creation has side effects?

Too many unknowns — not allowed.

### Engineering Insight

This is the same reasoning as `static` generally, applied to the most fundamental case: `main()` has no natural instance to belong to, because instances don't exist yet when it needs to run.

------------------------------------------------------------------------

## Interview Q&A

### Is `private` about security?

No — it's about data integrity. It guarantees all mutation goes through the class's own methods, which can enforce invariants; it does not stop determined access via reflection.

### Why can a `protected` member be accessed by any class in the same package, not just subclasses?

Because within a package, Java already treats all classes as trusted collaborators (that's the meaning of package-private). `protected` only narrows to "subclass only" once you cross a package boundary, where inheritance is the sole remaining trust relationship.

### How does `final` prevent race conditions?

A race condition requires a shared, mutable write that another thread can observe mid-change. `final` removes the write entirely after construction — with nothing left to mutate, concurrent reads are inherently safe.

### Why can't a static method access instance variables directly?

A static method can run without any object existing. Instance variables only exist once an object has been constructed, so there's no guaranteed instance for the static method to read from — it would need an explicit object reference instead.

### Can you have an object of an interface type?

No — you can only hold a *reference* of an interface type pointing at an object of an implementing class. The interface itself has no implementation to instantiate.

### When a parent-type reference points at a child object, which methods can you call?

Only the methods declared on the parent (reference) type — checked at compile time. Which *implementation* actually runs (parent's or the child's override) is resolved at runtime, based on the object's actual type.

### Why does Java disallow `private` on a top-level class?

Because `private` needs an enclosing scope to be private *to*, and a top-level type's enclosing scope is the package itself — the widest scope Java has, not a narrower one. There's nothing to restrict it within.

### Why is a private inner class legal when a private outer class isn't?

The inner class has an enclosing class (`Outer`) to be private to; the outer class's only "enclosing" context is the package, and hiding a type from its own package defeats the purpose of package membership.

### Why is `main()` static?

Because the JVM must invoke it before any object of the class exists — a non-static `main()` would require the JVM to first decide how to construct an instance, with no way to resolve which constructor, what arguments, or what side effects that construction should have.

### What does every Java class inherit from, even with no explicit `extends`?

`java.lang.Object` — every class implicitly extends it unless it explicitly extends something else (which itself ultimately traces back to `Object`).

------------------------------------------------------------------------

❌ Access modifiers exist to keep data secure from malicious actors.

✔ They exist for data integrity — enforcing that a class's own invariants are respected on every mutation. Reflection and decompilation can still bypass `private` entirely.

------------------------------------------------------------------------

❌ `protected` means "only subclasses can access this."

✔ `protected` means "subclasses, plus anything in the same package" — package membership alone is enough within the same package.

------------------------------------------------------------------------

❌ `final` just stops you from reassigning a variable — it's a syntax convenience.

✔ `final` is a concurrency tool: removing reassignment removes the write side of a race condition, making shared immutable state safe by construction.

------------------------------------------------------------------------

❌ A parent-type reference to a child object calls the child's *full* API.

✔ It calls only what the parent type declares — the reference type gates *what* you can call at compile time; the object type only decides *which implementation* runs for methods that exist on the reference type.

------------------------------------------------------------------------

❌ You could make a top-level class `private` if you really wanted stricter hiding.

✔ Java disallows it categorically — there's no enclosing scope narrower than the package for a top-level type to be private to.

------------------------------------------------------------------------

## What You Should Remember Forever

```text
Access modifiers        → data integrity, not security
protected                → package OR subclass
final                    → no reassignment → no race condition
static                   → belongs to the class, not any instance
Interface                → contract, enforced at compile time, no direct instantiation
Reference type           → what you can call   (compile time)
Object type              → what actually runs  (runtime)
private on a type        → only legal when there's an enclosing class to be private to
main() is static         → the JVM calls it before any object exists
Every class               → implicitly extends java.lang.Object
```

------------------------------------------------------------------------

## Stage 2 · Week 1 Checklist

- [x] Explain why access modifiers are for data integrity, not security
- [x] Explain why `protected` grants access to the whole package, not just subclasses
- [x] Explain how `final` prevents race conditions
- [x] Explain why a static method can't directly access instance members
- [x] Explain why you can't instantiate an interface, only reference one
- [x] Explain the difference between reference type (compile time) and object type (runtime) in method dispatch
- [x] Explain why Java disallows `private` on top-level classes/interfaces
- [x] Explain why a private *inner* class is legal when a private *outer* class isn't
- [x] Explain why `main()` must be `static`
- [x] State what every Java class implicitly extends
