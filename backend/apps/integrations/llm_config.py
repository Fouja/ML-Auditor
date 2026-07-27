"""
Models for LLM Configuration - supports multiple LLM providers
"""

import uuid
from django.db import models
from django.conf import settings


class LLMConfiguration(models.Model):
    """Configuration des LLMs disponibles pour chaque utilisateur"""
    
    LLM_PROVIDERS = [
        ('openai', 'OpenAI (GPT-4, etc.)'),
        ('anthropic', 'Anthropic (Claude)'),
        ('nvidia', 'NVIDIA NIM'),
        ('ollama', 'Ollama (Local)'),
        ('huggingface', 'Hugging Face'),
        ('custom', 'Custom API'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='llm_configs'
    )
    provider = models.CharField(max_length=50, choices=LLM_PROVIDERS)
    name = models.CharField(max_length=255)  # Ex: "GPT-4 Turbo", "Claude 3"
    api_key = models.CharField(max_length=500)  # Chiffré en production
    api_endpoint = models.URLField(blank=True, null=True)  # Pour custom
    model_name = models.CharField(max_length=255)  # Ex: "gpt-4", "claude-3-opus"
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ('user', 'provider', 'model_name')
    
    def __str__(self):
        return f"{self.user.email} - {self.name}"
