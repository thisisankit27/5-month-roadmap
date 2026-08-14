# Spring MVC: HTTP, Servlets, Controllers & DispatcherServlet Internals

------------------------------------------------------------------------

> **Goal of this Chapter**
> This is not "here's `@GetMapping`." Spring MVC is a layer of translation: HTTP is stateless, text-based, and knows nothing about Java objects — Spring MVC's entire job is bridging that gap, from a raw socket read down to a typed method call, and back. The goal is to understand *what each layer of that bridge is actually doing* — the servlet container, `DispatcherServlet`, `HandlerMapping`, `HandlerAdapter`, interceptors — so `@RequestMapping` stops looking like magic string-matching and starts looking like the specific mechanism it is.

## Crisp Definition

**Spring MVC translates a stateless HTTP request into a typed Java method call and back into an HTTP response, using a front controller (`DispatcherServlet`) that locates the right handler, wraps it with cross-cutting interceptors, and invokes it through a handler-type-agnostic adapter.**

------------------------------------------------------------------------

## HTTP Is a Stateless Protocol

### The Core Idea

HTTP is stateless: every request is independent, and the server does not remember anything about previous requests.

```text
Request 1 → processed → response → server forgets
Request 2 → treated as completely new
```

### The Iterator Analogy

A **stateful** construct, like a Java `Iterator`, stores its position internally — `hasNext()` knows where it is, `next()` moves forward, and that state persists between calls.

**Stateless** HTTP has none of that: the server doesn't know the previous request, the current page, or prior user actions. The **client** must send the full context on every single request.

### Pagination Example

```text
GET /search?q=shoes&page=2
```

The server reads `page=2`, fetches results 31–60, and sends the response. It does **not** remember that the client visited page 1, or what they clicked before. **Pagination is client-driven state** — the client, not the server, tracks where it is.

### Cookies — Simulating State on Top of a Stateless Protocol

Cookies exist specifically to simulate state in a protocol that has none. A cookie is sent in **headers**, not the payload:

```text
Cookie: sessionId=abc123
```

The server uses this to identify the user and fetch stored session data associated with that ID.

**Real-life example (Netflix-style recommendations):**

1. The server assigns a session/user ID via a cookie.
2. That cookie is sent with every subsequent request: `Cookie: userId=xyz789`.
3. The server maps that ID to watch history, preferences, liked content.
4. Next visit: server reads the cookie, fetches the data, shows personalized recommendations — all without the client re-sending any of that history itself.

### Key Distinction

| Concept | Who Maintains State | Example |
|---|---|---|
| Pagination | Client | `?page=3` |
| Cookies | Client + Server | `sessionId=abc123` |
| Session | Server | Stored user data, keyed by the cookie's ID |

------------------------------------------------------------------------

## Components of an HTTP Request

| Component | Purpose | Example |
|---|---|---|
| **Method (verb)** | What action the client wants | `GET` fetch, `POST` create, `PUT` full update, `PATCH` partial update, `DELETE` remove |
| **URI** | Where the request is going | `/products?page=2` — `/products` is the resource, `?page=2` is a query parameter (client state) |
| **HTTP Version** | Protocol version | `HTTP/1.1`, `HTTP/2`, `HTTP/3` |
| **Headers** | Metadata about the request | `Host`, `Content-Type`, `Authorization: Bearer token123`, `Cookie: sessionId=abc123` — used for auth, content type, cookies, caching |
| **Body (payload)** | Actual data sent — mainly `POST`/`PUT`/`PATCH` | `{"name": "Shoes", "price": 2000}` — not used in most `GET` requests |

**Full example:**

```http
POST /products HTTP/1.1
Host: example.com
Content-Type: application/json
Cookie: sessionId=abc123

{
  "name": "Shoes",
  "price": 2000
}
```

**One-line memory hook:** *Request = Method + URI + Version + Headers + Body.*

### Spring MVC Mapping

| Request Component | Spring Annotation |
|---|---|
| Method | `@GetMapping`, `@PostMapping`, ... |
| URI params | `@RequestParam`, `@PathVariable` |
| Headers | `@RequestHeader` |
| Cookies | `@CookieValue` |
| Body | `@RequestBody` |

------------------------------------------------------------------------

## Components of an HTTP Response

