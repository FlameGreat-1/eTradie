

# 🔴 TIER 5: FRONTEND SECURITY

---

## Browser Security

* [ ] CSP implemented
* [ ] HSTS enabled
* [ ] X-Frame-Options
* [ ] X-Content-Type-Options
* [ ] Referrer-Policy

---

## XSS Protection

* [ ] Output encoding
* [ ] DOM sanitization
* [ ] No dangerous HTML rendering

---

## Storage

* [ ] No tokens in localStorage
* [ ] HttpOnly cookies
* [ ] Secure cookies
* [ ] SameSite cookies


> **You cannot prevent users from seeing data that the frontend has already received.**

That's a fundamental web security principle.

If the browser receives it, the user can see it:

* DevTools
* Network tab
* Memory inspection
* Browser extensions
* Local proxies like Burp Suite
* Modified JavaScript

So the goal is **never send sensitive data to the browser in the first place**.

---

# 🚨 Rule #1

## Never send broker credentials to the frontend

The browser should NEVER receive:

```text
MT Login
MT Password
Broker Password
Encrypted Broker Password
API Secret
JWT Signing Secret
Encryption Keys
Internal Service Credentials
```

Not even encrypted versions.

---

# 🚨 Rule #2

## Frontend is an untrusted environment

Treat every browser as compromised.

Assume users can:

* inspect requests
* inspect responses
* modify JavaScript
* intercept API calls
* manipulate forms
* replay requests

Your backend must enforce everything.

Never trust frontend validation.

---

# Production-Grade Frontend Security Checklist

## Sensitive Data Exposure

* [ ] No broker passwords returned by API
* [ ] No encryption keys returned by API
* [ ] No internal service URLs exposed
* [ ] No database identifiers leaked unnecessarily
* [ ] No stack traces shown to users
* [ ] No internal error details exposed

---

## Authentication

* [ ] Access tokens stored in memory or secure cookie strategy
* [ ] Refresh tokens only in HttpOnly cookies
* [ ] Session expiration handling
* [ ] Forced logout capability
* [ ] Device/session management UI

---

## Authorization

Frontend should never decide permissions.

* [ ] Backend validates every action
* [ ] Backend validates resource ownership
* [ ] Backend validates account ownership

Even if a user changes JavaScript manually.

---

## API Security

* [ ] CSRF protection (if cookie auth)
* [ ] Request signing where applicable
* [ ] Rate limiting
* [ ] Replay protection for critical actions

---

## Trading Actions

For actions like:

* connect broker
* place trade
* modify trade
* disconnect account

implement:

* [ ] confirmation workflows
* [ ] server-side validation
* [ ] audit logging

---

## Browser Storage Audit

Check:

### localStorage

Should NOT contain:

* [ ] broker passwords
* [ ] JWT refresh tokens
* [ ] API secrets
* [ ] internal IDs with elevated privileges

---

### sessionStorage

Should NOT contain:

* [ ] broker credentials
* [ ] secrets
* [ ] refresh tokens

---

### IndexedDB

Should NOT contain:

* [ ] sensitive credentials
* [ ] encryption keys

---

# Network Tab Audit

Open DevTools → Network.

Verify:

### Request Payloads

Should never contain:

* [ ] stored broker password after initial submission
* [ ] internal secrets
* [ ] signing keys

---

### Responses

Should never contain:

* [ ] broker password
* [ ] encrypted broker password
* [ ] private keys
* [ ] service credentials

---

# Source Code Exposure

Remember:

Everything shipped to the browser is visible.

Therefore:

Never place in frontend code:

* [ ] database passwords
* [ ] API secrets
* [ ] private keys
* [ ] OpenAI/Anthropic server-side keys
* [ ] JWT signing secrets
* [ ] encryption keys

A React/Vite build does NOT hide secrets.

---

# Environment Variables

Many teams make this mistake.

If you put:

```env
VITE_SECRET_KEY=xxxxx
```

it becomes public.

Anything exposed through client-side build tooling is visible to users.

Only public values belong there.

---

# Trade Platform-Specific Frontend Security

Since you're handling money:

### Prevent UI State Manipulation

Users can modify:

```javascript
user.balance = 1000000
```

inside DevTools.

Therefore:

* [ ] Never trust displayed balance
* [ ] Never trust displayed margin
* [ ] Never trust displayed permissions
* [ ] Never trust displayed account ownership

Every critical action must be validated server-side.

---

# What Users Will Always Be Able to See

Users can always see:

* Their own account data
* Their own positions
* Their own orders
* API requests they make
* API responses sent to them

That is normal.

You cannot hide data that legitimately belongs to them.

---

# What Users Must Never Be Able to See

* Other users' trades
* Other users' positions
* Other users' broker credentials
* Internal service secrets
* Encryption keys
* JWT signing keys
* Database credentials
* Infrastructure topology
* Internal admin APIs

---

# Security Review Question

For every field returned by every API endpoint, ask:

> "If this exact field appears in Chrome DevTools, am I comfortable with the user seeing it?"

If the answer is **No**, then the backend should not send it.

That single rule eliminates a huge percentage of frontend data-leak vulnerabilities.
