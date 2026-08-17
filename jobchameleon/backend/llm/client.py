import asyncio
import concurrent.futures
import logging
import os
import threading
import time
from urllib.parse import urlparse
import httpx
import anthropic
import instructor
import openai
from openai import OpenAI
from pydantic import BaseModel
from data.repository import Repository, create_repository
from core.logging import get_logger

_log = get_logger(__name__)

# 180s read / 10s connect — structured extraction on remote APIs (especially
# NVIDIA NIM) can legitimately need > 2 minutes for a large résumé.  Anything
# beyond this is likely hung. (H5)
_TIMEOUT = httpx.Timeout(180.0, connect=10.0)

# Number of retries (after the first attempt) for transient LLM errors. (C2)
_MAX_LLM_RETRIES = 3
_RETRY_BASE_DELAY = 1.0  # seconds; doubles each retry → 1s, 2s, 4s

# H5: a dedicated, bounded thread pool for blocking LLM calls. Using the default
# asyncio executor meant a burst of slow (up to 120s) generations could occupy
# every default worker and starve all other to_thread work (DB reads, file IO).
# Keeping LLM calls on their own pool caps the blast radius at max_workers.
LLM_EXECUTOR = concurrent.futures.ThreadPoolExecutor(max_workers=4, thread_name_prefix="llm")

# Cache constructed SDK clients so each LLM call reuses the underlying httpx
# connection pool / TLS session instead of paying full client + TLS setup every
# call. Keyed by the exact constructor kwargs (via repr, since httpx.Timeout is
# not hashable) so different base_url/key/timeout/max_retries configs get
# distinct clients. OpenAI/Anthropic clients are documented thread-safe, so
# sharing one across the bounded LLM pool is safe.
_CLIENT_CACHE: dict = {}
_CLIENT_CACHE_LOCK = threading.Lock()


def _cached_raw_client(kind: str, factory, **kwargs):
    key = (kind, tuple(sorted((name, repr(val)) for name, val in kwargs.items())))
    client = _CLIENT_CACHE.get(key)
    if client is not None:
        return client
    with _CLIENT_CACHE_LOCK:
        client = _CLIENT_CACHE.get(key)
        if client is None:
            client = factory(**kwargs)
            _CLIENT_CACHE[key] = client
        return client


def _openai(**kwargs) -> OpenAI:
    """Cached raw OpenAI client (shared httpx pool). Wrap with instructor per
    call where structured output is needed — instructor.from_openai does not
    mutate the passed client, so re-wrapping a cached client is safe."""
    return _cached_raw_client("openai", OpenAI, **kwargs)


def _anthropic(**kwargs):
    """Cached raw Anthropic client (shared httpx pool)."""
    return _cached_raw_client("anthropic", anthropic.Anthropic, **kwargs)


def reset_client_cache() -> None:
    """Drop all cached SDK clients (used by tests / after a key change)."""
    with _CLIENT_CACHE_LOCK:
        _CLIENT_CACHE.clear()


# Module-level hook for broadcasting LLM API call events to the UI via WebSocket.
# Set by the application (main.py) at startup; None when running in tests.
_llm_event_callback: object | None = None


def set_llm_event_callback(callback: object) -> None:
    """Register a callable(event_type: str, msg: str, step: str | None) -> None
    that will be invoked for each LLM API call start/success/failure.

    The callable is called synchronously from the LLM thread pool — it must
    not block.
    """
    global _llm_event_callback
    _llm_event_callback = callback


def _broadcast_llm_event(event: str, msg: str, step: str | None = None) -> None:
    cb = _llm_event_callback
    if cb is not None:
        try:
            cb(event, msg, step)
        except Exception:
            pass


async def acall_llm(s: str, u: str, m: type[BaseModel], step: str | None = None):
    """Async wrapper that runs call_llm on the dedicated LLM thread pool (H5)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(LLM_EXECUTOR, call_llm, s, u, m, step)


async def acall_raw(s: str, u: str, step: str | None = None) -> str:
    """Async wrapper that runs call_raw on the dedicated LLM thread pool (H5)."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(LLM_EXECUTOR, call_raw, s, u, step)