| Component | Purpose | Example |
|---|---|---|
| **Status Line** | Tells the result of the request | `HTTP/1.1 200 OK` — version + status code + reason phrase |
| **Headers** | Metadata about the response | `Content-Type`, `Content-Length`, `Set-Cookie: sessionId=abc123`, `Cache-Control` |
| **Body** | Actual data returned | JSON (most common in APIs), HTML (web pages), XML, plain text |

**Common status codes:**

| Code | Meaning |
|---|---|
| `200 OK` | Success |
| `201 Created` | Resource created |
| `400 Bad Request` | Client error |
| `401 Unauthorized` | Auth required |
| `404 Not Found` | Resource not found |
| `500 Internal Server Error` | Server error |

**Full example:**

```http
HTTP/1.1 200 OK
Content-Type: application/json
Set-Cookie: sessionId=abc123

{
  "id": 101,
  "name": "Shoes"
}
```

**One-line memory hook:** *Response = Status Line + Headers + Body.*

### Spring MVC Mapping

| Response Component | Spring Mechanism |
|---|---|
| Status | `@ResponseStatus`, `ResponseEntity` |
| Headers | `ResponseEntity` / `HttpHeaders` |
| Body | `@ResponseBody`, `@RestController` |

------------------------------------------------------------------------

## Servlets and Servlet Containers

### What Is a Servlet?

A **Servlet** is a Java **interface** used to handle HTTP requests and responses — it acts as an entry point for web requests and runs inside a **Servlet Container**. Think: *"Servlet = request handler."*

Three key methods:

- **`init()`** — initializes important parameters, dependencies, etc.
- **`service()`** — accepts the request, sends it to the Spring app to handle, gets the response, translates it into an HTTP response, and sends it back down through the OS to the NIC to the internet.
- **`destroy()`** — tears down the servlet.

### Servlet Container ≠ Servlet

The **Servlet Container** is the *environment* that runs servlets — Apache Tomcat, Jetty, etc. It's responsible for:

- managing servlet lifecycle,
- handling HTTP request/response,
- mapping URL → servlet,
- multi-threading, and
- security.

------------------------------------------------------------------------

## Standalone vs. Embedded Servers

### The Old Approach — Traditional Deployment (External Server)

**Step 1:** Write your Spring MVC app (controllers, services, configs).

**Step 2:** Build a **WAR** file (`mvn clean install` → `myapp.war`). WAR = **Web Archive**, designed to run *inside* a server.

**Step 3:** Install and run a server separately (e.g. download Tomcat, `startup.sh`).

**Step 4:** Deploy the WAR into the server (`myapp.war → tomcat/webapps/`). Tomcat extracts the WAR, loads your app, creates servlets (including `DispatcherServlet`), and starts serving requests.

**Runtime flow:** `Client → Tomcat → Your App → Response`.

**The real problems this creates:**

1. **Version conflicts** — App A needs Tomcat 8, App B needs Tomcat 10, but they share one server.
2. **Manual deployment** — build WAR, copy to server, restart server: slow and error-prone.
3. **Config complexity** — XML configs (`web.xml`), server configs, port configs — too many moving parts.
4. **Single point of failure** — five apps on one Tomcat instance; Tomcat crashes, all five go down.
5. **Scaling pain** — scaling one app means scaling the entire shared server.

### The Modern Approach — Spring Boot (Embedded Server)

**Step 1:** Write your app the same way — but no external server is needed.

**Step 2:** Build a **JAR** (`mvn clean package` → `myapp.jar`).

**Step 3:** Run it directly: `java -jar myapp.jar`.

**What's actually inside the JAR:** an embedded Tomcat, already bundled, alongside your Spring app.

**What happens when you run it:**

1. JVM starts.
2. Spring Boot starts.
3. Embedded Tomcat starts.
4. `DispatcherServlet` is registered.
5. App is ready.

**Runtime flow:** `Client → Embedded Tomcat (inside the app) → Controller → Response`.

**Advantages:**

1. **No separate server** — the server *is* part of your app; no installation, no setup.
2. **Easy deployment** — `java -jar myapp.jar` and you're done. No copying, no config.
3. **Isolation** — each app has its own server and its own config, so there are no cross-app conflicts.
4. **Microservices-friendly** — each service is an independent unit (auth service on 8081, product service on 8082), scaled independently.

### Standalone vs. Embedded, Visualized

```text
Standalone Server (Old)          Embedded Server (Modern)

     Tomcat                      App1 (Tomcat inside)
   /   |   \                     App2 (Tomcat inside)
 App1 App2 App3                  App3 (Tomcat inside)

Shared environment                Fully independent
Risky + rigid                     Flexible + scalable
```

