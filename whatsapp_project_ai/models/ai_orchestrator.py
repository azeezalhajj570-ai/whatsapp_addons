import json
import logging
from odoo import models

_logger = logging.getLogger(__name__)


class WhatsAppProjectAIOrchestrator(models.AbstractModel):
    _name = "whatsapp.project.ai.orchestrator"
    _description = "WhatsApp AI Project Orchestrator"

    # -------------------------
    # PUBLIC ENTRY POINT
    # -------------------------

    def process_incoming_message(self, message):
        """Main entry point for AI classification"""
        self.ensure_one()

        if message.is_ai_processed:
            _logger.info("AI: Message %s already processed, skipping", message.id)
            return

        agent = self._get_agent()
        if not agent:
            return

        try:
            ai_data = self._call_ai(agent, message)
            if not ai_data:
                return

            self._apply_ai_result(message, ai_data)

            if message.ai_confidence < 0.60:
                _logger.info(
                    "AI: Low confidence (%.2f) for message %s",
                    message.ai_confidence,
                    message.id,
                )
                return

            _logger.info(
                "AI: Message %s classified successfully (intent=%s)",
                message.id,
                ai_data.get("intent_tag"),
            )

        except Exception as e:
            self._handle_ai_error(message, e)

    # -------------------------
    # AI HELPERS
    # -------------------------

    def _get_agent(self):
        agent = self.env.ref(
            "whatsapp_project_ai.agent_whatsapp_pm", raise_if_not_found=False
        )
        if not agent:
            _logger.warning("AI: Agent whatsapp_pm not found")
        return agent

    def _call_ai(self, agent, message):
        """Build prompt and call AI"""
        prompt = self._build_prompt(message)

        responses = agent.get_direct_response(prompt=prompt)
        if not responses:
            _logger.warning("AI: Empty response")
            return None

        raw = self._extract_json(responses[0])
        return json.loads(raw)

    def _build_prompt(self, message):
        intents = self._available_intents()
        services = self._service_catalog()
        return (
            f"msg:{message.body or ''}\n"
            f"sender:{message.mobile_number or ''}\n"
            f"tags:{json.dumps(intents, separators=(',', ':'))}\n"
            f"services:{json.dumps(services, separators=(',', ':'))}\n"
            "rules: pick exactly one tag from tags; JSON only; keys intent_tag,"
            "confidence,rationale,service_id; confidence 0-1"
        )

    def _extract_json(self, text):
        if "```" in text:
            text = text.split("```")[1]
        return text.strip()

    # -------------------------
    # DATA BUILDERS
    # -------------------------

    def _available_intents(self):
        products = self.env["product.template"].search([
            ("type", "=", "service"),
            ("sale_ok", "=", True),
        ])
        tag_names = sorted({t.name for p in products for t in p.product_tag_ids})
        if tag_names:
            return tag_names
        return [t.name for t in self.env["project.tags"].search([])]

    def _service_catalog(self):
        products = self.env["product.template"].search([
            ("type", "=", "service"),
            ("sale_ok", "=", True),
        ])

        return [
            {
                "id": p.id,
                "name": p.name,
                "tags": [t.name for t in p.product_tag_ids],
            }
            for p in products
        ]

    # -------------------------
    # APPLY RESULTS
    # -------------------------

    def _apply_ai_result(self, message, ai_data):
        tag_ids = []

        intent = ai_data.get("intent_tag")
        if intent:
            tag = self.env["project.tags"].search(
                [("name", "=", intent)], limit=1
            ) or self.env["project.tags"].create({"name": intent})
            tag_ids.append(tag.id)

        message.write({
            "ai_confidence": ai_data.get("confidence", 0.0),
            "ai_rationale": ai_data.get("rationale"),
            "is_ai_processed": True,
            "tag_ids": [(6, 0, tag_ids)],
        })

    # -------------------------
    # ERROR HANDLING
    # -------------------------

    def _handle_ai_error(self, message, error):
        _logger.exception("AI: Error processing message %s", message.id)

        message.write({
            "is_ai_processed": True,
            "ai_rationale": f"AI Error: {error}",
        })

        if any(x in str(error).lower() for x in ("quota", "429", "limit")):
            self._notify_admin(message, error)

    def _notify_admin(self, message, error):
        admin = self.env.ref("base.user_admin", raise_if_not_found=False)
        if not admin:
            return

        message.activity_schedule(
            "mail.mail_activity_data_todo",
            user_id=admin.id,
            summary="AI Quota / Rate Limit Error",
            note=f"Message {message.mobile_number}<br/>{error}",
        )

    # -------------------------
    # EXECUTION ACTIONS
    # -------------------------

    def action_create_lead(self, message, ai_data=None):
        ai_data = ai_data or {}

        crm_tags = self._map_project_tags_to_crm(message.tag_ids)

        return self.env["crm.lead"].create({
            "name": f"WhatsApp Inquiry",
            "partner_id": message.partner_id.id,
            "description": message.body,
            "type": "lead",
            "tag_ids": [(6, 0, crm_tags)],
            "priority": ai_data.get("priority", "1"),
            "expected_revenue": ai_data.get("expected_revenue", 0.0),
        })

    def _map_project_tags_to_crm(self, project_tags):
        crm_tag_ids = []
        for tag in project_tags:
            crm_tag = self.env["crm.tag"].search(
                [("name", "=", tag.name)], limit=1
            ) or self.env["crm.tag"].create({"name": tag.name})
            crm_tag_ids.append(crm_tag.id)
        return crm_tag_ids