def _is_retryable_llm_error(exc: Exception) -> bool:
    """True for transient errors worth retrying (rate limit, connection, 5xx).

    Permanent errors — authentication, invalid request, 4xx other than 429 —
    return False so they propagate immediately rather than wasting retries.

    Also unwraps ``instructor.InstructorRetryException`` (which wraps the
    underlying SDK error after exhausting its own internal retries) so the
    outer retry loop can still retry transient failures.
    """
    if type(exc).__name__ == "InstructorRetryException":
        cause = exc.__cause__ or exc.__context__ or exc
        return _is_retryable_llm_error(cause)
    if isinstance(
        exc,
        (
            openai.RateLimitError,
            openai.APIConnectionError,
            openai.APITimeoutError,
            anthropic.RateLimitError,
            anthropic.APIConnectionError,
            anthropic.APITimeoutError,
        ),
    ):
        return True
    # HTTP 5xx from either SDK (APIStatusError subclasses expose status_code).
    status = getattr(exc, "status_code", None)
    return isinstance(status, int) and 500 <= status < 600


def is_transient_llm_error(exc: Exception) -> bool:
    """Public alias of the transient-error classifier (used by callers that
    need to distinguish retryable LLM failures from permanent ones, e.g. M4)."""
    return _is_retryable_llm_error(exc)


def _retry_llm_call(fn, *, max_retries: int = _MAX_LLM_RETRIES):
    """Run ``fn`` with exponential backoff on transient LLM errors.

    Retries up to ``max_retries`` times with 1s/2s/4s delays. Permanent errors
    are re-raised on the first occurrence.
    """
    delay = _RETRY_BASE_DELAY
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            _log.warning("LLM attempt %d/%d failed: %s %s", attempt + 1, max_retries + 1, type(exc).__name__, exc)
            if attempt >= max_retries or not _is_retryable_llm_error(exc):
                _log.error("LLM giving up after %d attempt(s): %s", attempt + 1, exc)
                raise
            _log.warning(
                "transient LLM error (attempt %d/%d) — retrying in %.0fs: %s",
                attempt + 1,
                max_retries,
                delay,
                exc,
            )
            time.sleep(delay)
            delay *= 2
# STABILITY: thread-safe LLM repository singleton
_repo_lock = threading.RLock()
_repo: Repository = create_repository()


def configure_repository(repo: Repository) -> None:
    global _repo
    with _repo_lock:
        _repo = repo


def get_repository() -> Repository:
    with _repo_lock:
        return _repo


def get_setting(key: str, default: str = "") -> str:
    return get_repository().settings.get_setting(key, default)

# Maps provider id → settings key holding the global API key
_KEY_NAMES: dict[str, str] = {
    "anthropic": "anthropic_key",
    "gemini":    "gemini_api_key",
    "groq":      "groq_api_key",
    "nvidia":    "nvidia_api_key",
    "openai":    "openai_api_key",
    "deepseek":  "deepseek_api_key",
    "xai":       "xai_api_key",
    "kimi":      "kimi_api_key",
    "mistral":   "mistral_api_key",
    "openrouter": "openrouter_api_key",
    "together":  "together_api_key",
    "fireworks": "fireworks_api_key",
    "cerebras":  "cerebras_api_key",
    "perplexity": "perplexity_api_key",
    "huggingface": "huggingface_api_key",
    "cohere": "cohere_api_key",
    "sambanova": "sambanova_api_key",
    "qwen": "qwen_api_key",
    "azure": "azure_openai_api_key",
    "custom":    "custom_api_key",
}

# Maps provider id → environment variable fallback
_ENV_NAMES: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini":    "GEMINI_API_KEY",
    "groq":      "GROQ_API_KEY",
    "nvidia":    "NVIDIA_API_KEY",
    "openai":    "OPENAI_API_KEY",
    "deepseek":  "DEEPSEEK_API_KEY",
    "xai":       "XAI_API_KEY",
    "kimi":      "MOONSHOT_API_KEY",
    "mistral":   "MISTRAL_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "together":  "TOGETHER_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
    "cerebras":  "CEREBRAS_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "huggingface": "HF_TOKEN",
    "cohere": "COHERE_API_KEY",
    "sambanova": "SAMBANOVA_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "azure": "AZURE_OPENAI_API_KEY",
    "custom":    "OPENAI_COMPAT_API_KEY",
}

# Env var fallback for model name per provider
_MODEL_ENV_NAMES: dict[str, str] = {
    "nvidia": "NVIDIA_MODEL",
    "openai": "OPENAI_MODEL",
    "anthropic": "ANTHROPIC_MODEL",
    "deepseek": "DEEPSEEK_MODEL",
    "openrouter": "OPENROUTER_MODEL",
}