### The Real Shift

```text
OLD:  Application depends on Server
NEW:  Server is part of the Application
```

**One-line memory hook:** *WAR → needs a server. JAR → has a server.*

### Standalone Servers Still Have Real Benefits

Standalone isn't obsolete — it's context-dependent:

1. **Resource sharing (cost-efficient)** — multiple apps sharing one server means shared CPU/memory and lower infrastructure cost; useful for small companies or internal tools.
2. **Centralized management** — one place to manage security, SSL config, logging, monitoring — simpler DevOps when the number of apps is small.
3. **Easier for traditional monoliths** — a single large application with tightly coupled modules doesn't gain much from splitting into independently deployed servers.
4. **Reusable infrastructure** — connection pools, thread pools, caching are already configured once, and new apps can plug into the same environment.

**The trade-offs, in the same order:**

1. **Single point of failure** — the server crashes, every app on it goes down.
2. **Version conflicts** — different apps needing different Java versions or library versions on the same server are hard to reconcile.
3. **Limited flexibility** — one server config serves every app, even when their resource needs (memory-heavy vs. lightweight) genuinely differ.
4. **Scaling problem** — scaling one app means scaling the whole shared server.

| Use Case | Best Choice |
|---|---|
| Small apps / internal tools | Standalone |
| Large scale / microservices | Embedded (Spring Boot) |

**Interview one-liner:** *"Standalone servers provide shared infrastructure efficiency, while embedded servers provide isolation and scalability."*

------------------------------------------------------------------------

## `@Controller` Is a Bean — Component Scanning Applies

### A Minimal REST Controller

```java
package com.example.controllers;

@RestController   // works with or without @ResponseBody — RestController assumes
                   // every return value belongs in the HTTP response body
@RequestMapping(value = "/greet")
public class SimpleController {

    @GetMapping
    @ResponseBody   // method-level: signals "include the result in the HTTP response body"
    public String greet() {
        System.out.println("Log: Received Greet()");
        return "Hello";
    }
}
```

### `@Controller` Is Discovered Like Any Other Bean

