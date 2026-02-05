# -*- coding: utf-8 -*-
"""Patch ai.utils.llm_providers to add OpenRouter provider entries."""
from odoo.addons.ai.utils import llm_providers


Provider = llm_providers.Provider
_original_get_provider = llm_providers.get_provider


if not any(p.name == "openrouter" for p in llm_providers.PROVIDERS):
    llm_providers.PROVIDERS.append(
        Provider(
            "openrouter",
            "OpenRouter",
            "text-embedding-3-small",
            [],
        )
    )

llm_providers.EMBEDDING_MODELS_SELECTION[:] = [
    (provider.embedding_model, provider.display_name)
    for provider in llm_providers.PROVIDERS
]


def _get_provider(env, llm_model):
    try:
        return _original_get_provider(env, llm_model)
    except Exception:
        if env and env["ai.openrouter.model"].sudo().search_count([("external_id", "=", llm_model)], limit=1):
            return "openrouter"
        raise


llm_providers.get_provider = _get_provider
