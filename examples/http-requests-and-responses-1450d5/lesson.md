# HTTP Requests and Responses

**Learning objective:** Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories.  
**Duration:** 45 minutes (budget 45) · **Format:** self-paced or instructor-led  
**Audience:** Web developers, API designers, and software engineering students learning fundamental web network communication.  
**Prerequisites:** Basic understanding of web browsers and client-server architecture; Familiarity with basic web terminology (URLs, web pages)

## What you will be able to do

- You can define the purpose, message structure, safety, idempotency, and cacheability of GET and POST methods.
- You can categorize HTTP status codes into 2xx (Successful), 4xx (Client Error), and 5xx (Server Error) classes.
- You can evaluate HTTP request/response headers and identify mandatory header requirements such as the Date header.

## Lesson plan

| # | Section | Type | Minutes |
|---|---|---|---|
| 1 | What Happens When You Click a Link? | Hook | 3 |
| 2 | HTTP Request Methods: GET vs. POST | Concept | 10 |
| 3 | HTTP Response Status Categories: 2xx, 4xx, and 5xx | Concept | 10 |
| 4 | Walkthrough: Request and Response Cycles in Action | Worked example | 8 |
| 5 | Hands-on Decision Matrix & Scenario Analysis | Activity | 8 |
| 6 | Test Your Understanding | Knowledge check | 4 |
| 7 | Lesson Wrap-Up and Next Steps | Summary | 2 |
| | **Total** | | **45** |

## 1. What Happens When You Click a Link? (3 min)
<!-- kind: hook -->

Imagine visiting your favorite online store. You click on a product page to view a pair of shoes. A moment later, you enter your shipping information and click "Place Order." 

To your web browser, these two clicks feel completely distinct. The first click simply retrieves information without changing anything on the store's servers. The second click sends data that creates a new purchase order and charges your account—an action you certainly wouldn't want duplicated by accident!

Under the hood, both interactions rely on **HTTP (Hypertext Transfer Protocol)**, an application-layer protocol sent over TCP or TLS-encrypted TCP connections to exchange request and response messages [S5]. Introduced in 1990 and standardized by specifications such as RFC 9110, HTTP provides the foundation for web communication [S6]. In this lesson, we will explore how HTTP request methods like **GET** and **POST** differ, and how servers use status categories (**2xx**, **4xx**, and **5xx**) to report the outcome of every request [S1, S2, S6].

*Sources: [S1], [S2], [S5], [S6]*

## 2. HTTP Request Methods: GET vs. POST (10 min)
<!-- kind: concept -->

An **HTTP request method** (sometimes called an HTTP verb) indicates the primary purpose of a request and what outcome is expected if the request succeeds [S2, S5]. The two most foundational methods on the web are `GET` and `POST` [S2].

### The GET Method
The **GET** method requests a representation of a specified resource without altering server state [S2, S3]. When communicating with an origin server in HTTP/1.1, GET uses an absolute path (for example, `/path/to/file.html`), whereas requests routed through proxies use an absolute URL [S3].

- **Request Body**: GET requests should only retrieve data and **must not** contain a request body [S2, S3]. Sending a message body in a GET request has undefined semantics; some servers reject GET requests containing a body with a 4xx client error status code [S3].
- **Safety**: A method is **safe** if it is used only to retrieve data and does not alter the state of the server [S2]. GET is safe [S2].
- **Idempotency**: A method is **idempotent** if executing it once yields the exact same server state as executing it several times successively [S4]. GET is idempotent because repeating identical GET requests produces no side effects on the server [S2].
- **Cacheability**: GET requests and responses are cacheable by default [S2].

### The POST Method
The **POST** method submits an entity to a target resource, typically causing state changes or side effects on the server (such as submitting HTML form results or placing orders) [S2, S4, S5].

