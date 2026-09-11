"""Single-user password authentication.

CLAUDE.md originally resolved network access as "Tailscale-only, no public
hosting, no password layer" — the tailnet was the perimeter, so the app
needed no auth of its own. That premise no longer holds: the app is now
reachable from a locked-down school laptop that cannot join a tailnet, so
it is publicly hosted and the perimeter has to move into the application.

The threat being defended against is specific and worth naming, because it
shapes how much machinery is justified: an unauthenticated public URL lets
any passer-by trigger `force_refresh` on 74 topics, each one a metered
Anthropic call billed to the owner's key. This is a cost-control and
privacy boundary for one known user — not a multi-tenant identity system.
Hence one password, one session cookie, and no user table.

Everything here is standard library except the session cookie signing,
which is Starlette's own SessionMiddleware (itsdangerous).
"""

import base64
import hashlib
import hmac
import logging
import os
import secrets
import time
from collections import defaultdict, deque

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from starlette.types import ASGIApp, Receive, Scope, Send

logger = logging.getLogger("mathsai")

SESSION_KEY = "authenticated"
SESSION_COOKIE = "mathsai_session"
SESSION_MAX_AGE = 30 * 24 * 60 * 60  # 30 days — a teacher should not re-auth daily

# scrypt parameters. 128 * N * r = 16MB of working memory, comfortably under
# OpenSSL's default 32MB maxmem, so no maxmem override is needed.
_SCRYPT_N = 2**14
_SCRYPT_R = 8
_SCRYPT_P = 1
_DKLEN = 32
_SALT_BYTES = 16

MIN_PASSWORD_LENGTH = 12

# The only paths served without a session. `/api/health` must stay open for
# the hosting platform's health probe — it leaks nothing but liveness.
PUBLIC_PATHS = frozenset({"/login", "/api/auth/login", "/api/health"})

# Login attempt throttling. Deliberately in-memory: this is one user on one
# container, so a shared store (Redis) would be more operational surface
# than the problem warrants. The honest trade-off is that the window resets
# on restart and does not span processes — documented in README rather than
# papered over.
MAX_ATTEMPTS = 10
ATTEMPT_WINDOW_SECONDS = 15 * 60
_attempts: dict[str, deque] = defaultdict(deque)


# --------------------------------------------------------------------------
# Password hashing
# --------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """Encode a password as `scrypt$N$r$p$<b64 salt>$<b64 hash>`.

    The parameters travel with the hash so they can be raised later without
    invalidating existing values.
    """
    salt = secrets.token_bytes(_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_DKLEN,
    )
    return "$".join(
        [
            "scrypt",
            str(_SCRYPT_N),
            str(_SCRYPT_R),
            str(_SCRYPT_P),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(derived).decode("ascii"),
        ]
    )


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time check of `password` against an encoded scrypt hash.

    Returns False rather than raising on a malformed hash — a corrupted or
    truncated APP_PASSWORD_HASH should deny access, never 500.
    """
    try:
        scheme, n, r, p, b64_salt, b64_hash = encoded.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(b64_salt), base64.b64decode(b64_hash)
        salt, stored = expected
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(stored),
        )
    except (ValueError, TypeError, MemoryError):
        return False
    return hmac.compare_digest(derived, stored)


# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

def is_production() -> bool:
    return os.getenv("ENVIRONMENT", "development").strip().lower() == "production"


def auth_enabled() -> bool:
    """Auth is active whenever a password hash is configured.

    Locally that means an unset APP_PASSWORD_HASH leaves the app open, which
    keeps the existing dev loop unchanged. That fail-open default is only
    safe because `check_auth_config()` makes it impossible in production.
    """
    return bool(os.getenv("APP_PASSWORD_HASH", "").strip())


def check_auth_config() -> None:
    """Refuse to start a production deployment that is missing auth config.

    This is the guard against the one mistake that actually matters here:
    shipping to a public URL with authentication silently switched off. A
    hard boot failure is noisy and immediate; a wide-open deployment is
    neither, and you would find out from the Anthropic bill.
    """
    if not is_production():
        return
    missing = [
        name
        for name in ("APP_PASSWORD_HASH", "SECRET_KEY")
        if not os.getenv(name, "").strip()
    ]
    if missing:
        raise RuntimeError(
            "ENVIRONMENT=production requires "
            + " and ".join(missing)
            + " to be set, otherwise the app would be publicly readable and "
            "anyone could spend Anthropic credits via the regenerate routes. "
            "Generate a hash with `python generate_password_hash.py`."
        )


def session_secret() -> str:
    """Cookie signing key.

    In production `check_auth_config()` has already proven SECRET_KEY is set.
    Locally an ephemeral key is generated, which simply means sessions do not
    survive a dev-server restart.
    """
    return os.getenv("SECRET_KEY", "").strip() or secrets.token_urlsafe(32)


# --------------------------------------------------------------------------
# Login throttling
# --------------------------------------------------------------------------

