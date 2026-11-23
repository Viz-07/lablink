# Security

| Threat | Implemented control |
| --- | --- |
| Unexpected input | Pydantic request models reject extra fields and validate identifiers, lengths, ranges, and slot intervals. |
| Cross-site request forgery | All mutating API requests require `X-Requested-With: LabLink`. The session cookie uses `SameSite=Lax`. |
| Session forgery or theft | The session is HMAC-SHA256-signed and time-limited. The cookie is `HttpOnly` and has `Secure` in production. The API looks up the current roles and permissions from repository state. |
| Unauthorized actions | API dependencies enforce sign-in and role. Services enforce scope for bookings, approval requests, analytics, and conflicts. |
| Script injection or clickjacking | CSP disallows inline script and style, restricts resources to defined sources, and blocks framing. The app also sends `X-Frame-Options: DENY` and `nosniff`. |
| Insecure transport | Production responses include HSTS and CSP's upgrade directive. |
| Request abuse | Demo authentication is limited to 10 requests per minute per IP. AI, recommend, and summary requests are limited to 10 per minute and 100 per day per signed-in user, with IP fallback. Other writes are limited to 60 per minute per subject. Mutating API bodies are limited to 64 KB. |
| Information leakage | Unexpected 500 responses carry a generic message and request ID. API responses use `no-store`, and API docs are disabled in production. AI failure logs record the feature and exception type. |
| Prompt injection or invented records | The system prompt treats the delimited `USER_TEXT` field as untrusted data. AI responses use typed schemas, and equipment or booking IDs are checked against the input set where applicable. |
| Credential exposure and container privilege | Vertex AI uses Application Default Credentials from the runtime service account in production. The deployment guide supplies the session secret from Secret Manager. The container runs as UID 10001. |
| Untraceable privileged changes | Equipment edits, certification changes, review decisions, allocation actions, and demo reset are among the actions recorded in the audit log. |

The campus demo deliberately offers seeded persona switching. Rate limits and in-memory state are local to the running process. See the [deployment guide](../implementation.md) for the demo configuration.
