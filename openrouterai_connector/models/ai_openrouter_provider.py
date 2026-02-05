# -*- coding: utf-8 -*-
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from ..services.openrouter_client import OpenRouterClient

_logger = logging.getLogger(__name__)


class AIOpenRouterProvider(models.Model):
    _name = "ai.openrouter.provider"
    _inherit = "ai.provider"
    _description = "OpenRouter AI Provider"

    name = fields.Char(string="Name", default="OpenRouter", required=True)
    active = fields.Boolean(default=True)
    code = fields.Selection(
        selection_add=[("openrouter", "OpenRouter")],
        string="Provider Code",
        default="openrouter",
        required=True,
    )
    api_key = fields.Char(string="API Key", required=True)
    base_url = fields.Char(string="Base URL", default="https://openrouter.ai/api/v1", required=True)
    app_url = fields.Char(string="App URL")
    app_name = fields.Char(string="App Name")
    default_route = fields.Selection(
        selection=[
            ("auto", "Auto"),
            ("low_cost", "Lowest Cost"),
            ("low_latency", "Lowest Latency"),
        ],
        string="Default Route",
        default="auto",
    )

    def _get_client(self):
        self.ensure_one()
        if not self.api_key:
            raise UserError(_("OpenRouter API key is required"))
        return OpenRouterClient(
            api_key=self.api_key,
            base_url=self.base_url,
            app_url=self.app_url,
            app_name=self.app_name,
        )

    def action_open_sync_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sync OpenRouter Models'),
            'res_model': 'ai.openrouter.sync.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_provider_id': self.id},
        }