def _client_ip(request: Request) -> str:
    """Best-effort client IP for rate-limit bucketing.

    X-Forwarded-For is spoofable, but it is only used to choose a counter
    bucket. Forging it lets an attacker spread their own attempts across
    buckets — exactly what they could do from multiple source addresses
    anyway — so trusting it here costs nothing that was not already free.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _is_rate_limited(ip: str) -> bool:
    now = time.monotonic()
    window = _attempts[ip]
    while window and now - window[0] > ATTEMPT_WINDOW_SECONDS:
        window.popleft()
    return len(window) >= MAX_ATTEMPTS


def _record_failure(ip: str) -> None:
    _attempts[ip].append(time.monotonic())


def reset_rate_limits() -> None:
    """Clear all attempt counters. Used by tests; never called in normal flow."""
    _attempts.clear()


# --------------------------------------------------------------------------
# Middleware
# --------------------------------------------------------------------------

class AuthMiddleware:
    """Gates every path except `PUBLIC_PATHS` behind a valid session.

    Written as raw ASGI rather than BaseHTTPMiddleware so it stays out of the
    response body path entirely — BaseHTTPMiddleware wraps responses in a
    way that interferes with streaming, and `/api/export/.../pdf` returns
    binary payloads this has no business touching.

    Note that `/assets/*` is deliberately *not* public: an unauthenticated
    visitor cannot even download the React bundle, only the login page.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not auth_enabled():
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        session = scope.get("session") or {}
        if path in PUBLIC_PATHS or session.get(SESSION_KEY):
            await self.app(scope, receive, send)
            return

        # An API caller wants a status code it can branch on; a browser
        # navigating to a page wants to land somewhere useful.
        if path.startswith("/api/"):
            response = JSONResponse({"detail": "Not authenticated"}, status_code=401)
        else:
            response = RedirectResponse("/login", status_code=303)
        await response(scope, receive, send)


# --------------------------------------------------------------------------
# Routes
# --------------------------------------------------------------------------

class LoginRequest(BaseModel):
    password: str


router = APIRouter(prefix="/api/auth", tags=["auth"])
page_router = APIRouter(include_in_schema=False)


@router.post("/login")
def login(payload: LoginRequest, request: Request):
    ip = _client_ip(request)

    if _is_rate_limited(ip):
        logger.warning("login blocked by rate limit ip=%s", ip)
        return JSONResponse(
            {"detail": "Too many attempts. Wait 15 minutes and try again."},
            status_code=429,
        )

    stored = os.getenv("APP_PASSWORD_HASH", "").strip()
    if not stored or not verify_password(payload.password, stored):
        _record_failure(ip)
        logger.warning("failed login attempt ip=%s", ip)
        return JSONResponse({"detail": "Incorrect password."}, status_code=401)

    _attempts.pop(ip, None)
    request.session[SESSION_KEY] = True
    logger.info("successful login ip=%s", ip)
    return {"status": "ok"}


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return {"status": "logged out"}


@page_router.get("/login", response_class=HTMLResponse)
def login_page() -> HTMLResponse:
    return HTMLResponse(_LOGIN_PAGE)


# Self-contained HTML rather than a React route, which is the point: the SPA
# bundle sits behind the auth gate, so it is never served to an
# unauthenticated visitor. Styling mirrors the Tailwind theme tokens by hand
# (CLAUDE.md — Aesthetic and UI Requirements) since Tailwind is not available
# outside the bundle. No server-side interpolation happens here, so there is
# no injection surface — errors arrive as JSON and are rendered by script.
_LOGIN_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MathsAI — Sign in</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Syne:wght@700&display=swap" rel="stylesheet">
<style>
  :root {
    --background: #0d0d14;
    --surface: #13131e;
    --border: rgba(255, 255, 255, 0.07);
    --accent: #00d4b8;
    --text-primary: #e8e8f0;
    --text-secondary: #7070a0;
    --danger: #f87171;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.5rem;
    background: var(--background);
    color: var(--text-primary);
    font-family: "DM Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  main {
    width: 100%;
    max-width: 22rem;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 0.75rem;
    padding: 2rem;
  }
  h1 {
    font-family: "Syne", system-ui, sans-serif;
    font-weight: 700;
    font-size: 1.5rem;
    margin: 0 0 0.5rem;
  }
  p.lede { margin: 0 0 1.5rem; color: var(--text-secondary); font-size: 0.875rem; }
  label { display: block; font-size: 0.75rem; letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-secondary); margin-bottom: 0.5rem; }
  input {
    width: 100%;
    padding: 0.625rem 0.75rem;
    border-radius: 0.5rem;
    border: 1px solid var(--border);
    background: var(--background);
    color: var(--text-primary);
    font: inherit;
  }
  input:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
  button {
    width: 100%;
    margin-top: 1rem;
    padding: 0.625rem 0.75rem;
    border: 0;
    border-radius: 0.5rem;
    background: var(--accent);
    color: var(--background);
    font: inherit;
    font-weight: 500;
    cursor: pointer;
  }
  button:disabled { opacity: 0.6; cursor: progress; }
  button:hover:not(:disabled) { filter: brightness(1.08); }
  p.error { margin: 1rem 0 0; min-height: 1.25rem; color: var(--danger); font-size: 0.8125rem; }
</style>
</head>
<body>
  <main>
    <h1>MathsAI</h1>
    <p class="lede">Enter the password to continue.</p>
    <form id="login-form">
      <label for="password">Password</label>
      <input id="password" name="password" type="password" autocomplete="current-password" autofocus required>
      <button id="submit" type="submit">Sign in</button>
    </form>
    <p class="error" id="error" role="alert" aria-live="polite"></p>
  </main>
<script>
  var form = document.getElementById("login-form");
  var input = document.getElementById("password");
  var button = document.getElementById("submit");
  var error = document.getElementById("error");

  form.addEventListener("submit", function (event) {
    event.preventDefault();
    error.textContent = "";
    button.disabled = true;

    fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: input.value })
    })
      .then(function (response) {
        if (response.ok) {
          window.location.replace("/");
          return null;
        }
        return response.json().catch(function () { return {}; });
      })
      .then(function (data) {
        if (!data) return;
        error.textContent = data.detail || "Sign in failed.";
        button.disabled = false;
        input.select();
      })
      .catch(function () {
        error.textContent = "Network error. Check your connection and try again.";
        button.disabled = false;
      });
  });
</script>
</body>
</html>
"""
