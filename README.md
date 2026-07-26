<p align="center">
  <h1 align="center">TimeNest Chat Service</h1>
  <p align="center"><strong>Real-time Chat Microservice for TimeNest</strong></p>
</p>

<p align="center">
  A standalone FastAPI service powering real-time inter-employee and client
  chat inside the TimeNest platform.
</p>

---

## What is this service?

This is the WebSocket-based chat backend for TimeNest. It runs as an
**independent FastAPI microservice**, separate from the main Laravel
application, but it is not a disconnected system — it shares the same
MySQL database and JWT secret as the Laravel backend.

Why a separate service instead of building chat inside Laravel?

- WebSocket connections are long-lived and async-native — Python's `asyncio`
  + FastAPI handles thousands of concurrent open connections far more
  naturally than PHP-FPM's request/response model.
- Chat can scale, deploy, and restart independently of the main application,
  without affecting attendance, leave, or worklog APIs.
- It keeps Laravel focused on what it's good at (business logic, HTTP APIs)
  and lets this service focus on what it's good at (real-time messaging).

This is **not a rewrite of Laravel in Python**. This service does not own
user or organization data — it only owns chat-specific tables. Everything
else it needs (users, organizations) is read from the same database Laravel
already manages.

> ⚠️ Status: **Under active development.** Core architecture, JWT
> verification flow, and configuration layer are complete. No chat tables
> exist yet — this is being built from a clean slate.

---

## How it fits into TimeNest

```
                     ┌─────────────────────┐
                     │   MySQL Database     │
                     │  (shared, single DB) │
                     └─────────▲───────────┘
                               │
             ┌─────────────────┴─────────────────┐
             │                                     │
   ┌─────────▼─────────┐               ┌───────────▼───────────┐
   │  Laravel Backend    │               │  Chat Microservice     │
   │  (owns users, orgs,  │               │  (FastAPI, owns only   │
   │  attendance, leave)  │               │  chat-specific tables) │
   └─────────────────────┘               └────────────────────────┘
             │                                     │
             └──────────── same JWT secret ────────┘
```

- Laravel owns `users` and `organizations` — this service only has
  **read-only mappings** of those tables (`app/models/user.py`,
  `app/models/organization.py`). It never writes to them.
- Alembic migrations in this service touch **chat tables only**.
- Both services trust the same JWT, so a user who logs in through Laravel
  is automatically authenticated for chat — no separate login step.

---

## Multi-Tenant Isolation

TimeNest is multi-tenant, and chat respects that strictly:

**Two users can only chat with each other if they share at least one
organization.** There is no global messaging across unrelated tenants,
by design.

---

## Authentication Flow

Every WebSocket connection goes through this verification chain before
being accepted:

1. **Signature + expiry check** — is the JWT valid and not expired?
2. **Guard check** — reject if `guard === "temp"` (temporary tokens, e.g.
   from partial-login/2FA-pending states, cannot open chat connections)
3. **`organization_uuid` null check** — a user with no active organization
   context has nothing to chat in
4. **`token_version` DB match** — the token's version must match what's
   currently stored for the user, which lets the main app invalidate all
   existing sessions instantly (e.g. on logout-everywhere or password change)

Only after all four checks pass does the WebSocket connection get accepted.

---

## Tech Stack

- **FastAPI** — async web framework, WebSocket support
- **SQLAlchemy (async)** + **`asyncmy`** — async MySQL driver
- **Alembic** — migrations, scoped to chat tables only
- **Redis** (`redis-py`) — typing indicators (TTL-based expiry); pub/sub
  reserved for future multi-server deployment
- **Pydantic Settings** — typed, validated configuration from environment
- **Scalar** (`scalar_fastapi`) — API documentation UI

---

## Project Structure

```
app/
├── core/         # config, database engine/session setup
├── models/       # SQLAlchemy models (chat tables + read-only user/org mappings)
├── schemas/      # Pydantic request/response schemas
├── auth/         # JWT verification logic
├── services/     # business logic layer
├── websocket/    # connection manager, WebSocket endpoints
└── api/          # HTTP routes (non-WebSocket, e.g. chat history)
```

---

## Getting Started

```bash
# Clone and enter the service directory
cd chat-service

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Environment setup
cp .env.example .env
# Fill in: DATABASE_URL components, JWT secret (must match Laravel's), Redis URL

# Run database migrations (chat tables only)
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload
```

API docs will be available at `http://localhost:8000/scalar` once the
service is running.

> The `DATABASE_URL` must point to the **same MySQL database** used by the
> Laravel application. The `JWT_SECRET` must be **identical** to Laravel's
> `JWT_SECRET` — otherwise token verification will fail for every request.

---

## Development Notes

- This service does not manage user registration, login, or organization
  creation — that's Laravel's job. This service only consumes identity,
  it doesn't create it.
- Never add write operations to `models/user.py` or `models/organization.py`.
  If a workflow needs to modify user/org data, that belongs in Laravel, not here.
- Redis pub/sub is intentionally deferred until this service needs to run
  on more than one server. Don't add it prematurely.

## License

Proprietary — All rights reserved. Part of the TimeNest platform.