- **Request Body**: POST carries payload data in its request body [S4, S5]. The format of the body is specified by the `Content-Type` request header [S4]. HTML forms using POST encode content using either `application/x-www-form-urlencoded` or `multipart/form-data` (which separates data blocks using a boundary delimiter, such as `boundary="delimiter12345"`) [S4]. Non-form requests (e.g., sent via `fetch()`) can carry any body format [S4].
- **Safety and Idempotency**: POST is **neither safe nor idempotent** [S2, S4]. Submitting identical POST requests multiple times can cause duplicated side effects (e.g., placing multiple identical orders) [S4].
- **Cacheability**: POST responses are not reusable for satisfying subsequent POST requests because POST is potentially unsafe [S6]. However, a POST response can be cached to satisfy subsequent GET or HEAD requests if it includes explicit freshness information and a `Content-Location` header matching the target URI [S2, S6].

### Analogy: Reader vs. Mailbox
Think of a **GET** request as looking at a notice pinned to a public bulletin board. Reading it multiple times changes nothing on the board (safe, idempotent). A **POST** request is like dropping a completed application form into a drop box. Dropping three copies of the form produces three entries (non-idempotent) and changes the internal state of the organization receiving them.

### GET vs. POST Summary Table
| Property | GET | POST |
| :--- | :--- | :--- |
| **Primary Purpose** | Retrieve resource data [S2, S3] | Submit payload to cause side effects [S2, S4] |
| **Request Body** | Must NOT contain body (undefined semantics) [S2, S3] | Carries payload data in body [S4, S5] |
| **Safe?** | Yes [S2] | No [S2, S4] |
| **Idempotent?** | Yes [S2] | No [S2, S4] |
| **Default Cacheability** | Cacheable by default [S2] | Unsafe for POST reuse; conditional for GET [S2, S6] |

> ### Common Mistake
> **Including a payload body inside a GET request for complex search queries.** RFC specifications leave the semantics of a GET body undefined [S3]. Some servers or firewalls will reject GET requests carrying bodies with a 4xx client error [S3]. To send safe, complex search requests with content bodies, modern standards introduce specific methods like `QUERY` [S8].

*Sources: [S2], [S3], [S4], [S5], [S6], [S8]*

## 3. HTTP Response Status Categories: 2xx, 4xx, and 5xx (10 min)
<!-- kind: concept -->

HTTP status codes are three-digit numbers generated by servers to communicate the outcome of a client's request [S1, S6]. These status codes are divided into five distinct classes based on their first digit [S1]. We focus on the three primary outcome classes: **2xx**, **4xx**, and **5xx** [S1, S6].

### 2xx: Successful Category
The **2xx (Successful)** status category indicates that the client's request was successfully received, understood, and accepted by the server [S1, S6].
- `200 OK`: Standard response for successful requests [S1, S3]. For GET requests, the requested resource representation is transmitted in the response body [S1, S3]. For HEAD requests, representation headers are returned without a body [S1, S6]. For POST or PUT requests, a description of the result is included in the body [S1].
- `201 Created`: Indicates that the request succeeded and a new resource was created as a result, typically sent after POST or PUT operations [S1].

### 4xx: Client Error Category
The **4xx (Client Error)** status category indicates that the request contains bad syntax or cannot be fulfilled due to a client-side problem [S1, S6].
- `401 Unauthorized`: Semantically means **"unauthenticated"** [S1]. It indicates that the client must authenticate itself to obtain the requested response [S1].
- `410 Gone`: Sent when the requested content has been permanently deleted from the server with no forwarding address, instructing clients and caches to remove references [S1].
- `4xx Client Error`: Returned by certain servers when a GET request is improperly submitted with a payload body [S3].

### 5xx: Server Error Category
The **5xx (Server Error)** status category indicates that the server encountered an internal failure or error condition that prevented it from fulfilling a valid request [S6]. The error lies entirely on the server side [S6].

