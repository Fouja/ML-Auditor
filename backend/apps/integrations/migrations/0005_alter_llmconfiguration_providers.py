from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("integrations", "0004_encrypt_llmconfiguration_api_key"),
    ]

    operations = [
        migrations.AlterField(
            model_name="llmconfiguration",
            name="provider",
            field=models.CharField(
                choices=[
                    ("openai", "OpenAI (GPT-4, etc.)"),
                    ("anthropic", "Anthropic (Claude)"),
                    ("nvidia", "NVIDIA NIM"),
                    ("ollama", "Ollama (Local)"),
                    ("huggingface", "Hugging Face"),
                    ("groq", "Groq (Free)"),
                    ("openrouter", "OpenRouter (Free models)"),
                    ("mistral", "Mistral AI"),
                    ("gemini", "Google Gemini (Free)"),
                    ("deepseek", "DeepSeek"),
                    ("together", "Together AI"),
                    ("lmstudio", "LM Studio (Local)"),
                    ("custom", "Custom API"),
                ],
                max_length=50,
            ),
        ),
    ]
