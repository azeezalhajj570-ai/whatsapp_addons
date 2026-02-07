# -*- coding: utf-8 -*-
import json
import logging
from datetime import timedelta

from odoo import api, fields, models

from ..services.openrouter_client import OpenRouterClient

_logger = logging.getLogger(__name__)


class AIOpenRouterRequestLog(models.Model):
    _name = "ai.openrouter.request.log"
    _description = "OpenRouter Request Log"
    _order = "request_ts desc"

    provider_id = fields.Many2one(
        comodel_name="ai.openrouter.provider",
        string="Provider",
        ondelete="set null",
    )
    generation_id = fields.Char(string="Generation ID", index=True)
    model_id = fields.Many2one(
        comodel_name="ai.openrouter.model",
        string="Model",
        ondelete="set null",
    )
    request_ts = fields.Datetime(string="Request Time", default=fields.Datetime.now)
    prompt_tokens = fields.Integer(string="Prompt Tokens")
    completion_tokens = fields.Integer(string="Completion Tokens")
    total_tokens = fields.Integer(string="Total Tokens")
    reasoning_tokens = fields.Integer(string="Reasoning Tokens")
    cached_tokens = fields.Integer(string="Cached Tokens")
    cache_write_tokens = fields.Integer(string="Cache Write Tokens")
    audio_tokens = fields.Integer(string="Audio Tokens")
    total_cost = fields.Float(string="Total Cost", digits=(16, 6))
    upstream_inference_cost = fields.Float(string="Upstream Inference Cost", digits=(16, 6))
    usage_payload = fields.Json(string="Usage Payload")
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

    @api.model
    def cron_reconcile_usage(self, limit=200, hours_back=48):
        """Backfill usage from OpenRouter generation endpoint for incomplete rows."""
        cutoff = fields.Datetime.now() - timedelta(hours=hours_back)
        domain = [
            ("state", "=", "success"),
            ("generation_id", "!=", False),
            ("request_ts", ">=", cutoff),
            "|",
            ("usage_payload", "=", False),
            ("total_tokens", "=", False),
        ]
        rows = self.search(domain, order="request_ts desc", limit=limit)
        if not rows:
            return 0

        reconciled = 0
        for row in rows:
            provider = row.provider_id or self.env["ai.openrouter.provider"].sudo().search(
                [("active", "=", True)], limit=1
            )
            if not provider:
                _logger.warning("OpenRouter reconcile: no active provider for log %s", row.id)
                continue

            try:
                payload = provider._get_client().get_generation(row.generation_id)
            except Exception as exc:
                _logger.warning(
                    "OpenRouter reconcile: generation lookup failed for %s (%s): %s",
                    row.id,
                    row.generation_id,
                    exc,
                )
                continue

            source = payload
            if isinstance(payload, dict) and isinstance(payload.get("data"), dict):
                source = payload["data"]
            usage = OpenRouterClient.extract_usage(source)
            if not usage.get("usage_payload"):
                _logger.info(
                    "OpenRouter reconcile: no usage payload for log %s (generation=%s)",
                    row.id,
                    row.generation_id,
                )
                continue

            row.write({
                "prompt_tokens": usage.get("prompt_tokens"),
                "completion_tokens": usage.get("completion_tokens"),
                "total_tokens": usage.get("total_tokens"),
                "reasoning_tokens": usage.get("reasoning_tokens"),
                "cached_tokens": usage.get("cached_tokens"),
                "cache_write_tokens": usage.get("cache_write_tokens"),
                "audio_tokens": usage.get("audio_tokens"),
                "total_cost": usage.get("cost") or row.total_cost,
                "upstream_inference_cost": usage.get("upstream_inference_cost") or row.upstream_inference_cost,
                "usage_payload": usage.get("usage_payload"),
                "response_payload": row.response_payload or json.dumps(payload, ensure_ascii=False),
            })
            reconciled += 1

        _logger.info(
            "OpenRouter reconcile: checked=%s reconciled=%s window_hours=%s",
            len(rows),
            reconciled,
            hours_back,
        )
        return reconciled
