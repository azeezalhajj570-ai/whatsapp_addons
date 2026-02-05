# -*- coding: utf-8 -*-
import json

from odoo import _, fields, models
from odoo.exceptions import UserError


class AIOpenRouterSyncWizard(models.TransientModel):
    _name = "ai.openrouter.sync.wizard"
    _description = "Sync OpenRouter Models"

    provider_id = fields.Many2one(
        comodel_name="ai.openrouter.provider",
        string="Provider",
        required=True,
        ondelete="cascade",
    )
    deactivate_missing = fields.Boolean(string="Deactivate Missing Models", default=True)

    def action_sync(self):
        self.ensure_one()
        provider = self.provider_id
        client = provider._get_client()
        payload = client.list_models()

        models_data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(models_data, list):
            raise UserError(_("Unexpected OpenRouter models response format"))

        OpenRouterModel = self.env["ai.openrouter.model"].sudo()
        OpenRouterCompany = self.env["ai.openrouter.company"].sudo()
        seen_ids = set()

        for item in models_data:
            external_id = item.get("id") or item.get("model")
            if not external_id:
                continue

            pricing = item.get("pricing") or {}
            prompt_price = _safe_float(pricing.get("prompt"))
            completion_price = _safe_float(pricing.get("completion"))
            image_price = _safe_float(pricing.get("image"))
            request_price = _safe_float(pricing.get("request"))

            architecture = item.get("architecture") or {}
            modality = item.get("modality") or architecture.get("modality")
            if isinstance(modality, list):
                modality = ", ".join(modality)
            elif isinstance(modality, dict):
                modality = ", ".join([str(value) for value in modality.values()])

            top_provider = item.get("top_provider") or {}
            provider_name = (
                item.get("provider")
                or item.get("provider_name")
                or top_provider.get("name")
                or item.get("owned_by")
            )
            provider_code = (
                item.get("provider")
                or item.get("provider_name")
                or top_provider.get("id")
                or item.get("owned_by")
            )

            display_name = item.get("name") or ""
            if not provider_name and ":" in display_name:
                provider_name = display_name.split(":", 1)[0].strip()
            if not provider_code and external_id and "/" in external_id:
                provider_code = external_id.split("/", 1)[0].strip()

            company_provider = False
            if provider_name:
                company_provider = OpenRouterCompany.search(
                    [("external_code", "=", provider_code or provider_name)],
                    limit=1,
                )
                if not company_provider:
                    company_provider = OpenRouterCompany.create({
                        "name": provider_name,
                        "external_code": provider_code or provider_name,
                        "active": True,
                    })

            vals = {
                "name": item.get("name") or external_id,
                "external_id": external_id,
                "description": item.get("description"),
                "provider_id": provider.id,
                "company_provider_id": company_provider.id if company_provider else False,
                "context_length": item.get("context_length") or 0,
                "prompt_price": prompt_price,
                "completion_price": completion_price,
                "image_price": image_price,
                "request_price": request_price,
                "provider_name": provider_name,
                "modality": modality,
                "architecture_modality": architecture.get("modality"),
                "architecture_tokenizer": architecture.get("tokenizer"),
                "architecture_instruct_type": architecture.get("instruct_type"),
                "top_provider_context_length": top_provider.get("context_length"),
                "top_provider_max_completion_tokens": top_provider.get("max_completion_tokens"),
                "top_provider_is_moderated": bool(top_provider.get("is_moderated")),
                "per_request_prompt_tokens": (item.get("per_request_limits") or {}).get("prompt_tokens"),
                "per_request_completion_tokens": (item.get("per_request_limits") or {}).get("completion_tokens"),
                "is_free": bool(item.get("is_free")) or (prompt_price == 0 and completion_price == 0),
                "active": True,
                "raw_payload": item,
            }

            existing = OpenRouterModel.search(
                [
                    ("provider_id", "=", provider.id),
                    ("external_id", "=", external_id),
                ],
                limit=1,
            )
            if existing:
                existing.write(vals)
            else:
                OpenRouterModel.create(vals)
            seen_ids.add(external_id)

        if self.deactivate_missing:
            to_deactivate = OpenRouterModel.search([
                ("provider_id", "=", provider.id),
                ("external_id", "not in", list(seen_ids)),
            ])
            if to_deactivate:
                to_deactivate.write({"active": False})

        return {"type": "ir.actions.act_window_close"}


def _safe_float(value):
    try:
        if value is None:
            return 0.0
        return float(value)
    except (TypeError, ValueError):
        return 0.0
