# Maven: Build Automation & Dependency Management

------------------------------------------------------------------------

> **Goal of this Chapter**
> This is not "here's the `pom.xml` tags." Maven exists because manually managing JARs doesn't scale past a handful of dependencies — the goal is to understand *which* problem each Maven mechanism (coordinates, the local repo, the lifecycle, scopes, `dependencyManagement`) solves, so version conflicts and scope choices stop looking like magic and start looking like predictable consequences of how dependency resolution actually works.

## Crisp Definition

**Maven is a build automation and dependency management tool — it resolves a project's declared dependencies (and their transitive dependencies) from a repository, and drives the project through a fixed, cumulative lifecycle of phases from compilation to deployment.**

------------------------------------------------------------------------

## Why Dependency Management Is Needed

### Engineering Problem

Before a tool manages dependencies for you, there are exactly two manual options, and both break down fast:

**1. Copy-paste code** — no versioning, no upgrade path, unmaintainable the moment the pasted code needs a fix upstream.

**2. Add external JARs manually** — now *you* manage dependency-of-dependency relationships by hand, version conflicts have no automated resolution, and you're managing classpath hell directly.

### Engineering Insight

Both manual approaches fail for the same underlying reason: they conflate "I need this code" with "I need to personally track every version and transitive requirement of this code." Maven's entire value proposition is separating those two concerns.

------------------------------------------------------------------------

## What Maven Actually Does

Maven is **not** just a dependency downloader — it's a **build + dependency management tool**, with three core purposes.

### 1. Dependency Management — the Primary Value

You declare dependencies in `pom.xml`. Maven:

- downloads them,
- downloads their **transitive dependencies** (dependencies of your dependencies),
- adds everything to the compile / test / runtime classpath, as appropriate.

### 2. Build Automation — the Lifecycle

Maven follows a fixed lifecycle:

```text
clean → validate → compile → test → package → verify → install → deploy
```

Each phase has a defined responsibility and runs plugins behind the scenes:

| Phase | Responsibility |
|---|---|
| `compile` | Compiles source code |
| `test` | Runs unit tests |
| `package` | Creates the JAR/WAR |
| `install` | Puts the artifact in the **local** repo |
| `deploy` | Pushes the artifact to a **remote** repo |

**Phases are cumulative, not isolated.** Running `mvn package` doesn't run *only* `package` — Maven automatically runs everything before it too:

```text
mvn package  →  validate → compile → test → package
```

### 3. Standard Project Structure

Maven enforces a fixed layout:

```text
src/main/java
src/test/java
target/
```

This buys tooling consistency, CI/CD compatibility, and zero-configuration builds — any Maven-aware tool knows where to look without project-specific setup.

**One-line interview summary:** *"Maven automates dependency management and the entire build lifecycle — compiling, testing, packaging, and deploying — using a standard project structure and declarative configuration."*

------------------------------------------------------------------------

## `pom.xml` Anatomy

```xml
<groupId>org.ppa</groupId>
<artifactId>MyFirstMavenProject</artifactId>
<version>1.0-SNAPSHOT</version>

<dependencies>
    <dependency>
        <groupId>org.jsoup</groupId>
        <artifactId>jsoup</artifactId>
        <version>1.10.2</version>
    </dependency>
    <dependency>
        <groupId>junit</groupId>
        <artifactId>junit</artifactId>
        <version>3.8.1</version>
        <scope>test</scope>
    </dependency>
</dependencies>
```

- `groupId`, `artifactId`, `version` → uniquely identify **your own project** (`org.ppa:MyFirstMavenProject:1.0-SNAPSHOT`).
- `<dependencies>` → lists the external libraries your project needs.
- `org.jsoup:jsoup:1.10.2` → Maven downloads the `jsoup` JAR, **including its transitive dependencies**, and adds it to the compile/runtime classpath.
- `junit:junit:3.8.1` with `<scope>test</scope>` → available only during testing, not in the production build.

