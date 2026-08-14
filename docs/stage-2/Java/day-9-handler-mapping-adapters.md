# Spring MVC: Building Custom HandlerMapping, HandlerAdapter & Return Value Handlers

------------------------------------------------------------------------

> **Goal of this Chapter**
> Last Notes explained *what* `HandlerMapping`, `HandlerExecutionChain`, and `HandlerAdapter` do inside `DispatcherServlet`. This chapter proves that understanding by building each of them by hand — a custom `HandlerMapping` that doesn't use `@Controller` at all, a custom `HandlerAdapter` that knows how to invoke it, and a custom `HandlerMethodReturnValueHandler` that overrides how a controller's return value gets turned into a response. If you can write the interfaces Spring normally provides for you, you actually understand the contract — not just the annotation that hides it.

## Crisp Definition

**Every extension point in `DispatcherServlet`'s pipeline — finding a handler, executing a handler, resolving its arguments, handling its return value — is a pluggable interface with a `supports(...)`-then-`execute(...)` shape, which is exactly what lets `@Controller`-based Spring MVC and a fully custom, annotation-free handler coexist in the same application.**

------------------------------------------------------------------------

## Recap — The Flow, and Convention Over Configuration

```text
Tomcat (Servlet Container)
        ↓
DispatcherServlet (Front Controller, contains mappings, controllers, paths, and more)
        ↓
Controllers (via mappings)
```

Spring follows **Convention over Configuration**: `DispatcherServlet` is auto-registered, and you only override its behavior when you have a genuine reason to — as this chapter's custom `HandlerMapping`/`HandlerAdapter` examples do.

------------------------------------------------------------------------

## Components Inside `DispatcherServlet`

- **`MultipartResolver`** — handles file uploads (`multipart/form-data`), converting the HTTP request into `MultipartFile` objects. Needed because a large payload (like an uploaded file) is sent as part of a multipart request, not a simple body.
- **`LocaleResolver`** — determines the request's language/region (`en_US`, `fr_FR`, ...), used for i18n. This *can* come from the request itself (e.g. an `Accept-Language` header) — Spring just resolves it into something your app can act on, it isn't invented out of nowhere.
- **`List<HandlerMapping>`** — the ordered list `DispatcherServlet` consults to find a handler for each request.

These aren't things you configure by hand in Postman-style testing — Spring Boot configures them for you by default.

------------------------------------------------------------------------

## How `HandlerMapping` Actually Works

```java
HandlerExecutionChain getHandler(HttpServletRequest request)
```

Returns:

```text
HandlerExecutionChain = [ Interceptors ] + Handler (Object)
```

**Why return a chain and not just the handler?** Because interceptors — the cross-cutting concerns — need to travel with the handler through the rest of the pipeline. The handler itself is typed as generic `Object`, since Spring supports multiple handler types.

**Key method on the chain:**

```java
boolean applyPreHandle(...)
```

Traverses every registered interceptor and runs its `preHandle()`. The boolean return says whether to proceed — any interceptor can stop the request by returning `false`.

**Multiple `HandlerMapping` implementations exist** — `RequestMappingHandlerMapping` (the one behind `@Controller`/`@RequestMapping`) is the most important; others exist for narrower cases. They're discovered through component scanning: Spring scans controllers and builds mappings from them internally.

------------------------------------------------------------------------

## Building a Custom `HandlerMapping`, Handler, and `HandlerAdapter`

### 1. Custom `HandlerMapping`

**Purpose:** map a request directly to a custom handler — one that is **not** an `@Controller`.

**Key points:**

- Implements `HandlerMapping`.
- Core method: `HandlerExecutionChain getHandler(request)`.
- Returns `HandlerExecutionChain = Handler (Object) + Interceptors`.

**The logic, in this example:**

```text
if path == "/customhand"    → MyCustomHandler + Interceptors
if path == "/hellocustom"   → MyCustomHandler2 (no interceptors)
```

Interceptors are added manually:

```java
hec.addInterceptor(myInterceptor1);
hec.addInterceptor(myInterceptor2);
```

Because with a **custom mapping, you own the chain** — nothing adds interceptors for you unless your `HandlerMapping` implementation does it.

**`@Order(0)`** sets priority among multiple `HandlerMapping` implementations — a lower value means higher priority, so Spring checks it earlier when trying to resolve a request.

### 2. Custom Handlers — Not Controllers

```java
public void func(HttpServletRequest request, HttpServletResponse response)
```