`@Controller` is a Spring-managed bean, detected via [component scanning](day-7-config-events.md#component-scanning-what-spring-finds-and-what-it-doesnt) — the same rules apply here as anywhere else: it must be inside the scan scope of your main class.

```text
Main class in:  com.example
Spring scans:   com.example.*
```

If your controller is outside that tree (`com.other.controllers`), Spring won't detect it, and the endpoint simply won't exist. The fix is the same as for any undiscovered bean:

```java
@ComponentScan(basePackages = {
    "com.example.resources",
    "com.example.controllers"
})
```

### `@Controller` vs. `@RestController`

**`@Controller`** is for MVC (views like JSP/Thymeleaf) — its return value is treated as a **view name**, not sent as the response body by default.

```java
@Controller
public class MyController {
    @GetMapping("/greet")
    public String greet() {
        return "hello";   // Spring looks for hello.html / hello.jsp — NOT the literal text "hello"
    }
}
```

Returning `"Hello"` from a bare `@Controller` method does **not** send `"Hello"` as text — it tries to resolve a view named `"Hello"`, and fails if none exists.

**Fix — add `@ResponseBody`:**

```java
@Controller
public class MyController {
    @GetMapping("/greet")
    @ResponseBody
    public String greet() {
        return "Hello";   // now sent as the HTTP response body
    }
}
```

**`@RestController`** is the shortcut: it's equivalent to `@Controller + @ResponseBody` on every method — every method's return value goes directly into the HTTP response body.

| Case | Result | Reason |
|---|---|---|
| `@Controller` only | Not working | Return value treated as a view name |
| `@Controller` + `@ResponseBody` | Works | Explicitly sends the body |
| `@RestController` | Works | Body sending is automatic |

------------------------------------------------------------------------

## Spring MVC — Model, View, Controller

### Model (Data Layer)

**Model = data + state.** It can come from a database, an in-memory cache, an external API, or objects constructed in code — e.g. `User user = userService.getUser();`.

### View (Presentation Layer)

**View = the UI representation of data** — HTML (Thymeleaf, JSP) or JSON in REST APIs.

**Important nuance:** "the view should ideally return only data" isn't quite right. In **traditional MVC**, the view is HTML — a UI. In **REST APIs**, the view layer is skipped entirely, and data (JSON) is returned directly instead.

### Controller (Request Handler)

**Controller = the entry point of request handling.** Responsibilities:

- map URL → method,
- accept input,
- call the service layer,
- return either a **view name** (MVC) or **data** (REST).

### View Resolution

When a controller returns a plain string in MVC mode, Spring tries to resolve it as a view:

```text
Spring searches for: Hello.html / Hello.jsp / Hello (template)
Locations checked:   /templates/ (Thymeleaf), /WEB-INF/, configured view resolvers
```

If nothing matches, you get a **404 / Whitelabel Error Page** — because Spring MVC follows the MVC pattern by default, where a controller's return value is a view name unless told otherwise:

| Component | Role |
|---|---|
| Model | Data |
| View | UI (HTML/JSP) |
| Controller | Handles the request |

### Telling Spring "This Is Data, Not a View"

**Option 1 — `@ResponseBody`:**

```java
@Controller
public class SimpleController {
    @GetMapping("/greet")
    @ResponseBody
    public String greet() {
        return "Hello";
    }
}
```

**Option 2 — `@RestController` (preferred):** automatically behaves like `@Controller + @ResponseBody` for every method.

### The View-Rendering Case, End to End

```java
@Controller
@RequestMapping(value = {"/view", "/VIEW"})
public class ViewReturningController {
    @GetMapping
    public String render() {
        return "arunkit";
    }
}
```

```properties
spring.thymeleaf.prefix=classpath:/templates/
spring.thymeleaf.suffix=.html
```

```text
src/main/resources/templates/arunkit.html
```

**Flow:** `DispatcherServlet → ViewReturningController → "arunkit" → Thymeleaf ViewResolver → /templates/arunkit.html → render HTML.`

**The key insight:** returning `"arunkit"` isn't the final filename — Spring computes `prefix + "arunkit" + suffix = classpath:/templates/arunkit.html`.

------------------------------------------------------------------------

## Reading Request Parameters

```java
@Controller
@RequestMapping(value = "/sendparam")
public class RequestParamDemo {

    @RequestMapping(method = RequestMethod.GET, path = "/say")
    @ResponseBody
    public String checkStatParam(@RequestParam(required = false) Integer id) {
        return id != null ? "Hello " + id : "Hello Guest";
    }

    @RequestMapping(method = RequestMethod.GET, path = {"/saypath", "/saypath/{id}"})
    @ResponseBody
    public String checkStatPathVar(@PathVariable(required = false) Integer id) {
        return id != null ? "Hello " + id : "Hello Guest";
    }
}
```

### `@RequestParam` — Extracting Query Parameters

```java
@RequestParam("identifier") int id
```

```text
URL:    http://localhost:8080/sendparam/say?identifier=10
Flow:   client sends ?identifier=10
        → Spring maps identifier → id
        → method executes, returns "Hello 10"
```

**Rules:**

- the parameter name must match: `@RequestParam("identifier")` matches `?identifier=`.
- default behavior is `required = true` — a missing parameter is an error.

### `@RequestParam(required = false)` — Optional Parameters

- If present → value assigned.
- If missing → no error, the argument is simply `null`.

**A rule that matters — use a non-primitive (wrapper) type:**

```java
Integer id   // ✔ correct
int id       // ✘ wrong
```

A missing optional parameter resolves to `null` — and a primitive `int` cannot hold `null`, so using `int` here causes a startup/runtime error. `Integer` can hold `null`, so the wrapper type is required whenever `required = false`.

```java
public String checkStat(@RequestParam(required = false) Integer id) {
    return id != null ? "Hello " + id : "Hello Guest";
}
```

### Request Params vs. Path Variables — When to Use Which

```text
example.com/courses?courseid=22    ← query parameter
example.com/courses/22             ← path variable
```

General convention (not a mandate):

1. **Filters, ratings, or any optional value** → `@RequestParam`.
2. **A large or complex key-value that would clutter a URL path** → also better suited to `@RequestParam`, since a path is meant to stay readable.

------------------------------------------------------------------------

## Passing and Returning Objects From Controllers

### Returning an Object — Serialization

```java
public class ExamResult {
    int phy, chem, maths;
    public ExamResult(int phy, int chem, int maths) {
        this.phy = phy; this.chem = chem; this.maths = maths;
    }
}

@RestController
@RequestMapping(value = "/examresult")
public class ExamResultController {
    @RequestMapping(method = RequestMethod.GET, value = "/view")
    public ExamResult getResult() {
        return new ExamResult(90, 18, 0);
    }
}
```

Returning the raw object like this **won't work as expected** until it can be serialized — Spring bundles **Jackson**, its built-in library for serializing/deserializing objects. Jackson is smart enough to find a class's getters and uses them to serialize:

```java
public int getPhy() { return phy; }
public int getChem() { return chem; }
public int getMaths() { return maths; }
```

Spring uses Jackson to convert the Java object → JSON (via the getters) and sends it as the HTTP response:

```json
{
  "phy": 90,
  "chem": 18,
  "maths": 0
}
```

### Accepting an Object — Data Binding

```java
@RequestMapping(method = RequestMethod.GET, value = "/examine")
public String examineResult(ExamResult examResult) {
    if (examResult.getPhy() > 90 && examResult.getChem() > 90 && examResult.getMaths() > 90) {
        return "Good Result";
    }
    return "Bad Result";
}
```

Spring has a strong auto-binding capability: given `?phy=99&chem=91&maths=100`, it reads the query params and maps them directly onto the object's fields — this is called **Data Binding / Auto Binding**.

### Content Negotiation — `produces`

```java
@RequestMapping(method = RequestMethod.GET, value = "/view", produces = "application/json")   // default, so optional
```

For XML output, add the Jackson XML dependency:

```xml
<dependency>
    <groupId>com.fasterxml.jackson.dataformat</groupId>
    <artifactId>jackson-dataformat-xml</artifactId>
</dependency>
```

```java
@RequestMapping(method = RequestMethod.GET, value = "/view", produces = "application/xml")
```

```xml
<ExamResult>
    <phy>90</phy>
    <chem>18</chem>
    <maths>0</maths>
</ExamResult>
```

------------------------------------------------------------------------

## The Architecture of a Web Request

When the server is "running on port 8080," it means the embedded servlet container (Tomcat) is listening on that port, handling incoming HTTP requests for the application.

### Actual Flow

```text
Client
  ↓
Servlet Container (Tomcat)
  ↓
DispatcherServlet (Front Controller)
  ↓
HandlerMapping (finds the controller)
  ↓
Controller
  ↓
Service → Repository (optional)
  ↓
Response back via DispatcherServlet
  ↓
Client
```

### What Actually Happens

**1. Application starts** — Spring Boot starts, embedded Tomcat starts, `DispatcherServlet` is registered.

**2. Request arrives** — `Client → Tomcat`. Tomcat receives the HTTP request and finds the mapped servlet — `DispatcherServlet`.

**3. `DispatcherServlet`'s core role** — it acts as the **Front Controller**: central entry point, routes the request to the correct controller, coordinates the entire flow.

```text
DispatcherServlet
   ↓
HandlerMapping → finds the controller
   ↓
HandlerAdapter → calls the method
   ↓
Controller executes
```

**Precise framing:** *"`DispatcherServlet` acts as a front controller that receives all requests and delegates them to appropriate controllers using handler mappings."*

------------------------------------------------------------------------

## Interceptors

### Engineering Problem

Cross-cutting concerns — logging, authentication, header validation, latency tracking — aren't part of any single controller's core business logic, but nearly every controller needs some subset of them. Duplicating that logic inside every controller method couples unrelated concerns together and makes each one harder to change independently.

### What Interceptors Are For

Used for **cross-cutting concerns** — things not part of core business logic: logging, authentication/authorization, header validation/modification, performance tracking (latency).

### Where They Fit in the Flow

```text
Client
  ↓
Servlet Container (Tomcat)
  ↓
DispatcherServlet
  ↓
HandlerInterceptor (preHandle)
  ↓
Controller
  ↓
HandlerInterceptor (postHandle)
  ↓
View / Response
  ↓
HandlerInterceptor (afterCompletion)
  ↓
Client
```

Interceptors are **invoked by `DispatcherServlet`**, not a separate layer of the stack.

```java
public interface HandlerInterceptor {
    default boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        return true;
    }
    default void postHandle(HttpServletRequest request, HttpServletResponse response, Object handler, ModelAndView modelAndView) { }
    default void afterCompletion(HttpServletRequest request, HttpServletResponse response, Object handler, Exception ex) { }
}
```

### `preHandle()` — Before the Controller Executes

Use cases: logging, auth checks, modifying the request, initializing resources, and — uniquely among the three — **it can block the request entirely**:

```java
return false;   // stops execution before the controller ever runs
```

**What the boolean means:** `true` continues the request flow; `false` stops it immediately.

**Real use case — authentication check:**

```java
if (notLoggedIn) {
    response.setStatus(401);
    return false;
}
return true;
```

Also used for rejecting invalid headers, suspicious requests, or rate limiting.

### `postHandle()` — After the Controller, Before the Response Is Sent

Use cases: modifying the response, adding attributes.

### `afterCompletion()` — After the Complete Request-Response Cycle

Use cases: cleanup, logging total request time.

| Task | Where |
|---|---|
| Logging | `preHandle` / `afterCompletion` |
| Header checks | `preHandle` |
| Default values | `preHandle` |
| Latency tracking | `preHandle` + `afterCompletion` |
| Drop request | `preHandle` (`return false`) |

### Registering Interceptors

Defining an interceptor class isn't enough — **you must register it with Spring**, via `WebMvcConfigurer`:

```java
public interface WebMvcConfigurer {
    void addInterceptors(InterceptorRegistry registry);
}
```

Spring calls this internally during startup.

**Interceptor class:**

```java
@Component
public class MyInterceptor1 implements HandlerInterceptor {
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) {
        System.out.println("MyInterceptor1 preHandle");
        return true;
    }
    public void postHandle(HttpServletRequest request, HttpServletResponse response, Object handler, ModelAndView modelAndView) {
        System.out.println("MyInterceptor1 postHandle");
    }
}
```

**Configuration class:**

```java
@Component
public class InterceptorConfig implements WebMvcConfigurer {
    @Autowired
    MyInterceptor1 myInterceptor1;
    @Autowired
    MyInterceptor2 myInterceptor2;

    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(myInterceptor1);
        registry.addInterceptor(myInterceptor2);
    }
}
```

### `InterceptorRegistry` — Order Matters

Think of it as a list managed by Spring, holding all interceptors in **execution order**:

```java
registry.addInterceptor(A);
registry.addInterceptor(B);
```

```text
preHandle:  A → B
postHandle: B → A   (reverse order, like closing nested resources)
```

### Path-Based Mapping

Control exactly where an interceptor applies:

```java
registry.addInterceptor(myInterceptor1)
        .addPathPatterns("/api/**")
        .excludePathPatterns("/login");
```

### Final Execution Flow

```text
DispatcherServlet
   ↓
Interceptor1 preHandle
   ↓
Interceptor2 preHandle
   ↓
Controller
   ↓
Interceptor2 postHandle
   ↓
Interceptor1 postHandle
```

**Interview one-liner:** *"In Spring MVC, interceptors are registered using `WebMvcConfigurer`'s `addInterceptors` method, where we add them to the `InterceptorRegistry` and optionally define path patterns."*

------------------------------------------------------------------------

## `DispatcherServlet` Internals — Handler, HandlerMapping, HandlerAdapter

### The Big Picture

`DispatcherServlet` is the brain of Spring MVC. It does three core things:

1. **Find who should handle the request** → `HandlerMapping`.
2. **Figure out how to call it** → `HandlerAdapter`.
3. **Execute it with interceptors wrapped around it** → `HandlerExecutionChain`.

### A Handler Is Not Just "a Controller"

In Spring's terms, a **Handler** is *any* object capable of handling a request — in practice, that's almost always a controller method, but the abstraction is deliberately broader (Spring also supports things like `HttpRequestHandler`).

Your controller method:

```java
@GetMapping("/hello")
public String sayHello() { }
```

...is internally wrapped as a `HandlerMethod` — a Spring class containing the controller object and a reference to the method. The JVM itself sees this as a reflective `Method` object.

### How `DispatcherServlet` Finds the Handler — `HandlerMapping`

```text
Request (/hello) → HandlerMapping → HandlerMethod
```

`HandlerMapping` matches the URL and returns a `HandlerExecutionChain`.

### `HandlerExecutionChain`

Contains **two things**:

```text
HandlerExecutionChain = [ List of Interceptors ] + Handler (controller method)
```

Internally, it exposes:

- `applyPreHandle()` — runs interceptors, before the handler.
- `applyPostHandle()` — runs interceptors, after the handler.
- `getHandler()` — returns the actual handler.

### `doDispatch()` — the Core Flow

Inside `DispatcherServlet.doDispatch()`:

1. `getHandler(request)` — loops through every `HandlerMapping`, looking for a match.
2. If nothing matches → **404**.
3. Otherwise, retrieves the `HandlerExecutionChain` — handler plus its interceptors.

### The Problem — the Handler Is Typed as `Object`

Inside `HandlerExecutionChain`:

```java
Object handler;
```

**Why `Object`?** Because Spring supports many different handler types (controller methods, `HttpRequestHandler`, others) — a single concrete type couldn't represent all of them uniformly.

### The Solution — `HandlerAdapter`

**Purpose:** *"make any handler executable,"* regardless of its concrete type.

```java
handlerAdapter.supports(handler)
```

If `true`, this particular adapter knows how to execute this handler — it then typecasts the handler and calls its method, ultimately via reflection.

| Problem | Solution |
|---|---|
| Handler is typed as `Object` | `HandlerAdapter` |
| Don't know how to invoke it generically | The adapter knows, for its supported type |
| Multiple handler types exist | Multiple adapters exist, one per type |

### The Full Internal Flow

```text
Client
  ↓
DispatcherServlet
  ↓
getHandler() → HandlerExecutionChain
  ↓
applyPreHandle() (interceptors)
  ↓
HandlerAdapter.supports(handler)
  ↓
HandlerAdapter.handle()
   → calls the controller method, via reflection
  ↓
applyPostHandle()
  ↓
Response
```

### Mental Model

- **`HandlerMapping`** = Finder — locates the right handler for this URL.
- **`HandlerExecutionChain`** = Package — bundles the handler with its interceptors.
- **`HandlerAdapter`** = Executor — knows how to actually invoke a given handler type.
- **`DispatcherServlet`** = Coordinator — orchestrates all of the above per request.

**Interview-level answer:** *"`DispatcherServlet` uses `HandlerMapping` to find the handler, wraps it in a `HandlerExecutionChain` with interceptors, and then uses a suitable `HandlerAdapter` to execute the handler method via reflection."*

### Engineering Insight

This entire pipeline is the same reflective-invocation mechanism from [day-4-reflection.md](day-4-reflection.md), applied at framework scale: Spring can't know your controller's concrete type at compile time, so it stores the handler as `Object` and uses reflection (mediated by `HandlerAdapter`) to invoke it anyway — exactly the "types unknown until runtime" problem reflection exists to solve.

------------------------------------------------------------------------

## Interview Q&A

### Why does HTTP need cookies if it's stateless?

Because statelessness means the server retains nothing between requests — cookies simulate continuity by having the client resend an identifying token (like `sessionId`) with every request, which the server maps back to stored state on its side.

### Is pagination server-side or client-side state?

Client-side — the server doesn't remember which page you were on; the client resends `?page=N` on every request, and the server treats each one as independent.

### What's the difference between a WAR and a JAR in a Spring context?

A WAR (Web Archive) is built to be deployed *into* an external server like Tomcat — the app depends on a server that exists separately. A JAR built by Spring Boot bundles an embedded server inside the artifact itself — the server is *part of* the application, and you run it directly with `java -jar`.

### What problem does an embedded server solve that a shared standalone server doesn't?

Isolation and independent scaling — each app gets its own server instance and config, so one app's crash, version requirement, or scaling need doesn't affect any other app sharing the same physical server.

### Why does returning a String from a bare `@Controller` method not send that string as the response?

Because `@Controller` treats a returned String as a **view name** by default, not response content — Spring tries to resolve a matching view (`.html`/`.jsp`) and returns a 404/Whitelabel error if none exists. `@ResponseBody` (or `@RestController`) is what tells Spring to treat the return value as the response body instead.

### What does `@RestController` actually do differently from `@Controller`?

It's shorthand for `@Controller` + `@ResponseBody` applied to every method — every method's return value is sent directly as the HTTP response body, with no view resolution attempted.

### Why must `@RequestParam(required = false)` use `Integer` instead of `int`?

Because a missing optional parameter resolves to `null`, and a primitive `int` cannot represent `null` — only a wrapper type like `Integer` can hold that absence without error.

### How does Spring serialize a returned Java object into JSON?

Via Jackson (bundled by default), which inspects the object's getters and uses them to build the JSON representation — a class needs getters for its fields to serialize correctly.

### What is Data Binding / Auto Binding in Spring MVC?

Spring automatically matches incoming query parameters to a Java object's fields when that object type is used as a controller method parameter — no manual parsing code is required.

### What is `DispatcherServlet`'s role, in one sentence?

It's Spring MVC's Front Controller — the single entry point that receives every request and coordinates finding the right handler, running interceptors around it, and invoking it.

### What are interceptors used for, and where do they run relative to the controller?

Cross-cutting concerns (logging, auth, header checks, latency tracking) that don't belong inside individual controllers. `preHandle` runs before the controller (and can block the request by returning `false`), `postHandle` runs after the controller but before the response is finalized, and `afterCompletion` runs after the entire response cycle completes.

### If interceptors A and B are registered in that order, what's the execution order for `preHandle` and `postHandle`?

`preHandle`: A then B. `postHandle`: B then A — the reverse, the same nesting discipline as closing resources in reverse order of opening.

### Why is a Spring "Handler" typed as `Object` internally, and what fixes the problem that creates?

Because Spring supports multiple kinds of handlers (controller methods, `HttpRequestHandler`, others) with no single common concrete type. `HandlerAdapter` fixes the resulting problem: each adapter's `supports(handler)` check identifies whether it knows how to invoke that specific handler type, then typecasts and invokes it (ultimately via reflection).

### What two things does a `HandlerExecutionChain` bundle together?

The matched handler (the controller method to invoke) and the ordered list of interceptors that should wrap its execution.

------------------------------------------------------------------------

❌ Cookies make HTTP stateful.

✔ HTTP itself remains stateless — cookies just give the client something to resend that lets the server *simulate* continuity by looking up stored state on its own side.

------------------------------------------------------------------------

❌ A WAR and a JAR are just two build output formats — pick whichever is convenient.

✔ They represent genuinely different architectures: a WAR needs an external server to run inside; a JAR built by Spring Boot has its own embedded server, with the isolation and independent-scaling consequences that follow from that.

------------------------------------------------------------------------

❌ `@Controller` and `@RestController` behave identically as long as you return a String.

✔ `@Controller` treats a returned String as a view name to resolve; `@RestController` sends it directly as the response body. Mixing them up produces a 404/Whitelabel error instead of the expected text.

------------------------------------------------------------------------

❌ `@RequestParam(required = false) int id` is fine — Java will just use `0` if the parameter is missing.

✔ It throws, because the missing value resolves to `null` first, and a primitive `int` cannot hold `null`. Use `Integer` for any optional request parameter.

------------------------------------------------------------------------

❌ Interceptors are a separate architectural layer sitting outside `DispatcherServlet`.

✔ They're invoked *by* `DispatcherServlet` itself, as part of the `HandlerExecutionChain` it builds for each request — not an independent layer the request passes through on its own.

------------------------------------------------------------------------

## What You Should Remember Forever

```text
HTTP                → stateless; client resends context every request
Cookies              → simulate state via a token the server maps to
                        stored session data

Request              → Method + URI + Version + Headers + Body
Response             → Status Line + Headers + Body

WAR                  → needs an external server (old, standalone)
JAR (Spring Boot)     → has an embedded server (modern, isolated)

@Controller           → return value = view name, by default
@RestController        → return value = response body, always
                          (= @Controller + @ResponseBody everywhere)

@RequestParam(required=false) → use wrapper types (Integer), never
                                  primitives — missing value is null

DispatcherServlet      → Front Controller: finds handler, wraps with
                           interceptors, invokes via HandlerAdapter

HandlerMapping          → Finder
HandlerExecutionChain    → Package (handler + interceptors)
HandlerAdapter            → Executor (typecasts + reflectively invokes)

preHandle   → before controller, CAN block (return false)
postHandle  → after controller, before response
afterCompletion → after the full cycle, for cleanup/logging
```

------------------------------------------------------------------------

## Stage 2 · Week 1 Checklist

- [x] Explain why HTTP is stateless, and how cookies simulate continuity on top of it
- [x] Name every component of an HTTP request and response, and its Spring MVC annotation counterpart
- [x] Explain the difference between a servlet and a servlet container
- [x] Explain the practical trade-offs between a standalone (WAR) and embedded (JAR) server architecture
- [x] Explain why `@Controller` alone doesn't return response text, and how `@RestController` fixes that
- [x] Explain why `@RequestParam(required = false)` requires a wrapper type, not a primitive
- [x] Explain how Spring serializes a returned object into JSON, and what auto-binding does for incoming params
- [x] Explain `DispatcherServlet`'s role as Front Controller, end to end
- [x] Explain what interceptors are for, their three lifecycle methods, and their execution order with multiple interceptors
- [x] Explain why a Spring Handler is typed as `Object` internally, and how `HandlerAdapter` resolves that
