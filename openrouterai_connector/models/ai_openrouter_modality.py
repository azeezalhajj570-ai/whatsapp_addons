# -*- coding: utf-8 -*-
from odoo import fields, models


class AIOpenRouterModality(models.Model):
    _name = "ai.openrouter.modality"
    _description = "OpenRouter Modality"
    _order = "name"

    name = fields.Char(string="Name", required=True, index=True)
    
    _sql_constraints = [
        ("name_uniq", "unique (name)", "Modality name must be unique.")
    ]
