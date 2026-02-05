# -*- coding: utf-8 -*-
from odoo import fields, models


class AIOpenRouterCompany(models.Model):
    _name = "ai.openrouter.company"
    _description = "OpenRouter Model Provider"
    _order = "name"

    name = fields.Char(string="Name", required=True)
    external_code = fields.Char(string="External Code", index=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "openrouter_company_unique",
            "unique(external_code)",
            "This OpenRouter provider already exists.",
        )
    ]
