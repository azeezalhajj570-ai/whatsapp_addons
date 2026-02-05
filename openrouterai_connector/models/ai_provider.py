# -*- coding: utf-8 -*-
from odoo import fields, models


class AIProvider(models.Model):
    _inherit = "ai.provider"

    code = fields.Selection(selection_add=[("openrouter", "OpenRouter")])