### Header Rules: The Date Header
HTTP specifications establish strict rules for server header generation:
- Origin servers with a clock **MUST** generate a `Date` header field in all **2xx**, **3xx**, and **4xx** responses [S6].
- Origin servers **MAY** generate a `Date` header in **1xx** and **5xx** responses [S6].

### Response Status Category Overview Table
| Class | Category Name | Responsibility | Specific Code Examples | Date Header Rule |
| :--- | :--- | :--- | :--- | :--- |
| **2xx** | Successful | Server accepted & fulfilled request [S1, S6] | `200 OK`, `201 Created` [S1] | **MUST** generate [S6] |
| **4xx** | Client Error | Client sent malformed/invalid request [S1, S6] | `401 Unauthorized`, `410 Gone` [S1] | **MUST** generate [S6] |
| **5xx** | Server Error | Server failed during processing [S6] | Server internal failure codes [S6] | **MAY** generate [S6] |

> ### Common Mistake
> **Confusing `401 Unauthorized` with a permission denial.** Despite its name, `401 Unauthorized` semantically means **"unauthenticated"**—the user has not provided valid authentication credentials [S1].

*Sources: [S1], [S3], [S6]*

## 4. Walkthrough: Request and Response Cycles in Action (8 min)
<!-- kind: worked_example -->

Let me walk you through four realistic request and response exchanges, highlighting request structure, header requirements, body handling, and status code categories.

### Scenario 1: Fetching a Web Page (Safe GET Request -> 200 OK)
A client issues a GET request to retrieve a contact page from an origin server [S3]:

**Client Request**:
```http
GET /contact HTTP/1.1
Host: example.com
User-Agent: curl/8.6.0
Accept: */*
```
*Explanation*: The GET method uses an absolute path (`/contact`) in HTTP/1.1 and contains no request body [S3].

**Server Response**:
```http
HTTP/1.1 200 OK
Content-Type: text/html; charset=UTF-8
Date: Fri, 21 Jun 2024 14:18:33 GMT
Last-Modified: Thu, 17 Oct 2019 07:18:26 GMT
Content-Length: 1234

<!doctype html>
<!-- HTML content follows -->
```
*Explanation*: The server responds with `200 OK` (2xx Successful category) [S1, S3]. Because this is a 2xx response from an origin server with a clock, the `Date` header **MUST** be included [S6]. The target content is returned in the response body [S1, S3].

---

### Scenario 2: Submitting Form Data (Unsafe POST Request -> 201 Created)
A user submits a web form to create a resource [S4]. HTML form POST requests encode content using `application/x-www-form-urlencoded` or `multipart/form-data` [S4].

**Client Request (`application/x-www-form-urlencoded`)**:
```http
POST /test HTTP/1.1
Host: example.com
Content-Type: application/x-www-form-urlencoded
Content-Length: 27

field1=value1&field2=value2
```

**Alternative Client Request (`multipart/form-data`)**:
```http
POST /test HTTP/1.1
Host: example.com
Content-Type: multipart/form-data; boundary="delimiter12345"

--delimiter12345
Content-Disposition: form-data; name="field1"

value1
--delimiter12345--
```
*Explanation*: Unlike GET, POST carries payload data inside the request body and specifies the format with the `Content-Type` header [S4]. Multipart data separates payload blocks using a boundary delimiter like `boundary="delimiter12345"` [S4].

**Server Response**:
```http
HTTP/1.1 201 Created
Content-Type: text/plain
Date: Fri, 21 Jun 2024 14:19:00 GMT

Resource successfully created.
```
*Explanation*: The server processes the state change and responds with `201 Created` (2xx Successful) [S1]. The `Date` header is mandatory [S6].

---

### Scenario 3: Missing Credentials (401 Unauthorized)
A client attempts to access a protected account page without including authentication header credentials [S1].

**Server Response**:
```http
HTTP/1.1 401 Unauthorized
Content-Type: text/plain
Date: Fri, 21 Jun 2024 14:20:12 GMT

Authentication credentials missing or invalid.
```
*Explanation*: The status is `401 Unauthorized` (4xx Client Error category), which semantically means the client is **unauthenticated** [S1]. A `Date` header MUST be present because it is a 4xx response [S6].

