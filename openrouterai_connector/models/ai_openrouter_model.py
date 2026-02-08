# -*- coding: utf-8 -*-
from odoo import fields, models


class AIOpenRouterModel(models.Model):
    _name = "ai.openrouter.model"
    _description = "OpenRouter Model"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    external_id = fields.Char(string="External ID", required=True, index=True)
    description = fields.Text(string="Description")
    provider_id = fields.Many2one(
        comodel_name="ai.openrouter.provider",
        string="Provider",
        required=True,
        ondelete="cascade",
    )
    company_provider_id = fields.Many2one(
        comodel_name="ai.openrouter.company",
        string="Company Provider",
        ondelete="set null",
    )
    context_length = fields.Integer(string="Context Length")
    prompt_price = fields.Float(string="Prompt Price", digits=(16, 6))
    completion_price = fields.Float(string="Completion Price", digits=(16, 6))
    image_price = fields.Float(string="Image Price", digits=(16, 6))
    request_price = fields.Float(string="Request Price", digits=(16, 6))
    provider_name = fields.Char(string="Provider Name")
    modality = fields.Char(string="Modality")
    input_modality_ids = fields.Many2many(
        "ai.openrouter.modality",
        "ai_openrouter_model_input_modality_rel",
        "model_id", "modality_id",
        string="Input Modalities",
    )
    output_modality_ids = fields.Many2many(
        "ai.openrouter.modality",
        "ai_openrouter_model_output_modality_rel",
        "model_id", "modality_id",
        string="Output Modalities",
    )
    architecture_modality = fields.Char(string="Architecture Modality")
    architecture_tokenizer = fields.Char(string="Architecture Tokenizer")
    architecture_instruct_type = fields.Char(string="Architecture Instruct Type")
    top_provider_context_length = fields.Integer(string="Top Provider Context Length")
    top_provider_max_completion_tokens = fields.Integer(string="Top Provider Max Completion Tokens")
    top_provider_is_moderated = fields.Boolean(string="Top Provider Moderated")
    per_request_prompt_tokens = fields.Char(string="Per-Request Prompt Tokens")
    per_request_completion_tokens = fields.Char(string="Per-Request Completion Tokens")
    is_free = fields.Boolean(string="Free")
    active = fields.Boolean(default=True)
    raw_payload = fields.Json(string="Raw Payload")

    _sql_constraints = [
        (
            "openrouter_model_unique",
            "unique(provider_id, external_id)",
            "This OpenRouter model already exists for this provider.",
        )
    ]

    def action_open_chat(self):
        self.ensure_one()
        provider = self.env["ai.provider"].search([("code", "=", "openrouter")], limit=1)
        if not provider:
            provider = self.env["ai.provider"].create({
                "name": "OpenRouter",
                "code": "openrouter",
            })

        ai_model = self.env["ai.model"].search([
            ("provider_id", "=", provider.id),
            ("technical_name", "=", self.external_id),
        ], limit=1)
        if not ai_model:
            ai_model = self.env["ai.model"].create({
                "name": self.name,
                "provider_id": provider.id,
                "technical_name": self.external_id,
            })

        agent = self.env["ai.agent"].search([
            ("llm_model_id", "=", ai_model.id),
        ], limit=1)
        if not agent:
            agent = self.env["ai.agent"].create({
                "name": f"OpenRouter: {self.name}",
                "llm_model_id": ai_model.id,
                "subtitle": "OpenRouter Chat",
            })
            if agent.partner_id:
                agent.partner_id.write({"name": f"OpenRouter: {self.name}"})

        return agent.open_agent_chat()