**Key point:** Maven automatically downloads the required JARs (which contain compiled `.class` files) into the local repository and adds them to the appropriate classpath. You can directly import and use these libraries in code — no manual JAR handling needed.

------------------------------------------------------------------------

## How Maven Resolves a Dependency

### The Flow

```text
You add a dependency
        │
        ▼
Maven searches the Central Maven Repository (repo.maven.apache.org/maven2)
        │
        ▼
Downloads the .JAR, stores it on your system
        │
        ▼
Local Maven Repo (avoids re-downloading for every project on the machine)
```

**Remote Maven Repo** — for artifacts not available publicly. A URL (remote server) or file-system path is configured in Maven's `<repository>` settings; only allowed projects can access it.

**Local repo:** `%User%\.m2\`

The `groupId`'s dots become folder-level separators within `.m2`:

```text
org.jsoup:jsoup:1.10.2  →  org/jsoup/jsoup/1.10.2/
```

### Using a Locally Installed Project as a Dependency

Once a project (`dependencyProject`) is built with `mvn install`, its `.JAR` lands in the local repo. Another project (`MyFirstMavenProject`) can import it exactly like any external library:

```xml
<groupId>org.ppa</groupId>
<artifactId>MyFirstMavenProject</artifactId>
<version>1.0-SNAPSHOT</version>

<dependencies>
    <dependency>
        <groupId>org.ppa</groupId>
        <artifactId>dependencyProject</artifactId>
        <version>1.0-SNAPSHOT</version>
    </dependency>
</dependencies>
```

`dependencyProject`'s methods are now usable — it's already compiled and installed as a `.JAR` in the local repo.

**One-line interview summary:** *"Maven resolves dependencies using coordinates, downloads JARs from remote repositories into the local `.m2` cache, and automatically adds them to the project classpath."*

### Two Senior-Level Corrections Worth Remembering

1. `mvnrepository.com` is **not** Maven Central — it's only a catalog/search UI. The actual default repository Maven downloads from is `https://repo.maven.apache.org/maven2`.
2. Dependency resolution always checks the **local repo first**, before reaching out to any remote repository.

------------------------------------------------------------------------

## What Can Go Wrong — Version Conflicts

### Engineering Problem

Given a project `P` that depends (transitively) on the same library `C` through two different paths, at two different versions, which version should actually be used?

```text
P → B → X → C(v1.0)      [C's depth: 3]
P → A → C(v2.0)          [C's depth: 2]   ← this one wins
```

### Resolution Rule

Maven represents project dependencies as a **Directed Acyclic Graph (DAG)** and resolves conflicts by depth: the `C` found at the **lower depth (closer to the root)** wins.

If both paths reach `C` at the **same depth**, the dependency declared **first in `pom.xml`** wins:

```xml
<!-- P → B → C(v1.0)
     P → A → C(v2.0)
     Same depth → declaration order decides -->
<dependencies>
    <dependency>B</dependency>   <!-- this C(v1.0) wins -->
    <dependency>A</dependency>
</dependencies>
```

**So declaration order only matters when there's an actual depth-tie conflict.**

To force a specific version, import `C` directly into `P` at depth 1 — least depth wins, so a direct declaration always overrides a transitive one. This isn't foolproof on its own, though.

### Solutions

**1. Ask the dependency owner.** The real fix for a genuine conflict is asking the owner of `C` to publish a version whose functionality serves both callers, then forcing that version via least-depth import.

**2. `dependencyManagement` — the senior-level best practice.**

```xml
<dependencyManagement>
    <dependencies>
        <dependency>
            <groupId>C</groupId>
            <artifactId>C</artifactId>
            <version>v2.0</version>
        </dependency>
    </dependencies>
</dependencyManagement>
```

This centralizes version control for a dependency across an entire multi-module project, rather than relying on depth/declaration-order tie-breaking scattered across POMs — heavily used in large projects.

### Engineering Insight