---

### Scenario 4: Accessing a Removed Resource (410 Gone)
A client requests an old promotional document that was permanently removed [S1].

**Server Response**:
```http
HTTP/1.1 410 Gone
Content-Type: text/plain
Date: Fri, 21 Jun 2024 14:21:05 GMT

This resource has been permanently deleted.
```
*Explanation*: The server responds with `410 Gone` (4xx Client Error category), notifying the client and caches that the resource has been permanently deleted with no forwarding address [S1].

*Sources: [S1], [S3], [S4], [S6]*

## 5. Hands-on Decision Matrix & Scenario Analysis (8 min)
<!-- kind: activity -->

In this activity, you will analyze four real-world scenarios and determine the appropriate HTTP request method, its safety/idempotency properties, and the expected status code category.

### Task Instructions
For each scenario below, record your answers on a piece of paper or in a text editor:
1. Choose the primary HTTP method (`GET` or `POST`) [S2].
2. State whether the method is **Safe** and **Idempotent** [S2, S4].
3. Identify whether a request body should be included [S3, S4].
4. Determine the expected HTTP status category (**2xx**, **4xx**, or **5xx**) and specific code if applicable [S1, S6].

---

### Scenarios to Analyze
1. **Scenario A**: A user opens their browser and navigates to the homepage (`/index.html`) to read news articles [S3].
2. **Scenario B**: A user submits a registration form containing their email and password to set up a new account [S4].
3. **Scenario C**: An unauthenticated script requests a restricted user settings endpoint without sending valid credentials [S1].
4. **Scenario D**: An external client sends a GET request that includes a JSON payload body to an origin server that strictly rejects GET request bodies [S3].

---

### Expected Results & Solution Key
- **Scenario A**:
  - Method: `GET` [S3]
  - Properties: Safe = Yes, Idempotent = Yes [S2]
  - Request Body: No body (MUST NOT contain body) [S2, S3]
  - Status Category: `2xx` (specifically `200 OK`) [S1, S3]

- **Scenario B**:
  - Method: `POST` [S4]
  - Properties: Safe = No, Idempotent = No [S2, S4]
  - Request Body: Yes (encoded via `application/x-www-form-urlencoded` or `multipart/form-data`) [S4]
  - Status Category: `2xx` (specifically `201 Created` or `200 OK`) [S1]

- **Scenario C**:
  - Method: `GET` (or POST depending on operation)
  - Status Category: `4xx` Client Error (specifically `401 Unauthorized`, meaning unauthenticated) [S1, S6]

- **Scenario D**:
  - Result: The request violates GET semantics (undefined body semantics) [S3].
  - Status Category: `4xx` Client Error (server rejects the GET body) [S3].

### Self-Check
Did you correctly identify that GET requests must not carry request bodies and are safe/idempotent, while POST requests carry payloads and are neither safe nor idempotent [S2, S3, S4]?

*Sources: [S1], [S2], [S3], [S4], [S6]*

## 6. Test Your Understanding (4 min)
<!-- kind: knowledge_check -->

Answer the following multiple-choice questions to evaluate your understanding of HTTP request methods and status code categories.

**Q1.** A web user double-clicks the 'Submit Payment' button on an order checkout page. The browser issues two identical HTTP POST requests to `/checkout`. What is the expected behavior regarding idempotency?

- A) POST is idempotent, so executing it twice yields the exact same server state as executing it once.
- B) POST is safe and idempotent, so duplicate requests are automatically ignored by origin servers.
- C) POST is neither safe nor idempotent, so executing it twice may cause side effects like creating duplicate orders.
- D) POST is safe but not idempotent, so it retrieves data while modifying response headers.

**Q2.** A client application constructs an HTTP GET request to search a database and includes a JSON payload in the request body. What is the standard HTTP semantics rule for this request?

