# QC Layer 1: Research & Factual Accuracy Audit

**Lesson:** HTTP Requests and Responses  
**Lesson version audited:** v1  
**Model:** gemini-3.5-flash  
**Date:** 2026-11-06T17:17:41+00:00  
**Accuracy score:** 88/100 (computed from claim verdicts)

## Summary

The lesson relies on highly authoritative standards and MDN documentation to explain GET and POST methods and status code categories. The main area for improvement is addressing the coverage gap in the 5xx status category by providing concrete status code examples (e.g., 500, 503) alongside 2xx and 4xx codes, and refocusing header rules toward the primary learning objectives.

## Claim verification

Verdict counts: partially_supported: 1, supported: 9, unsupported: 2

| # | Claim | Section | Verdict | Explanation | Correction | Evidence |
|---|---|---|---|---|---|---|
| 1 | HTTP (Hypertext Transfer Protocol) is an application-layer protocol sent over TCP or TLS-encrypted TCP connections to exchange request and response messages. | 1. What Happens When You Click a Link? | **supported** | The evidence confirms that HTTP is an application-layer protocol sent over TCP or TLS-encrypted TCP connections to exchange request/response messages. |  | [E7] MDN states HTTP is an application layer protocol sent over TCP or TLS-encrypted TCP connection to exchange request/response pairs. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview> |
| 2 | The GET method requests a representation of a specified resource without altering server state. | 2. HTTP Request Methods: GET vs. POST | **supported** | The GET method requests a representation of a resource and is classified as a safe method that does not alter server state. |  | [E4][E8] MDN states GET requests a representation of the specified resource and is a safe method that does not alter the state of the server. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/GET> <https://developer.mozilla.org/en-US/docs/Glossary/Safe/HTTP> |
| 3 | GET requests should only retrieve data and must not contain a request body. | 2. HTTP Request Methods: GET vs. POST | **partially_supported** | While GET requests should only retrieve data and shouldn't contain a request body, claiming they 'must not' contain one is imprecise because the spec defines GET body semantics as undefined rather than strictly forbidden. | GET requests should only be used to request data and shouldn't contain a request body, though its semantics are undefined. | [E4] MDN specifies GET requests should only be used to request data and shouldn't contain a body, noting that the semantics of sending a body in GET requests are undefined. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/GET> |
| 4 | HTML forms using POST encode content using either application/x-www-form-urlencoded or multipart/form-data. | 2. HTTP Request Methods: GET vs. POST | **supported** | The evidence explicitly lists application/x-www-form-urlencoded and multipart/form-data as the body content encodings for HTML forms using POST. |  | [E3] MDN states that for HTML forms using POST, the body encoding may be application/x-www-form-urlencoded or multipart/form-data. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/POST> |
| 5 | POST is neither safe nor idempotent. | 2. HTTP Request Methods: GET vs. POST | **supported** | The evidence identifies POST as an unsafe method and distinguishes it from idempotent unsafe methods like PUT and DELETE. |  | [E6][E8] MDN and RFC 9110 state POST is unsafe, while PUT and DELETE are categorized as idempotent but unsafe methods, confirming POST is neither safe nor idempotent. <https://datatracker.ietf.org/doc/html/rfc9110> <https://developer.mozilla.org/en-US/docs/Glossary/Safe/HTTP> |
| 6 | A POST response can be cached to satisfy subsequent GET or HEAD requests if it includes explicit freshness information and a Content-Location header matching the target URI. | 2. HTTP Request Methods: GET vs. POST | **supported** | The RFC specification confirms that a cached POST response containing explicit freshness information and a Content-Location matching the POST target URI can satisfy subsequent GET or HEAD requests. |  | [E6] RFC 9110 states that POST responses are cacheable when they include explicit freshness information and a Content-Location header field matching the POST target URI, and can be reused to satisfy later GET or HEAD requests. <https://datatracker.ietf.org/doc/html/rfc9110> |
| 7 | Status code 201 Created indicates that the request succeeded and a new resource was created as a result, typically sent after POST or PUT operations. | 3. HTTP Response Status Categories: 2xx, 4xx, and 5xx | **supported** | The evidence confirms 201 Created indicates successful resource creation and is commonly returned after POST or PUT requests. |  | [E2][E6][E9] MDN and RFC 7231 state 201 Created indicates that a request led to the creation of a resource, commonly sent as the result of POST or PUT requests. <https://datatracker.ietf.org/doc/html/rfc7231> <https://datatracker.ietf.org/doc/html/rfc9110> <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/201> |
| 8 | Status code 401 Unauthorized semantically means 'unauthenticated'. | 3. HTTP Response Status Categories: 2xx, 4xx, and 5xx | **supported** | The evidence shows 401 Unauthorized is returned specifically when a request lacks valid authentication credentials. |  | [E5] MDN states 401 Unauthorized indicates a request was not successful because it lacks valid authentication credentials, contrasting with 403 Forbidden where credentials are valid. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/401> |
| 9 | Status code 410 Gone is sent when the requested content has been permanently deleted from the server with no forwarding address. | 3. HTTP Response Status Categories: 2xx, 4xx, and 5xx | **supported** | The evidence confirms that 410 Gone indicates the target resource is no longer available at the origin server and that this condition is likely permanent. |  | [E10] MDN states 410 Gone indicates that the target resource is no longer available at the origin server and that this condition is likely to be permanent. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/410> |
| 10 | Origin servers with a clock MUST generate a Date header field in all 2xx, 3xx, and 4xx responses. | 3. HTTP Response Status Categories: 2xx, 4xx, and 5xx | **unsupported** | The provided evidence contains example HTTP responses with Date headers but does not state the specification rules requiring origin servers to generate a Date header field. |  | [E1][E2][E4][E5][E6] The provided evidence does not mention normative requirements regarding when origin servers MUST generate a Date header field. <https://datatracker.ietf.org/doc/html/rfc7230> <https://datatracker.ietf.org/doc/html/rfc7231> <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/GET> <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/401> |
| 11 | Origin servers MAY generate a Date header in 1xx and 5xx responses. | 3. HTTP Response Status Categories: 2xx, 4xx, and 5xx | **unsupported** | The provided evidence does not state rules regarding whether origin servers MAY generate a Date header in 1xx and 5xx responses. |  | [E1][E2][E4][E5][E6] The provided evidence does not address the optional generation of Date headers by origin servers in 1xx or 5xx responses. <https://datatracker.ietf.org/doc/html/rfc7230> <https://datatracker.ietf.org/doc/html/rfc7231> <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/GET> <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/401> |
| 12 | When communicating with an origin server in HTTP/1.1, GET uses an absolute path, whereas requests routed through proxies use an absolute URL. | 2. HTTP Request Methods: GET vs. POST | **supported** | The evidence specifies that the request target is an absolute path when making requests to an origin server and an absolute URL in requests to proxies. |  | [E3][E4] MDN states that the request target is an absolute path in requests to an origin server and an absolute URL in requests to proxies. <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/POST> <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/GET> |