Maven represents project dependencies as a Directed Acyclic Graph and resolves them by performing topological ordering to determine build order; it detects and rejects circular dependencies to ensure a valid build sequence. Depth-based conflict resolution is really just a deterministic tie-breaking rule layered on top of that same graph structure.

------------------------------------------------------------------------

## Dependency Scopes — Compile, Runtime, Test

### Engineering Problem

Not every dependency your project needs at runtime is one your source code directly references — and not every dependency needed for testing belongs in the shipped artifact. Treating all dependencies identically either bloats the compile classpath with things the compiler never touches, or ships test-only tooling into production.

### Default — Compile-Time Dependency

```xml
<dependencies>
    <dependency>
        ...
    </dependency>
</dependencies>
```

With no `<scope>` specified, this is a **compile-time dependency** by default — the compiler loads it directly into the compile-time classpath.

### `runtime` Scope

```xml
<dependency>
    <groupId>org.ppa</groupId>
    <artifactId>dependencyProject</artifactId>
    <version>1.0-SNAPSHOT</version>
    <scope>runtime</scope>
</dependency>
```

A runtime-scoped dependency **cannot be discovered by the compiler**, but the JVM can still work with it — typically because it's loaded dynamically via reflection (`Class.forName(...)`) rather than referenced directly by a compile-time symbol.

```java
// DependencyCheck.checker();  // ✘ Cannot resolve symbol 'DependencyCheck' — no compile-time reference

Class<?> cls = Class.forName("org.ppa.DependencyCheck");
Method m = cls.getDeclaredMethod("checked");
Object obj = cls.getDeclaredConstructor().newInstance();
m.invoke(obj);
```

This is the same reflective loading mechanism as [Class loading and dynamic instantiation](day-4-reflection.md) — `runtime` scope exists precisely for dependencies your code reaches through reflection instead of a direct import.

### When to Use `runtime` Scope — JDBC Driver Example

```xml
<dependency>
    <groupId>mysql</groupId>
    <artifactId>mysql-connector-java</artifactId>
    <scope>runtime</scope>
</dependency>
```

**Why runtime?** Your code uses:

```java
Connection con = DriverManager.getConnection(...);
```

You never directly write `new com.mysql.cj.jdbc.Driver()`. The driver is loaded dynamically at runtime, required when the app actually runs, but not needed for compilation at all — a textbook runtime dependency.

### Why Not Just Make Everything `compile` Scope?

You could — but it makes the compile classpath unnecessarily large, creates tighter coupling than the code actually has, reduces build clarity, and makes dependency management messier over time. `runtime` scope keeps the compile-time classpath clean and dependencies minimal and intentional — a dependency's scope should reflect how the code actually uses it, not just "does the project need this at all."

**Interview one-liner:** *"Runtime scope is used for dependencies required during execution but not directly referenced in source code, such as JDBC drivers or logging implementations."*

### `test` Scope

```xml
<scope>test</scope>
```

Not added to the compile-time classpath at all — only available to unit testing frameworks during the `test` phase.

### Engineering Insight

Scopes are Maven's way of encoding *when* and *how* a dependency is actually needed — compile-time symbol resolution, JVM-only dynamic loading, or test-only tooling — instead of treating "is a dependency" as a single undifferentiated category.

------------------------------------------------------------------------

## Interview Q&A

### Why isn't copy-pasting code or manually adding JARs a sustainable dependency strategy?

Copy-pasting has no versioning or upgrade path and becomes unmaintainable. Manually adding JARs forces you to track transitive dependencies, resolve version conflicts, and manage the classpath by hand — Maven exists to automate exactly this.

### Is Maven just a dependency downloader?

No — it's a build automation tool as much as a dependency manager. It also enforces a fixed lifecycle (`validate → compile → test → package → verify → install → deploy`) and a standard project structure.

### What does running `mvn package` actually execute?

Every phase up to and including `package` — `validate → compile → test → package` — because Maven's lifecycle phases are cumulative, not isolated.

