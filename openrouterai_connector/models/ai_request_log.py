# -*- coding: utf-8 -*-
from odoo import fields, models


class AIOpenRouterRequestLog(models.Model):
    _name = "ai.openrouter.request.log"
    _description = "OpenRouter Request Log"
    _order = "request_ts desc"

    provider_id = fields.Many2one(
        comodel_name="ai.openrouter.provider",
        string="Provider",
        ondelete="set null",
    )
    model_id = fields.Many2one(
        comodel_name="ai.openrouter.model",
        string="Model",
        ondelete="set null",
    )
    request_ts = fields.Datetime(string="Request Time", default=fields.Datetime.now)
    prompt_tokens = fields.Integer(string="Prompt Tokens")
    completion_tokens = fields.Integer(string="Completion Tokens")
    total_tokens = fields.Integer(string="Total Tokens")
    total_cost = fields.Float(string="Total Cost", digits=(16, 6))
    response_text = fields.Text(string="Response Text")
    request_payload = fields.Text(string="Request Payload")
    response_payload = fields.Text(string="Response Payload")
    state = fields.Selection(
        selection=[
            ("success", "Success"),
            ("error", "Error"),
        ],
        string="State",
        default="success",
    )