- A) Sending a body in a GET request is safe and explicitly mandated by RFC 9110.
- B) Sending a body in a GET request has undefined semantics, and some servers reject it with a 4xx client error.
- C) GET request bodies are automatically converted to POST requests by intermediate proxies.
- D) GET request bodies are cacheable by default if a Content-Type header is provided.

**Q3.** An API client sends a request to fetch protected account information without presenting valid authentication credentials. The server responds with status code 401. What does 401 semantically mean?

- A) The server encountered an internal failure processing the request.
- B) The client is authenticated but lacks permission to view the resource.
- C) The client is unauthenticated and must provide valid credentials.
- D) The requested content has been permanently deleted with no forwarding address.

**Q4.** According to RFC 9110, which rule correctly describes the generation of the Date header field by origin servers with a clock?

- A) Origin servers MUST generate a Date header in 2xx, 3xx, and 4xx responses, and MAY generate one in 1xx and 5xx responses.
- B) Origin servers MUST generate a Date header in 5xx responses, but MAY omit it in 2xx and 4xx responses.
- C) Origin servers MUST generate a Date header in all 5xx and 1xx responses, but MAY omit it in 2xx responses.
- D) Origin servers MAY generate a Date header in 2xx responses, but MUST NOT generate one in 4xx responses.

**Q5.** A client submits an HTML form using the POST method with file upload capabilities. How is the payload body formatted?

- A) It must use absolute URLs with path markers.
- B) It is formatted using multipart/form-data with a boundary delimiter or application/x-www-form-urlencoded.
- C) It is appended directly to the URL query string with undefined body semantics.
- D) It uses HEAD representation headers without a body payload.

**Q6.** A client requests a URL for a promotional campaign that was permanently deleted from the web server with no forwarding address. What response status code should the server return?

- A) 201 Created
- B) 401 Unauthorized
- C) 410 Gone
- D) 500 Server Error

*Sources: [S1], [S2], [S3], [S4], [S6]*

## 7. Lesson Wrap-Up and Next Steps (2 min)
<!-- kind: summary -->

### Summary of Core Concepts
- **GET**: Used to retrieve target resource representations [S2, S3]. It is safe, idempotent, cacheable by default, and must not carry a request body [S2, S3].
- **POST**: Used to submit payloads that alter server state or create resources [S2, S4]. It is neither safe nor idempotent, carries payload data in its request body (e.g., `application/x-www-form-urlencoded` or `multipart/form-data`), and its responses cannot satisfy subsequent POST requests [S2, S4, S6].
- **Status Categories**: Status codes communicate outcome states [S1, S6]:
  - **2xx (Successful)**: Request accepted and fulfilled (e.g., `200 OK`, `201 Created`) [S1, S6].
  - **4xx (Client Error)**: Client-side syntax or auth issue (e.g., `401 Unauthorized` [unauthenticated], `410 Gone` [permanently deleted]) [S1, S6].
  - **5xx (Server Error)**: Server encountered an internal failure while processing [S6].
- **Header Requirements**: Origin servers with a clock **MUST** include a `Date` header in 2xx, 3xx, and 4xx responses, and **MAY** include one in 5xx responses [S6].

### Next Step
Next, explore HTTP headers in depth (such as cache-control and custom headers) or learn how modern APIs utilize HTTP methods for RESTful system design!

*Sources: [S1], [S2], [S3], [S4], [S6]*

## Key takeaways

- GET requests retrieve resource representations without modifying server state, making GET both safe and idempotent [S2, S3].
- GET requests must not contain a request body; sending a body in a GET request has undefined semantics and may cause 4xx server rejections [S2, S3].
- POST requests submit payload data in the message body to cause side effects, making POST neither safe nor idempotent [S2, S4].
- HTTP status categories categorize server outcome states: 2xx means Successful, 4xx means Client Error, and 5xx means Server Error [S1, S6].
- Status code 401 Unauthorized semantically means 'unauthenticated', requiring the client to present valid credentials [S1].
- Origin servers with a clock MUST generate a Date header in all 2xx, 3xx, and 4xx responses, and MAY generate one in 5xx responses [S6].

