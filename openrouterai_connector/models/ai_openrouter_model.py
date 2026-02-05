# -*- coding: utf-8 -*-
from odoo import fields, models


class AIOpenRouterModel(models.Model):
    _name = "ai.openrouter.model"
    _description = "OpenRouter Model"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    external_id = fields.Char(string="External ID", required=True, index=True)
    provider_id = fields.Many2one(
        comodel_name="ai.openrouter.provider",
        string="Provider",
        required=True,
        ondelete="cascade",
    )
    context_length = fields.Integer(string="Context Length")
    prompt_price = fields.Float(string="Prompt Price", digits=(16, 6))
    completion_price = fields.Float(string="Completion Price", digits=(16, 6))
    provider_name = fields.Char(string="Provider Name")
    modality = fields.Char(string="Modality")
    is_free = fields.Boolean(string="Free")
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "openrouter_model_unique",
            "unique(provider_id, external_id)",
            "This OpenRouter model already exists for this provider.",
        )
    ]