## Source reliability and relevance

| Id | Source | Reliability | Relevance | Reachable | Cited | Note |
|---|---|---|---|---|---|---|
| S1 | [HTTP response status codes - HTTP \| MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status) | high | high | yes | yes | Official MDN documentation on HTTP response status codes; highly authoritative and directly relevant to the core objective. |
| S2 | [HTTP request methods - HTTP \| MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods) | high | high | yes | yes | Official MDN documentation covering HTTP request methods including GET and POST. |
| S3 | [GET request method - HTTP \| MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/GET) | high | high | yes | yes | Official MDN documentation detailing GET request characteristics, safety, and idempotency. |
| S4 | [POST request method - HTTP \| MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/POST) | high | high | yes | yes | Official MDN documentation detailing POST request behavior, encodings, and semantics. |
| S5 | [Overview of HTTP - HTTP \| MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview) | high | high | yes | yes | Official MDN documentation providing an architectural overview of HTTP protocol messages. |
| S6 | [RFC 9110: HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110.html#name-status-codes) | high | high | yes | yes | IETF RFC 9110 official specification; the definitive standard for HTTP semantics and status codes. |
| S7 | [HTTP headers - HTTP \| MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers) | high | low | yes | no | Official MDN documentation on HTTP headers; included in sources list but uncited in the lesson. |
| S8 | [QUERY request method - HTTP \| MDN](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/QUERY) | medium | medium | yes | yes | MDN documentation on the experimental QUERY method; relevant context for modern GET payload alternatives. |
| B1 | [HTTP: The Definitive Guide](https://openlibrary.org/works/OL16026044W) | high | low | yes | no | Verified reference book on HTTP protocol fundamentals; listed in sources but not cited in the text. |
| B2 | [RESTful Web APIs: Services for a Changing World](https://openlibrary.org/works/OL19548004W) | high | low | yes | no | Verified reference book on RESTful API design; listed in sources but not cited in the text. |
| B3 | [Learning HTTP/2](https://openlibrary.org/works/OL20055086W) | high | low | yes | no | Verified reference book on HTTP/2; listed in sources but not cited in the text. |

## Issues and suggested improvements

### QC1-2 · MAJOR · claim unsupported
- **Where:** 3. HTTP Response Status Categories: 2xx, 4xx, and 5xx
- **Text:** "Origin servers with a clock MUST generate a Date header field in all 2xx, 3xx, and 4xx responses."
- **Problem:** The provided evidence contains example HTTP responses with Date headers but does not state the specification rules requiring origin servers to generate a Date header field.
- **Suggestion:** Add an authoritative citation or remove the claim.

### QC1-3 · MAJOR · claim unsupported
- **Where:** 3. HTTP Response Status Categories: 2xx, 4xx, and 5xx
- **Text:** "Origin servers MAY generate a Date header in 1xx and 5xx responses."
- **Problem:** The provided evidence does not state rules regarding whether origin servers MAY generate a Date header in 1xx and 5xx responses.
- **Suggestion:** Add an authoritative citation or remove the claim.

### QC1-4 · MAJOR · coverage_gap
- **Where:** 3. HTTP Response Status Categories: 2xx, 4xx, and 5xx
- **Text:** "The 5xx (Server Error) status category indicates that the server encountered an internal failure or error condition that prevented it from fulfilling a valid request [S6]. The error lies entirely on the server side [S6]."
- **Problem:** Although the stated learning objective requires students to distinguish between 2xx, 4xx, and 5xx response categories, the text provides specific code examples for 2xx (200, 201) and 4xx (401, 410) but omits any concrete 5xx status code examples (such as 500 Internal Server Error or 503 Service Unavailable) in Section 3 and Section 4.
- **Suggestion:** Include concrete 5xx code definitions (e.g., 500 Internal Server Error, 503 Service Unavailable) in Section 3 and add a corresponding 5xx response cycle in Section 4's worked examples.

### QC1-1 · MINOR · claim partially supported
- **Where:** 2. HTTP Request Methods: GET vs. POST
- **Text:** "GET requests should only retrieve data and must not contain a request body."
- **Problem:** While GET requests should only retrieve data and shouldn't contain a request body, claiming they 'must not' contain one is imprecise because the spec defines GET body semantics as undefined rather than strictly forbidden.
- **Suggestion:** GET requests should only be used to request data and shouldn't contain a request body, though its semantics are undefined.

### QC1-5 · MINOR · out_of_scope_content
- **Where:** 3. HTTP Response Status Categories: 2xx, 4xx, and 5xx
- **Text:** "Header Rules: The Date Header: Origin servers with a clock MUST generate a Date header field in all 2xx, 3xx, and 4xx responses [S6]."
- **Problem:** The lesson introduces granular Date header requirement rules across response status classes and assesses them in Q4, which distracts from the primary objective of understanding GET/POST methods and 2xx/4xx/5xx status code categories.
- **Suggestion:** Replace the Date header requirement rules and Knowledge Check Q4 with content and questions that reinforce distinguishing between 2xx, 4xx, and 5xx status code categories.


## Verification searches run

- HTTP request methods GET POST
- HTTP response status codes 201 401 410
- HTTP Date header origin server MUST MAY
- HTTP POST response caching Content-Location
- HTTP request line absolute path origin server proxy

## Pages consulted during verification

- RFC 7230 - Hypertext Transfer Protocol (HTTP/1.1): Message Syntax and Routing: <https://datatracker.ietf.org/doc/html/rfc7230>
- RFC 7231 - Hypertext Transfer Protocol (HTTP/1.1): Semantics and Content: <https://datatracker.ietf.org/doc/html/rfc7231>
- POST request method - HTTP | MDN: <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/POST>
- GET request method - HTTP | MDN: <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods/GET>
- 401 Unauthorized - HTTP | MDN: <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/401>
- RFC 9110 - HTTP Semantics: <https://datatracker.ietf.org/doc/html/rfc9110>
- Overview of HTTP - HTTP | MDN: <https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview>
- Safe (HTTP Methods) - Glossary | MDN: <https://developer.mozilla.org/en-US/docs/Glossary/Safe/HTTP>
- 201 Created - HTTP | MDN: <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/201>
- 410 Gone - HTTP | MDN: <https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status/410>