These are plain classes with no `@Controller`, no annotations at all. The response is written manually:

```java
response.getWriter().write(...);
```

**The key insight:** Spring does **not** know how to call an arbitrary plain class's method — that's precisely the gap `HandlerAdapter` exists to fill.

### 3. Custom `HandlerAdapter`

**Purpose:** convert a generic handler into something executable.

**`supports()`:**

```java
return handler instanceof MyCustomHandler;
```

Tells Spring: *"I know how to run this specific handler type."*

**`handle()`:**

```java
MyCustomHandler ch = (MyCustomHandler) handler;
ch.func(request, response);
```

Executes the handler — typecasting it to its concrete type, then invoking it directly (this is the same reflective-invocation spirit as any Spring internal call, even where it's a direct cast rather than literal `Method.invoke()`).

**Multiple adapters can exist side by side.** Spring iterates them and picks whichever one's `supports(handler)` returns `true` for the handler it just resolved.

### 4. Full Execution Flow

```text
Client
  ↓
DispatcherServlet
  ↓
CustomHandlerMapping
  ↓
HandlerExecutionChain
   → [Interceptors + Handler]
  ↓
applyPreHandle()
  ↓
Find HandlerAdapter (supports = true)
  ↓
HandlerAdapter.handle()
  ↓
applyPostHandle()
  ↓
afterCompletion()
  ↓
Response
```

### 5. Interceptors Only Apply Where You Registered Them

In this example, interceptors run for `/customhand` but **not** `/hellocustom` — purely because they were added manually only for the first path's `HandlerExecutionChain`. There's no implicit global registration; a custom `HandlerMapping` decides interceptor scope entirely on its own.

### Key Concepts Recap

| Concept | Meaning |
|---|---|
| Handler | Any object (not just a controller) |
| `HandlerMethod` | Wrapper for `@Controller` methods specifically |
| `HandlerMapping` | Finds the handler for a request |
| `HandlerExecutionChain` | Handler + its interceptors, bundled |
| `HandlerAdapter` | Executes a handler once found |
| Interceptor | Cross-cutting logic wrapped around execution |

**One-line memory hooks:**

```text
HandlerMapping finds → Chain wraps → Adapter executes
supports() decides → handle() executes
If you build the chain, you add the interceptors
```

**Interview-level summary:** *"Spring MVC decouples request handling using `HandlerMapping` (to find handlers), `HandlerExecutionChain` (to wrap handlers with interceptors), and `HandlerAdapter` (to execute handlers), allowing support for multiple handler types."*

------------------------------------------------------------------------

## `Controller` Interface vs. `@Controller`

### Engineering Problem

Every prior example still relied on `@Controller`'s automatic mapping, binding, and response handling. What does request handling look like with **none** of that — implementing the raw `Controller` interface directly?

### What Implementing `Controller` Means

```java
public class Adder implements Controller {
    @Override
    public ModelAndView handleRequest(HttpServletRequest request, HttpServletResponse response) throws Exception {
        int sum = Integer.parseInt(request.getParameter("a"));
        sum += Integer.parseInt(request.getParameter("b"));
        response.getWriter().write("{Sum : " + sum + "}");
        return null;
    }
}
```

This is a deliberately lower-level approach: no annotations, no auto-mapping, no auto-binding. Everything is manual — extracting and parsing request params, writing the response body directly.

**`return null;` is meaningful here** — it signals *"I already wrote the response myself; no view resolution is needed."*

### Wiring the URL — `SimpleUrlHandlerMapping`

Since there's no `@RequestMapping` on `Adder`, URL mapping is handled by a built-in `HandlerMapping` implementation instead of a fully custom one:

```java
@Configuration
@EnableWebMvc   // tells Spring MVC "there's something of yours to discover here" —
                 // otherwise it won't search every bean for potential HandlerMapping/Adapter beans
public class CustomSimpleUrlHandlerMapping {

    @Bean
    public HandlerMapping createOwnHM() {
        SimpleUrlHandlerMapping simpleUrlHandlerMapping = new SimpleUrlHandlerMapping();
        Map<String, Controller> urlMap = new HashMap<>();
        urlMap.put("/add", new Adder());
        simpleUrlHandlerMapping.setUrlMap(urlMap);
        return simpleUrlHandlerMapping;
    }
}
```

`SimpleUrlHandlerMapping` is a built-in `HandlerMapping` implementation — it maps URL → handler (a `Controller`-implementing object), removing the need to write a fully custom `HandlerMapping` from scratch. It's a superclass-level implementation of the same `HandlerMapping` interface used everywhere else.

### Why `@EnableWebMvc`?

It enables Spring MVC's own configuration machinery — detection of `HandlerMapping`, `HandlerAdapter`, and related beans. Without it, a custom mapping bean like this one may never get picked up.

### What Happens Internally

```text
Request → SimpleUrlHandlerMapping
       → Adder (Controller)
       → SimpleControllerHandlerAdapter
       → handleRequest()
       → Response
```

### The `HandlerAdapter` You Never Had to Write

Because `Adder` implements the `Controller` interface, Spring already has a built-in `HandlerAdapter` for exactly this case: `SimpleControllerHandlerAdapter`. **No custom `HandlerAdapter` was needed** — this is the same "adapter per handler type" mechanism from the custom example above, just with Spring already having shipped the adapter for `Controller` implementations specifically.

### `@Controller` vs. `Controller` Interface

| Feature | `@Controller` | `Controller` Interface |
|---|---|---|
| URL Mapping | Automatic (`@RequestMapping`) | Manual (`SimpleUrlHandlerMapping` config) |
| Params | Auto-binding | Manual parsing (`request.getParameter(...)`) |
| Response | Auto JSON/View | Manual writing (`response.getWriter().write(...)`) |
| Adapter used | `RequestMappingHandlerAdapter` | `SimpleControllerHandlerAdapter` |

**One-line memory hook:** *`@Controller` = high-level automation. `Controller` interface = manual control.*

**Interview one-liner:** *"Implementing the `Controller` interface is a low-level approach where we manually handle requests and responses, whereas `@Controller` provides abstraction with automatic mapping and binding."*

### Engineering Insight

This is the same "adapter per type" pattern as the fully custom handler earlier — the only difference is that Spring ships `SimpleControllerHandlerAdapter` out of the box because `Controller` is a Spring-defined interface, not an arbitrary one you invented yourself. Nothing here is special-cased; it's the exact same extension mechanism, just pre-filled.

------------------------------------------------------------------------

## Customizing How a Return Value Becomes a Response

### Engineering Problem

`@Controller` methods normally return either a view name (resolved via a `ViewResolver`) or, with `@ResponseBody`/`@RestController`, an object serialized to JSON via Jackson. What if a return type needs neither — it needs its **own** custom handling logic?

### 1. A Custom Return Type

```java
public class CustomReturnValue {
    private String message;
    public CustomReturnValue(String message) { this.message = message; }
    public String getMessage() { return message; }
}
```

### 2. A Controller Returning It

```java
@Controller
public class DemoController {
    @GetMapping("/custom")
    @ResponseBody   // optional if the handler writes the response itself
    public CustomReturnValue getData() {
        return new CustomReturnValue("Hello from custom handler");
    }
}
```

Spring, by default, doesn't know what to do with `CustomReturnValue` beyond serializing it via Jackson — to override that behavior entirely, plug into `HandlerMethodReturnValueHandler`.

### 3. A Custom `HandlerMethodReturnValueHandler`

```java
@Component
public class MyReturnValueHandler implements HandlerMethodReturnValueHandler {

    @Override
    public boolean supportsReturnType(MethodParameter returnType) {
        return returnType.getParameterType().equals(CustomReturnValue.class);
    }

    @Override
    public void handleReturnValue(Object returnValue, MethodParameter returnType,
                                   ModelAndViewContainer mavContainer, NativeWebRequest webRequest) throws Exception {
        HttpServletResponse response = webRequest.getNativeResponse(HttpServletResponse.class);
        CustomReturnValue val = (CustomReturnValue) returnValue;
        response.getWriter().write("Custom handled: " + val.getMessage());
        mavContainer.setRequestHandled(true);   // tells Spring: "I handled it, stop further processing"
    }
}
```

- **`supportsReturnType()`** — decides whether this handler applies to a given method's return type.
- **`handleReturnValue()`** — writes the response manually.
- **`mavContainer.setRequestHandled(true)`** — critical: without it, Spring may still attempt its default handling on top of what you already wrote.

### 4. Registering It With Spring

```java
@Configuration
public class WebConfig implements WebMvcConfigurer {
    @Autowired
    MyReturnValueHandler myHandler;

    @Override
    public void addReturnValueHandlers(List<HandlerMethodReturnValueHandler> handlers) {
        handlers.add(myHandler);
    }
}
```

### 5. Where This Fits — Inside `RequestMappingHandlerAdapter`

Internally, `RequestMappingHandlerAdapter` holds:

```java
List<HandlerMethodReturnValueHandler>
List<HandlerMethodArgumentResolver>
```

**Execution flow:**

```text
Controller method returns CustomReturnValue
        ↓
RequestMappingHandlerAdapter
        ↓
Loop over ReturnValueHandlers
        ↓
supportsReturnType() → true
        ↓
handleReturnValue()
        ↓
Response sent
```

### 6. The Input-Side Mirror — `HandlerMethodArgumentResolver`

The same `supports(...)`-then-`resolve(...)` shape exists for **method parameters**, not just return values:

```java
public String test(@CustomArg MyObj obj)
```

```java
boolean supportsParameter(...)
Object resolveArgument(...)
```

`HandlerMethodArgumentResolver` is what lets Spring resolve `@RequestParam`, `@PathVariable`, `@RequestBody`, and any custom parameter annotation you define — the exact same extension point, mirrored on the input side.

### Big Picture

| Concern | Component |
|---|---|
| Find handler | `HandlerMapping` |
| Execute handler | `HandlerAdapter` |
| Resolve method args | `HandlerMethodArgumentResolver` |
| Handle return value | `HandlerMethodReturnValueHandler` |

**One-line memory hook:** *Adapter executes → ArgumentResolver feeds → ReturnValueHandler outputs.*

**Interview-level answer:** *"Spring MVC uses `RequestMappingHandlerAdapter`, which internally delegates parameter resolution to `HandlerMethodArgumentResolver`s and return handling to `HandlerMethodReturnValueHandler`s."*

### Engineering Insight

Every extension point covered in this chapter — `HandlerMapping`, `HandlerAdapter`, `HandlerMethodArgumentResolver`, `HandlerMethodReturnValueHandler` — shares the exact same shape: a `supports(...)` check, followed by an `execute(...)`/`resolve(...)`/`handle(...)` call once that check passes. This is the **Strategy Pattern**, applied uniformly across every stage of request processing: Spring doesn't special-case any of these decisions internally — it iterates a list of strategies and asks each one "can you handle this?" until one says yes. Once you recognize the shape once, every other extension point in Spring MVC is the same shape again.

------------------------------------------------------------------------

## Interview Q&A

### Why does a custom `HandlerMapping` need to manually add interceptors, when `@Controller`-based mappings don't seem to require this?

Because with a custom `HandlerMapping`, you own the construction of the `HandlerExecutionChain` entirely — nothing populates its interceptor list except code you write. `RequestMappingHandlerMapping` (behind `@Controller`) does this wiring for you internally, based on `WebMvcConfigurer.addInterceptors()` registrations.

### What does `@Order(0)` control on a `HandlerMapping`?

Priority among multiple registered `HandlerMapping` implementations — a lower value means Spring consults that mapping earlier when trying to resolve a request to a handler.

### Why can't Spring invoke a plain class's method directly, without any `HandlerAdapter`?

Because the handler inside a `HandlerExecutionChain` is typed as generic `Object` — Spring has no compile-time knowledge of what concrete type it is or how to call it. A `HandlerAdapter`'s `supports(handler)` check identifies whether it knows how to run that specific handler type, and only then typecasts and invokes it.

### What is `SimpleUrlHandlerMapping`, and what problem does it solve?

A built-in `HandlerMapping` implementation that maps a URL directly to a `Controller`-implementing object via a simple map, removing the need to hand-write a fully custom `HandlerMapping` when you're not using `@Controller`/`@RequestMapping` at all.

### If you implement the raw `Controller` interface instead of using `@Controller`, do you need to write your own `HandlerAdapter`?

No — Spring already ships `SimpleControllerHandlerAdapter`, which supports any object implementing the `Controller` interface specifically. A custom `HandlerAdapter` is only needed for handler types Spring doesn't already know about.

### What's the practical trade-off between `@Controller` and directly implementing `Controller`?

`@Controller` gives you automatic URL mapping, parameter binding, and response serialization at the cost of being "magic" until you understand the mechanism behind it. Implementing `Controller` directly gives full manual control over request parsing and response writing, at the cost of writing all of that by hand — useful mainly for understanding the internals, or narrow cases needing behavior `@Controller`'s defaults don't support.

### Why would you need a custom `HandlerMethodReturnValueHandler`?

When a controller method's return type needs handling logic Spring's defaults (view resolution, or Jackson-based JSON serialization via `@ResponseBody`) don't provide — you take over exactly how that specific return type becomes an HTTP response.

### What does `mavContainer.setRequestHandled(true)` do inside a custom `HandlerMethodReturnValueHandler`, and why is it necessary?

It tells Spring the response has already been fully written by your handler, so no further processing (like attempting a view resolution) should occur — omitting it risks Spring trying to handle the same response a second time.

### What's the mirror-image extension point to `HandlerMethodReturnValueHandler`, and what does it do?

`HandlerMethodArgumentResolver` — instead of turning a controller's return value into a response, it turns incoming request data into a controller method's parameter values (this is the mechanism behind `@RequestParam`, `@PathVariable`, `@RequestBody`, and any custom parameter annotation).

### What single design pattern unifies `HandlerMapping`, `HandlerAdapter`, `HandlerMethodArgumentResolver`, and `HandlerMethodReturnValueHandler`?

The Strategy Pattern — each is a `supports(...)`-check followed by an execute/resolve/handle call, and `DispatcherServlet` (or `RequestMappingHandlerAdapter`) iterates a list of these strategies until one reports it can handle the current case.

------------------------------------------------------------------------

❌ Interceptors registered anywhere in the app apply to every `HandlerMapping`'s requests automatically.

✔ Interceptor scope is decided entirely by whichever `HandlerMapping` builds the `HandlerExecutionChain` for that request — a custom `HandlerMapping` only applies interceptors you explicitly add to its own chain.

------------------------------------------------------------------------

❌ Implementing the raw `Controller` interface requires you to also hand-write a `HandlerAdapter`.

✔ Spring already ships `SimpleControllerHandlerAdapter` for exactly this interface — a custom `HandlerAdapter` is only necessary for handler types Spring has no built-in adapter for.

------------------------------------------------------------------------

❌ `@EnableWebMvc` is required for every Spring Boot web application.

✔ Spring Boot auto-configures Spring MVC already; `@EnableWebMvc` matters specifically when you're registering custom infrastructure beans (like a custom `HandlerMapping`) that Spring's default auto-configuration might not otherwise pick up.

------------------------------------------------------------------------

❌ Returning a custom object from `@Controller` always requires implementing a custom `HandlerMethodReturnValueHandler`.

✔ Only if Jackson's default JSON serialization (via `@ResponseBody`) isn't what you want. Most custom types serialize fine automatically — a custom return-value handler is for genuinely different output handling.

------------------------------------------------------------------------

## What You Should Remember Forever

```text
HandlerMapping.getHandler()   → returns a HandlerExecutionChain,
                                  not just a bare handler, because
                                  interceptors must travel with it

Custom HandlerMapping         → you own the chain; interceptors are
                                  only added where you add them
@Order(0)                     → lower value = checked first, among
                                  multiple HandlerMappings

Handler is typed Object       → because Spring supports many handler
                                  kinds; HandlerAdapter bridges that gap
supports(handler) → handle()  → the shape every HandlerAdapter follows

Controller interface           → manual mapping, binding, response —
                                   SimpleUrlHandlerMapping +
                                   SimpleControllerHandlerAdapter,
                                   both already built in

HandlerMethodReturnValueHandler → supportsReturnType() + handleReturnValue()
                                    + setRequestHandled(true)
HandlerMethodArgumentResolver    → the same shape, mirrored on the input side

All four extension points        → Strategy Pattern: supports() then act(),
                                     iterated until one says yes
```

------------------------------------------------------------------------

## Stage 2 · Week 1 Checklist

- [x] Explain why `HandlerMapping.getHandler()` returns a chain rather than a bare handler
- [x] Explain why a custom `HandlerMapping` must add interceptors manually
- [x] Explain what a `HandlerAdapter`'s `supports()`/`handle()` pair does, and why it's needed at all
- [x] Explain what `SimpleUrlHandlerMapping` and `SimpleControllerHandlerAdapter` do, and when they're used instead of the `@Controller`-based defaults
- [x] Explain the practical trade-offs between `@Controller` and implementing the `Controller` interface directly
- [x] Explain what a `HandlerMethodReturnValueHandler` is for, and why `setRequestHandled(true)` matters
- [x] Explain how `HandlerMethodArgumentResolver` mirrors `HandlerMethodReturnValueHandler` on the input side
- [x] Name the design pattern shared by `HandlerMapping`, `HandlerAdapter`, `HandlerMethodArgumentResolver`, and `HandlerMethodReturnValueHandler`, and explain why it fits