# Default model per provider (used when no step/global model is set)
_DEFAULT_MODELS: dict[str, str] = {
    "anthropic": "claude-sonnet-4-6",
    "gemini":    "gemini-2.5-flash",
    "groq":      "llama-3.3-70b-versatile",
    "nvidia":    "z-ai/glm-5.1",
    "openai":    "gpt-4o-mini",
    "deepseek":  "deepseek-chat",
    "xai":       "grok-4",
    "kimi":      "kimi-k2.6",
    "mistral":   "mistral-large-latest",
    "openrouter": "openrouter/auto",
    "together":  "openai/gpt-oss-120b",
    "fireworks": "accounts/fireworks/models/llama-v3p1-70b-instruct",
    "cerebras":  "llama-3.3-70b",
    "perplexity": "sonar",
    "huggingface": "openai/gpt-oss-120b",
    "cohere": "command-a-03-2025",
    "sambanova": "Meta-Llama-3.3-70B-Instruct",
    "qwen": "qwen-plus",
    "azure": "gpt-4o-mini",
    "custom":    "model-id",
    "ollama":    "llama3",
    "claude_cli": "claude-sonnet-4-6",  # uses the user's Claude subscription via the claude CLI (no API key)
    "codex_cli":  "gpt-5.5",             # ChatGPT-account Codex only allows its own default model (gpt-5.5 as of 2026-06); codex falls back to the account default if this is unavailable
    "gemini_cli": "",                    # uses the user's Google account / Gemini plan via the gemini CLI; "" = the CLI's own default model
    "copilot_cli": "",                   # uses the user's GitHub Copilot subscription via the copilot CLI; "" = the CLI's own default model
}

_OPENAI_COMPAT_BASE_URLS: dict[str, str] = {
    "xai": "https://api.x.ai/v1",
    "kimi": "https://api.moonshot.ai/v1",
    "mistral": "https://api.mistral.ai/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "together": "https://api.together.xyz/v1",
    "fireworks": "https://api.fireworks.ai/inference/v1",
    "cerebras": "https://api.cerebras.ai/v1",
    "perplexity": "https://api.perplexity.ai",
    "huggingface": "https://router.huggingface.co/v1",
    "cohere": "https://api.cohere.ai/compatibility/v1",
    "sambanova": "https://api.sambanova.ai/v1",
    "qwen": "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
}

_OPENAI_COMPAT_PROVIDERS = set(_OPENAI_COMPAT_BASE_URLS) | {"azure", "custom"}
_BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1"}

# Providers that authenticate WITHOUT an API key: ollama (local) and the
# subscription CLIs (claude_cli / codex_cli, which use the user's own CLI login).
# Centralized so every "needs a key?" check stays in sync.
# Subscription-CLI providers: shell out to a coding-assistant CLI the user has
# already signed into with their OWN plan (no API key). Add new ones here AND in
# llm/subscription_cli.py (_EXE + complete_text branch + status/login).
SUBSCRIPTION_CLI_PROVIDERS = frozenset({"claude_cli", "codex_cli", "gemini_cli", "copilot_cli"})
KEYLESS_PROVIDERS = frozenset({"ollama"}) | SUBSCRIPTION_CLI_PROVIDERS


def provider_needs_key(provider: str) -> bool:
    """True if the provider requires an API key (i.e. not ollama or a subscription CLI)."""
    return provider not in KEYLESS_PROVIDERS


