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
    """Create a new LLM configuration"""
    from .models import LLMConfiguration

    try:
        config = LLMConfiguration.objects.create(
            user=request.auth,
            provider=payload.provider,
            name=payload.name,
            api_key=payload.api_key,
            api_endpoint=payload.api_endpoint or "",
            model_name=payload.model_name,
        )
        return {
            "id": str(config.id),
            "provider": config.provider,
            "name": config.name,
            "model_name": config.model_name,
            "is_active": config.is_active,
            "message": "LLM configuration created successfully",
        }
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


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


@router.post("/{config_id}/test/")
def test_llm_configuration(request, config_id: str):
    """Test LLM configuration connection"""
    from .models import LLMConfiguration

    try:
        config = LLMConfiguration.objects.get(id=config_id, user=request.auth)

        if config.provider == "openai":
            import openai

            openai.api_key = config.api_key
            response = openai.ChatCompletion.create(
                model=config.model_name,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=10,
            )
            return {"status": "✓ Connecté", "model": config.model_name}

        elif config.provider == "nvidia":
            import requests

            headers = {"Authorization": f"Bearer {config.api_key}"}
            endpoint = config.api_endpoint or "https://integrate.api.nvidia.com/v1"
            response = requests.post(
                f"{endpoint}/chat/completions",
                json={
                    "model": config.model_name,
                    "messages": [{"role": "user", "content": "Test"}],
                    "max_tokens": 10,
                },
                headers=headers,
                timeout=10,
            )
            if response.status_code == 200:
                return {"status": "✓ Connecté", "model": config.model_name}
            else:
                return JsonResponse(
                    {"error": f"Erreur API: {response.status_code}"}, status=400
                )

        elif config.provider == "anthropic":
            import anthropic

            client = anthropic.Anthropic(api_key=config.api_key)
            response = client.messages.create(
                model=config.model_name,
                max_tokens=10,
                messages=[{"role": "user", "content": "Test"}],
            )
            return {"status": "✓ Connecté", "model": config.model_name}

        elif config.provider == "ollama":
            import requests

            endpoint = config.api_endpoint or "http://localhost:11434"
            response = requests.post(
                f"{endpoint}/api/generate",
                json={"model": config.model_name, "prompt": "Test", "stream": False},
                timeout=10,
            )
            if response.status_code == 200:
                return {"status": "✓ Connecté", "model": config.model_name}
            else:
                return JsonResponse(
                    {"error": "Impossible de se connecter à Ollama"}, status=400
                )

        else:
            return {"status": "Test non implémenté pour ce provider"}

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)


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
