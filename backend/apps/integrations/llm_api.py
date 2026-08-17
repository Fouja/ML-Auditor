"""
LLM Configuration API endpoints
"""

from django.http import JsonResponse
from ninja import Router

from .schemas import LLMConfigurationCreateSchema, LLMConfigurationUpdateSchema

router = Router()


@router.get("/")
def list_llm_configurations(request):
    """List all LLM configurations for current user"""
    from .models import LLMConfiguration

    configs = LLMConfiguration.objects.filter(user=request.auth)
    return [
        {
            "id": str(config.id),
            "provider": config.provider,
            "name": config.name,
            "model_name": config.model_name,
            "is_active": config.is_active,
            "created_at": config.created_at.isoformat(),
        }
        for config in configs
    ]


@router.post("/")
def create_llm_configuration(request, payload: LLMConfigurationCreateSchema):
    """Create or update an LLM configuration"""
    from .models import LLMConfiguration

    try:
        config, created = LLMConfiguration.objects.update_or_create(
            user=request.auth,
            provider=payload.provider,
            model_name=payload.model_name,
            defaults={
                "name": payload.name,
                "api_key": payload.api_key,
                "api_endpoint": payload.api_endpoint or "",
            },
        )
        return {
            "id": str(config.id),
            "provider": config.provider,
            "name": config.name,
            "model_name": config.model_name,
            "is_active": config.is_active,
            "message": "LLM configuration created successfully" if created else "LLM configuration updated successfully",
        }
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


@router.get("/active/")
def get_active_llm(request):
    """Get the currently active LLM configuration"""
    from .models import LLMConfiguration

    config = LLMConfiguration.objects.filter(user=request.auth, is_active=True).first()

    if config:
        return {
            "id": str(config.id),
            "provider": config.provider,
            "name": config.name,
            "model_name": config.model_name,
            "is_active": True,
        }
    else:
        return JsonResponse({"error": "Aucun LLM configuré"}, status=404)


@router.get("/{config_id}/")
def get_llm_configuration(request, config_id: str):
    """Get a specific LLM configuration"""
    from .models import LLMConfiguration

    try:
        config = LLMConfiguration.objects.get(id=config_id, user=request.auth)
        return {
            "id": str(config.id),
            "provider": config.provider,
            "name": config.name,
            "model_name": config.model_name,
            "api_endpoint": config.api_endpoint,
            "is_active": config.is_active,
            "created_at": config.created_at.isoformat(),
        }
    except LLMConfiguration.DoesNotExist:
        return JsonResponse({"error": "Configuration not found"}, status=404)


@router.put("/{config_id}/")
def update_llm_configuration(
    request, config_id: str, payload: LLMConfigurationUpdateSchema
):
    """Update LLM configuration"""
    from .models import LLMConfiguration

    try:
        config = LLMConfiguration.objects.get(id=config_id, user=request.auth)
        if payload.name is not None:
            config.name = payload.name
        if payload.api_key is not None:
            config.api_key = payload.api_key
        if payload.api_endpoint is not None:
            config.api_endpoint = payload.api_endpoint
        config.save()
        return {"message": "Configuration updated successfully"}
    except LLMConfiguration.DoesNotExist:
        return JsonResponse({"error": "Configuration not found"}, status=404)


@router.delete("/{config_id}/")
def delete_llm_configuration(request, config_id: str):
    """Delete LLM configuration"""
    from .models import LLMConfiguration

    try:
        config = LLMConfiguration.objects.get(id=config_id, user=request.auth)
        config.delete()
        return {"message": "Configuration deleted successfully"}
    except LLMConfiguration.DoesNotExist:
        return JsonResponse({"error": "Configuration not found"}, status=404)


_LLM_TEST_TIMEOUT = 30
_LLM_TEST_MESSAGE = "Test"

# Providers whose /chat/completions endpoints are OpenAI-compatible and can be
# tested with the generic helper (keys are also used by the frontend to know
# which providers skip the API-key requirement).
OPENAI_COMPATIBLE_PROVIDERS = {
    "openai",
    "nvidia",
    "huggingface",
    "custom",
    "groq",
    "openrouter",
    "mistral",
    "gemini",
    "deepseek",
    "together",
    "lmstudio",
}

# Local providers — no API key required.
KEYLESS_PROVIDERS = {"ollama", "lmstudio"}


def _friendly_llm_error(exc: Exception, endpoint: str = "") -> str:
    """Turn low-level transport errors into a human-readable message."""
    import requests

    if isinstance(exc, requests.exceptions.ReadTimeout):
        return (
            f"L'API LLM n'a pas répondu dans le délai imparti ({_LLM_TEST_TIMEOUT}s). "
            "Le modèle n'est probablement pas disponible pour cette clé/compte, ou le réseau est lent. "
            "Essayez un autre modèle (par ex. meta/llama-3.1-8b-instruct)."
        )
    if isinstance(exc, requests.exceptions.ConnectTimeout):
        target = endpoint or "l'API"
        return f"Connexion à {target} expirée. Vérifiez l'URL et votre connexion réseau."
    if isinstance(exc, requests.exceptions.ConnectionError):
        target = endpoint or "l'API"
        return f"Impossible de se connecter à {target}. Vérifiez l'URL, le réseau ou un pare-feu."
    if isinstance(exc, requests.exceptions.HTTPError):
        status = getattr(exc.response, "status_code", 0)
        if status in (401, 403):
            return f"Clé API invalide ou refusée ({status}). Vérifiez votre clef API."
        if status in (404, 410):
            return (
                f"Le modèle n'est pas disponible pour cette clé/compte (HTTP {status}). "
                "Essayez un autre modèle de votre compte (par ex. meta/llama-3.1-8b-instruct)."
            )
        return f"Erreur API (HTTP {status})."
    if isinstance(exc, requests.exceptions.RequestException):
        return f"Erreur réseau: {exc}"
    return str(exc) or "Erreur inconnue"