def _validate_base_url(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid base URL: {url}")
    host = parsed.hostname or ""
    if host.lower() in _BLOCKED_HOSTS:
        raise ValueError(f"Cannot use localhost as LLM base URL: {url}")
    # Resolve hostnames too, not just literal IPs: a name like "localtest.me"
    # resolves to 127.0.0.1 and a bare metadata host would otherwise slip past
    # the literal-IP check below. is_public_host enforces the same
    # no-private/loopback/link-local policy after DNS resolution.
    from core.url_guard import is_public_host

    if not is_public_host(host):
        raise ValueError(f"Cannot use private/loopback/internal host as LLM base URL: {url}")
    return url


def _provider_base_url(provider: str) -> str:
    if provider == "azure":
        base = (
            get_setting("azure_openai_endpoint", "")
            or os.environ.get("AZURE_OPENAI_ENDPOINT", "")
        ).strip().rstrip("/")
        if not base:
            raise ValueError("Azure OpenAI endpoint is required")
        if not base.endswith("/openai/v1"):
            base = f"{base}/openai/v1"
        return _validate_base_url(base)
    if provider == "custom":
        return _validate_base_url(
            get_setting("custom_base_url", "")
            or os.environ.get("OPENAI_COMPAT_BASE_URL", "")
            or "https://api.openai.com/v1"
        )
    return _OPENAI_COMPAT_BASE_URLS[provider]


def _resolve(step: str | None = None) -> tuple[str, str, str]:
    """
    Resolve (provider, api_key, model) for a given pipeline step.

    Priority order:
      1. Step-specific setting  ({step}_provider / {step}_api_key / {step}_model)
      2. Global setting         (llm_provider / provider key / nvidia_model etc.)
      3. Environment variable   (ANTHROPIC_API_KEY etc.)
      4. Hardcoded defaults
    """
    sp = get_setting(f"{step}_provider", "") if step else ""
    sk = get_setting(f"{step}_api_key",  "") if step else ""
    sm = get_setting(f"{step}_model",    "") if step else ""

    p = sp or get_setting("llm_provider", "ollama")

    # API key: step-specific > global setting for this provider > env var
    if sk:
        k = sk
    else:
        k = (get_setting(_KEY_NAMES.get(p, ""), "")
             or os.environ.get(_ENV_NAMES.get(p, ""), "")
             or (os.environ.get("GOOGLE_API_KEY", "") if p == "gemini" else ""))

    # Model: step-specific > provider-level setting > env var > default
    if sm:
        model = sm
    elif p in _DEFAULT_MODELS:
        model = (get_setting(f"{p}_model", "")
                 or os.environ.get(_MODEL_ENV_NAMES.get(p, ""), "")
                 or _DEFAULT_MODELS[p])
    else:
        model = (os.environ.get(_MODEL_ENV_NAMES.get(p, ""), "")
                 or _DEFAULT_MODELS.get(p, "llama3"))

    if step:
        _log.debug("step=%s → provider=%s model=%s", step, p, model)

    return p, k, model


def resolve_config(step: str | None = None) -> tuple[str, str, str]:
    """Public resolver for agents that need provider-specific request shapes."""
    return _resolve(step)


class MissingKeyError(RuntimeError):
    """Raised when the configured provider requires an API key but none is set."""


def assert_llm_configured(step: str | None = None) -> None:
    """Raise MissingKeyError if the resolved provider needs a key and has none.

    Lets callers that must produce real LLM output (e.g. resume generation) fail
    loudly with an actionable message instead of silently emitting an empty
    structured result that downstream code mistakes for success. Keyless
    providers (ollama, claude_cli, codex_cli) always pass.
    """
    provider, key, _model = _resolve(step)
    if provider_needs_key(provider) and not key:
        raise MissingKeyError(
            f"No API key configured for provider {provider!r}. "
            "Add your key in Settings, or switch to a local provider."
        )


def _client_nvidia(k: str):
    return instructor.from_openai(
        _openai(
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=k,
            timeout=_TIMEOUT,
            max_retries=0,
        ),
        mode=instructor.Mode.JSON,
    )


def _client_gemini(k: str):
    return _openai(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=k,
        timeout=_TIMEOUT,
        max_retries=0,
    )


def _client_openai_compat(provider: str, key: str):
    return _openai(
        base_url=_provider_base_url(provider),
        api_key=key,
        timeout=_TIMEOUT,
        max_retries=0,
    )


def call_llm(s: str, u: str, m: type[BaseModel], step: str | None = None):
    """
    Call LLM with structured output.

    Pass `step` (e.g. "evaluator", "scout", "ingestor") to use that step's
    per-step provider/key/model settings. Omit for global defaults.

    Transient errors (rate limit, connection, 5xx) are retried with backoff.
    """
    p, k, model = _resolve(step)
    _log.info("call_llm START step=%s provider=%s model=%s user_len=%d", step, p, model, len(u or ""))
    _broadcast_llm_event("llm_start", f"[{p}] calling {model} (structured, step={step})", step)
    try:
        result = _retry_llm_call(lambda: _call_llm_once(s, u, m, step))
        _broadcast_llm_event("llm_ok", f"[{p}] {model} OK (step={step})", step)
        return result
    except Exception as exc:
        _broadcast_llm_event("llm_fail", f"[{p}] {model} FAILED: {type(exc).__name__} (step={step})", step)
        raise


def _subscription_call(provider, attempt, fallback, *, step):
    """Run a subscription-CLI call, retrying once on a cold-start timeout, then
    falling back gracefully on any other CLI failure (not-installed, login,
    credit, malformed output). The first call after a sign-in/idle period often
    times out while the runtime warms up but succeeds on the retry."""
    from llm import subscription_cli as _sub
    try:
        try:
            return attempt()
        except _sub.CliTimeout:
            _log.warning("%s subscription CLI timed out (step=%s) — retrying once", provider, step)
            return attempt()
    except _sub.CliError as exc:
        _log.warning("%s subscription CLI failed (step=%s): %s", provider, step, exc)
        return fallback()


def _call_llm_once(s: str, u: str, m: type[BaseModel], step: str | None = None):
    p, k, model = _resolve(step)
    key_hint = (k[:6] + "…") if k and len(k) > 6 else repr(k)
    _log.info("_call_llm_once step=%s provider=%s key=%s model=%s sys_len=%d user_len=%d",
              step, p, key_hint, model, len(s or ""), len(u or ""))

    if p == "anthropic":
        if not k:
            _log.warning("anthropic — no key (step=%s) — falling back", step)
            return _parse_fallback(u, m)
        anthropic_client = _anthropic(api_key=k, timeout=180.0, max_retries=0)
        r = anthropic_client.messages.parse(
            model=model,
            max_tokens=4096,
            system=s,
            messages=[{"role": "user", "content": u}],
            output_format=m,
        )
        return r.parsed_output

    elif p == "groq":
        if not k:
            _log.warning("groq — no key (step=%s) — falling back", step)
            return _parse_fallback(u, m)
        groq_client = instructor.from_openai(
            _openai(base_url="https://api.groq.com/openai/v1", api_key=k,
                    timeout=_TIMEOUT, max_retries=0)
        )
        return groq_client.chat.completions.create(
            model=model,
            response_model=m,
            max_retries=1,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )

    elif p == "gemini":
        if not k:
            _log.warning("gemini: no key (step=%s); falling back", step)
            return _parse_fallback(u, m)
        gemini_client = instructor.from_openai(_client_gemini(k), mode=instructor.Mode.JSON)
        return gemini_client.chat.completions.create(
            model=model,
            response_model=m,
            max_retries=1,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )

    elif p == "nvidia":
        if not k:
            _log.warning("nvidia — no key (step=%s) — falling back", step)
            return _parse_fallback(u, m)
        # Use secondary NVIDIA API key for DeepSeek models if available
        nv_key = os.environ.get("NVIDIA_API_KEY_2", "") or k if "deepseek" in model.lower() else k
        nvidia_client = _client_nvidia(nv_key)
        _log.info("nvidia calling model=%s (step=%s) max_retries=1", model, step)
        _broadcast_llm_event("nvidia_call", f"[nvidia] calling {model} (step={step})", step)
        try:
            # chat_template_kwargs (enable_thinking) is NOT supported for Mistral
            # tokenizers on NVIDIA NIM — skip it for non-Nemotron/DeepSeek models.
            _skip_thinking = "mistral" in model.lower() or "mixtral" in model.lower()
            extra = {} if _skip_thinking else {"chat_template_kwargs": {"enable_thinking": False}}
            result = nvidia_client.chat.completions.create(
                model=model,
                response_model=m,
                max_retries=1,
                max_tokens=16384,
                messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
                **({"extra_body": extra} if extra else {}),
            )
            _log.info("nvidia call OK (step=%s)", step)
            _broadcast_llm_event("nvidia_ok", f"[nvidia] {model} OK (step={step})", step)
            return result
        except Exception as exc:
            _log.error("nvidia call FAILED (step=%s): %s %s", step, type(exc).__name__, exc)
            _broadcast_llm_event("nvidia_fail", f"[nvidia] {model} FAILED: {type(exc).__name__} (step={step})", step)
            raise

    elif p == "openai":
        if not k:
            _log.warning("openai — no key (step=%s)", step)
            return _parse_fallback(u, m)
        openai_client = instructor.from_openai(_openai(api_key=k, timeout=_TIMEOUT, max_retries=0))
        return openai_client.chat.completions.create(
            model=model,
            response_model=m,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )

    elif p == "deepseek":
        if not k:
            _log.warning("deepseek — no key (step=%s)", step)
            return _parse_fallback(u, m)
        # deepseek-reasoner does not support tool_choice — use JSON mode instead
        mode = instructor.Mode.JSON if "reasoner" in model else instructor.Mode.TOOLS
        deepseek_client = instructor.from_openai(
            _openai(base_url="https://api.deepseek.com", api_key=k, timeout=_TIMEOUT, max_retries=0),
            mode=mode,
        )
        return deepseek_client.chat.completions.create(
            model=model,
            response_model=m,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )

    elif p in _OPENAI_COMPAT_PROVIDERS:
        if not k:
            _log.warning("%s — no key (step=%s)", p, step)
            return _parse_fallback(u, m)
        if p == "perplexity":
            schema = m.model_json_schema()
            # _call_raw_once (not call_raw) — the outer _retry_llm_call already
            # wraps this call_llm invocation; nesting would multiply retries.
            raw = _call_raw_once(
                s + "\nReturn only valid JSON matching this schema:\n" + str(schema),
                u,
                step=step,
            )
            try:
                return m.model_validate_json(raw)
            except Exception:
                _log.warning("perplexity structured parse failed (step=%s)", step)
                return _parse_fallback(u, m)
        try:
            client = _client_openai_compat(p, k)
        except ValueError as exc:
            _log.warning("%s configuration invalid (step=%s): %s", p, step, exc)
            return _parse_fallback(u, m)
        compat_client = instructor.from_openai(
            client,
            mode=instructor.Mode.JSON,
        )
        return compat_client.chat.completions.create(
            model=model,
            response_model=m,
            max_retries=1,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )

    elif p in SUBSCRIPTION_CLI_PROVIDERS:
        # Subscription providers: shell out to the user's logged-in CLI (Claude /
        # Codex / Gemini / Copilot — no API key). The CLI returns text, so we ask
        # for schema-shaped JSON and parse.
        from llm import subscription_cli as _sub
        return _subscription_call(
            p, lambda: _sub.complete_structured(p, s, u, m, model=model),
            lambda: _parse_fallback(u, m), step=step,
        )

    else:  # ollama / default
        b = get_setting("ollama_url", "http://localhost:11434/v1")
        _log.info("ollama at %s model=%s (step=%s)", b, model, step)
        ollama_client = instructor.from_openai(
            _openai(base_url=b, api_key="ollama", timeout=_TIMEOUT, max_retries=0)
        )
        return ollama_client.chat.completions.create(
            model=model,
            response_model=m,
            max_retries=1,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )


def call_raw(s: str, u: str, step: str | None = None) -> str:
    """
    Call LLM for free-form text output.

    Pass `step` (e.g. "generator") to use that step's per-step settings.

    Transient errors (rate limit, connection, 5xx) are retried with backoff.
    """
    p, k, model = _resolve(step)
    _log.info("call_raw START step=%s provider=%s model=%s user_len=%d", step, p, model, len(u or ""))
    _broadcast_llm_event("llm_start", f"[{p}] calling {model} (raw, step={step})", step)
    try:
        result = _retry_llm_call(lambda: _call_raw_once(s, u, step))
        _broadcast_llm_event("llm_ok", f"[{p}] {model} OK (raw, step={step})", step)
        return result
    except Exception as exc:
        _broadcast_llm_event("llm_fail", f"[{p}] {model} FAILED: {type(exc).__name__} (raw, step={step})", step)
        raise


def _call_raw_once(s: str, u: str, step: str | None = None) -> str:
    p, k, model = _resolve(step)
    key_hint = (k[:6] + "…") if k and len(k) > 6 else repr(k)
    _log.info("_call_raw_once step=%s provider=%s key=%s model=%s user_len=%d",
              step, p, key_hint, model, len(u or ""))

    if p == "anthropic":
        if not k:
            return ""
        anthropic_client = _anthropic(api_key=k, timeout=180.0, max_retries=0)
        anthropic_response = anthropic_client.messages.create(
            model=model,
            max_tokens=4096,
            system=s,
            messages=[{"role": "user", "content": u}],
        )
        return str(getattr(anthropic_response.content[0], "text", "") or "")

    elif p == "groq":
        if not k:
            return ""
        groq_client = _openai(base_url="https://api.groq.com/openai/v1", api_key=k,
                   timeout=_TIMEOUT, max_retries=0)
        groq_response = groq_client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )
        return groq_response.choices[0].message.content or ""

    elif p == "gemini":
        if not k:
            return ""
        gemini_client = _client_gemini(k)
        gemini_response = gemini_client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )
        return gemini_response.choices[0].message.content or ""

    elif p == "nvidia":
        if not k:
            return ""
        # Use secondary NVIDIA API key for DeepSeek models if available
        nv_key = os.environ.get("NVIDIA_API_KEY_2", "") or k if "deepseek" in model.lower() else k
        nvidia_client = _openai(base_url="https://integrate.api.nvidia.com/v1", api_key=nv_key,
                   timeout=_TIMEOUT, max_retries=0)
        _log.info("nvidia raw calling model=%s (step=%s)", model, step)
        _broadcast_llm_event("nvidia_call", f"[nvidia] calling {model} (raw, step={step})", step)
        try:
            _skip_thinking_raw = "mistral" in model.lower() or "mixtral" in model.lower()
            extra_raw = {} if _skip_thinking_raw else {"chat_template_kwargs": {"enable_thinking": False}}
            nvidia_response = nvidia_client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
                max_tokens=16384,
                **({"extra_body": extra_raw} if extra_raw else {}),
            )
            _log.info("nvidia raw call OK (step=%s)", step)
            _broadcast_llm_event("nvidia_ok", f"[nvidia] {model} OK (raw, step={step})", step)
            return nvidia_response.choices[0].message.content or ""
        except Exception as exc:
            _log.error("nvidia raw call FAILED (step=%s): %s %s", step, type(exc).__name__, exc)
            _broadcast_llm_event("nvidia_fail", f"[nvidia] {model} FAILED: {type(exc).__name__} (raw, step={step})", step)
            raise

    elif p == "openai":
        if not k:
            return ""
        openai_client = _openai(api_key=k, timeout=_TIMEOUT, max_retries=0)
        openai_response = openai_client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )
        return openai_response.choices[0].message.content or ""

    elif p == "deepseek":
        if not k:
            return ""
        deepseek_client = _openai(base_url="https://api.deepseek.com", api_key=k, timeout=_TIMEOUT, max_retries=0)
        deepseek_response = deepseek_client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )
        return deepseek_response.choices[0].message.content or ""

    elif p in _OPENAI_COMPAT_PROVIDERS:
        if not k:
            return ""
        try:
            compat_raw_client = _client_openai_compat(p, k)
        except ValueError as exc:
            _log.warning("%s configuration invalid (step=%s): %s", p, step, exc)
            return ""
        # Perplexity included: it serves only the OpenAI-compatible
        # chat-completions API (no Responses API).
        compat_chat_response = compat_raw_client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )
        return compat_chat_response.choices[0].message.content or ""

    elif p in SUBSCRIPTION_CLI_PROVIDERS:
        from llm import subscription_cli as _sub
        return _subscription_call(
            p, lambda: _sub.complete_text(p, s, u, model=model), lambda: "", step=step,
        )

    else:  # ollama
        b = get_setting("ollama_url", "http://localhost:11434/v1")
        ollama_client = _openai(base_url=b, api_key="ollama", timeout=_TIMEOUT, max_retries=0)
        ollama_response = ollama_client.chat.completions.create(
            model=model,
            messages=[{"role": "system", "content": s}, {"role": "user", "content": u}],
        )
        return ollama_response.choices[0].message.content or ""


def _parse_fallback(u: str, m: type[BaseModel]):
    """Minimal local fallback — no LLM, returns an empty but VALID model.

    The instance MUST be valid: callers access attributes on it (e.g. the
    ingestor reads ``.n``), and a bare ``model_construct()`` omits required
    fields, which then raises ``AttributeError`` downstream. So when the model
    has required fields with no default, populate them with type-appropriate
    empties instead of leaving them unset.
    """
    try:
        return m()
    except Exception:
        pass
    empties: dict = {str: "", int: 0, float: 0.0, bool: False, list: [], dict: {}, tuple: ()}
    try:
        kwargs = {}
        for field_name, field_info in m.model_fields.items():
            if field_info.is_required():
                annotation = field_info.annotation
                origin = getattr(annotation, "__origin__", None) or annotation
                kwargs[field_name] = empties.get(origin, "")
        return m(**kwargs)
    except Exception as log_exc:
        logging.getLogger(__name__).warning('suppressed exception in backend/llm/client.py:_parse_fallback: %s', log_exc)
        return m.model_construct()