## Answer key

1. **C**: POST is neither safe nor idempotent [S2, S4]. Submitting duplicate POST requests can result in duplicate side effects on the server, such as creating two distinct purchase orders [S4].
2. **B**: GET requests should only retrieve data and must not contain a body [S2, S3]. Standard HTTP leaves body semantics in GET requests undefined, and some servers reject GET requests carrying bodies with a 4xx client error status code [S3].
3. **C**: Although status code 401 is named 'Unauthorized', HTTP specifications clarify that it semantically means 'unauthenticated'—the client must authenticate itself to receive the requested response [S1].
4. **A**: RFC 9110 specifies that origin servers with a clock MUST generate a Date header in all 2xx, 3xx, and 4xx responses, and MAY generate one in 1xx and 5xx responses [S6].
5. **B**: HTML forms using POST encode body content using either application/x-www-form-urlencoded or multipart/form-data (which separates data blocks using a boundary delimiter, such as boundary="delimiter12345") [S4].
6. **C**: Status code 410 Gone (in the 4xx Client Error category) is sent when requested content has been permanently deleted from the server with no forwarding address [S1].

## Supplementary videos (optional, outside the 45 minutes)

- **[HTTP Request Methods | GET, POST, PUT, DELETE](https://www.youtube.com/watch?v=tkfVQK6UxDI)** (Curious Code, 3:01). *When:* before. *Why:* Provides a quick, visual 3-minute explanation of core HTTP request methods (GET, POST, PUT, DELETE) and their basic purposes. [V1]
- **[HTTP Status Codes Explained In 5 Minutes](https://www.youtube.com/watch?v=qmpUfWN7hh4)** (ByteByteGo, 5:07). *When:* during. *Why:* Offers a concise 5-minute visual overview explaining status code categories (2xx, 4xx, 5xx) and common HTTP response states. [V2]

## References

### Websites

- [S1] HTTP response status codes - HTTP | MDN. developer.mozilla.org. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status>
- [S2] HTTP request methods - HTTP | MDN. developer.mozilla.org. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods>
- [S3] GET request method - HTTP | MDN. developer.mozilla.org. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/GET>
- [S4] POST request method - HTTP | MDN. developer.mozilla.org. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/POST>
- [S5] Overview of HTTP - HTTP | MDN. developer.mozilla.org. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview>
- [S6] RFC 9110: HTTP Semantics. rfc-editor.org. <https://www.rfc-editor.org/rfc/rfc9110.html#name-status-codes>
- [S7] HTTP headers - HTTP | MDN. developer.mozilla.org. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers>
- [S8] QUERY request method - HTTP | MDN. developer.mozilla.org. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/QUERY>

### Books

- [B1] *HTTP: The Definitive Guide*. David Gourley, Brian Totty, Linda Mui · O'Reilly Media, Incorporated · 1997. <https://openlibrary.org/works/OL16026044W>
- [B2] *RESTful Web APIs: Services for a Changing World*. Leonard Richardson, Michael Amundsen, Sam Ruby · O'Reilly Media · 2013. <https://openlibrary.org/works/OL19548004W>
- [B3] *Learning HTTP/2*. Stephen Ludin · CreateSpace Independent Publishing Platform · 2017. <https://openlibrary.org/works/OL20055086W>

### Videos

- [V1] HTTP Request Methods | GET, POST, PUT, DELETE. Curious Code, YouTube. <https://www.youtube.com/watch?v=tkfVQK6UxDI>
- [V2] HTTP Status Codes Explained In 5 Minutes. ByteByteGo, YouTube. <https://www.youtube.com/watch?v=qmpUfWN7hh4>