### What's the difference between `mvnrepository.com` and Maven Central?

`mvnrepository.com` is only a search catalog. The actual default repository Maven downloads artifacts from is `https://repo.maven.apache.org/maven2`.

### When resolving a dependency, does Maven check the local repo or a remote repo first?

The local repo (`.m2`) is checked first — remote repositories are only contacted if the artifact isn't already cached locally.

### Given a diamond dependency conflict, how does Maven decide which version of a transitively-shared library to use?

It picks the version found at the **lowest depth** in the dependency graph (closer to the root project). If two paths reach the conflicting dependency at the same depth, the one declared **first** in `pom.xml` wins.

### What's the senior-level fix for recurring version conflicts across a multi-module project?

`<dependencyManagement>` — it centralizes the version for a given dependency in one place, instead of relying on depth/declaration-order tie-breaking scattered across POMs.

### What's the difference between compile scope and runtime scope?

Compile scope is on the compile-time classpath — the compiler can directly resolve symbols from it. Runtime scope is not visible to the compiler at all, but is available to the JVM when the application actually runs — typical for dependencies accessed via reflection rather than a direct import, like a JDBC driver.

### Why not just declare every dependency with compile scope, to be safe?

Because it bloats the compile classpath with things the compiler never actually touches, creates coupling that doesn't reflect how the code is really used, and makes dependency intent harder to read. Scope should describe *how* a dependency is used, not just whether it's needed at all.

### What does `test` scope guarantee?

That the dependency is available only to test code and testing frameworks during the `test` phase — it's excluded from the compile-time classpath and never ships in the production artifact.

------------------------------------------------------------------------

❌ Maven's main job is downloading JARs.

✔ Downloading and resolving dependencies is the *primary* value, but Maven equally owns the build lifecycle (compile/test/package/install/deploy) and enforces a standard project structure.

------------------------------------------------------------------------

❌ `mvnrepository.com` is Maven's official default repository.

✔ It's just a searchable catalog. The actual default repository is `repo.maven.apache.org/maven2`.

------------------------------------------------------------------------

❌ Declaration order in `pom.xml` always determines which version of a conflicting transitive dependency wins.

✔ Depth in the dependency graph decides first — least depth wins. Declaration order is only the tie-breaker when two conflicting paths reach the same depth.

------------------------------------------------------------------------

❌ A `runtime`-scope dependency means "not really needed."

✔ It means "needed by the JVM at execution time, but not referenced by a compile-time symbol" — often because it's loaded reflectively, like a JDBC driver. It's just as required as a compile-scope dependency, only accessed differently.

------------------------------------------------------------------------

## What You Should Remember Forever

```text
Maven                    → build automation + dependency management,
                            not just a JAR downloader

Lifecycle                → clean → validate → compile → test → package
                            → verify → install → deploy
                            (cumulative — running a later phase runs
                            every phase before it too)

Resolution order          → local repo (.m2) first, then remote

Version conflict           → least depth wins;
                              same depth → first declared in pom.xml wins
dependencyManagement       → centralizes version control, senior-level fix

compile scope (default)   → compiler loads it into compile-time classpath
runtime scope              → JVM-only, typically reflection-loaded
                              (e.g. JDBC drivers)
test scope                 → test phase only, never in the shipped artifact
```

------------------------------------------------------------------------

## Stage 2 · Week 1 Checklist

- [x] Explain why manual JAR management doesn't scale, and what Maven automates instead
- [x] Explain the Maven lifecycle and why phases are cumulative
- [x] Explain the difference between the Maven Central catalog site and the actual default repository
- [x] Explain why the local repo is always checked before a remote repo
- [x] Explain how Maven resolves a version conflict between two transitive dependencies at different depths
- [x] Explain when `dependencyManagement` is the right tool over ad-hoc version forcing
- [x] Explain the difference between compile, runtime, and test scope, with a concrete example of each
- [x] Explain why a JDBC driver is a textbook runtime-scope dependency