def _test_openai_compatible(config) -> tuple[bool, str, str]:
    """Generic OpenAI-compatible chat completion test (OpenAI, NVIDIA, custom, HuggingFace)."""
    import requests

    endpoint = (config.api_endpoint or "https://integrate.api.nvidia.com/v1").rstrip("/")
    headers = {
        "Authorization": f"Bearer {config.decrypted_api_key}",
        "Content-Type": "application/json",
    }
    if config.provider == "huggingface" and config.api_endpoint:
        headers["Authorization"] = f"Bearer {config.decrypted_api_key}"
    try:
        response = requests.post(
            f"{endpoint}/chat/completions",
            json={
                "model": config.model_name,
                "messages": [{"role": "user", "content": _LLM_TEST_MESSAGE}],
                "max_tokens": 10,
            },
            headers=headers,
            timeout=_LLM_TEST_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        return False, _friendly_llm_error(exc, endpoint), ""
    if response.status_code == 200:
        return True, "✓ Connecté", config.model_name
    try:
        detail = response.json().get("detail") or response.json().get("message") or ""
    except Exception:
        detail = ""
    return (
        False,
        f"Erreur API: HTTP {response.status_code}" + (f" — {detail[:200]}" if detail else ""),
        "",
    )


@router.post("/{config_id}/test/")
def test_llm_configuration(request, config_id: str):
    """Test LLM configuration connection with clear, actionable error messages."""
    from .models import LLMConfiguration

    try:
        config = LLMConfiguration.objects.get(id=config_id, user=request.auth)
    except LLMConfiguration.DoesNotExist:
        return JsonResponse({"error": "Configuration not found"}, status=404)

    api_key = config.decrypted_api_key
    if not api_key and config.provider not in KEYLESS_PROVIDERS:
        return JsonResponse(
            {
                "error": (
                    "Clé API manquante ou illisible. Re-enregistrez la clé de cette "
                    "configuration (le secret stocké n'a pas pu être déchiffré)."
                )
            },
            status=400,
        )

    try:
        if config.provider in OPENAI_COMPATIBLE_PROVIDERS:
            ok, status_text, model = _test_openai_compatible(config)
            return JsonResponse(
                {"status": status_text, "model": model} if ok else {"error": status_text},
                status=200 if ok else 400,
            )

        elif config.provider == "anthropic":
            import requests

            try:
                response = requests.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": config.model_name,
                        "max_tokens": 10,
                        "messages": [{"role": "user", "content": _LLM_TEST_MESSAGE}],
                    },
                    timeout=_LLM_TEST_TIMEOUT,
                )
            except requests.exceptions.RequestException as exc:
                return JsonResponse({"error": _friendly_llm_error(exc, "api.anthropic.com")}, status=400)
            if response.status_code in (200, 201):
                return {"status": "✓ Connecté", "model": config.model_name}
            if response.status_code in (401, 403):
                return JsonResponse({"error": "Clé API Anthropic invalide ou refusée."}, status=400)
            if response.status_code == 404:
                return JsonResponse(
                    {"error": "Le modèle Anthropic n'est pas disponible pour cette clé. Essayez un autre modèle."},
                    status=400,
                )
            return JsonResponse({"error": f"Erreur API Anthropic: HTTP {response.status_code}"}, status=400)

        elif config.provider == "ollama":
            import requests

            endpoint = (config.api_endpoint or "http://localhost:11434").rstrip("/")
            try:
                response = requests.post(
                    f"{endpoint}/api/generate",
                    json={"model": config.model_name, "prompt": _LLM_TEST_MESSAGE, "stream": False},
                    timeout=_LLM_TEST_TIMEOUT,
                )
            except requests.exceptions.RequestException as exc:
                return JsonResponse({"error": _friendly_llm_error(exc, endpoint)}, status=400)
            if response.status_code == 200:
                return {"status": "✓ Connecté", "model": config.model_name}
            try:
                detail = response.json().get("error") or ""
            except Exception:
                detail = ""
            return JsonResponse(
                {
                    "error": (
                        f"Impossible de se connecter à Ollama (HTTP {response.status_code})."
                        + (f" — {detail[:200]}" if detail else "")
                    )
                },
                status=400,
            )

        return {"status": "Test non implémenté pour ce provider"}

    except Exception as e:
        return JsonResponse({"error": _friendly_llm_error(e)}, status=400)


@router.post("/{config_id}/set-active/")
def set_active_llm(request, config_id: str):
    """Set LLM as active (deactivate others)"""
    from .models import LLMConfiguration

    try:
        # Deactivate all other configs
        LLMConfiguration.objects.filter(user=request.auth).update(is_active=False)

        # Activate this one
        config = LLMConfiguration.objects.get(id=config_id, user=request.auth)
        config.is_active = True
        config.save()

        return {"status": "✓ LLM activé", "model": config.model_name}
    except LLMConfiguration.DoesNotExist:
        return JsonResponse({"error": "Configuration not found"}, status=404)
