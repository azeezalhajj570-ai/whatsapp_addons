import json
import logging
from datetime import timedelta
from odoo import fields, models

_logger = logging.getLogger(__name__)


class WhatsAppProjectAIOrchestrator(models.AbstractModel):
    _name = "whatsapp.project.ai.orchestrator"
    _description = "WhatsApp AI Project Orchestrator"

    # -------------------------
    # PUBLIC ENTRY POINT
    # -------------------------

    def process_incoming_message(self, message):
        """Main entry point for AI classification"""
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

        raw = self._extract_json(responses[0]).strip()
        if not raw:
            _logger.warning("AI: Blank JSON response")
            return None

        try:
            return json.loads(raw)
        except Exception:
            _logger.exception("AI: Invalid JSON response: %s", raw[:500])
            return None

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
        cleaned = (text or "").strip()
        if "```" in cleaned:
            parts = cleaned.split("```")
            if len(parts) >= 2:
                cleaned = parts[1].strip()

        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:].strip()

        if cleaned.startswith("{") or cleaned.startswith("["):
            return cleaned

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return cleaned[start:end + 1].strip()

        return cleaned

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

        intent = (
            ai_data.get("intent_tag")
            or ai_data.get("project_tag")
            or ai_data.get("tag")
            or ai_data.get("intent")
        )
        if not intent:
            _logger.warning(
                "AI: No intent tag returned for message %s (keys=%s)",
                message.id,
                ", ".join(sorted(ai_data.keys())),
            )
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

    def action_create_project(self, message, product=None, ai_data=None):
        ai_data = ai_data or {}
        partner = message.partner_id or self._find_partner_from_message(message)
        project_vals = {
            "name": ai_data.get("rationale") or f"Project for {partner.name if partner else 'Customer'}",
            "partner_id": partner.id if partner else False,
            "description": message.body,
        }
        
        if product:
            project_vals["name"] = product.name
            # If product has a project template, we could use it here, 
            # but for now we just create a basic project
        
        project = self.env["project.project"].create(project_vals)
        
        # Post message to project
        project.message_post(
            body=f"Created from WhatsApp Message: {message.body}",
            partner_ids=[partner.id] if partner else []
        )
        
        # Link back
        message.write({
            "linked_model": "project.project",
            "linked_res_id": project.id,
        })

        self.env["project.task"]._ai_ensure_project_task_stages(
            project,
            stage_names=ai_data.get("stage_names"),
        )
        
        return project

    def action_create_task(self, message, product=None, ai_data=None):
        ai_data = ai_data or {}
        partner = message.partner_id or self._find_partner_from_message(message)
        # Find a relevant project
        domain = [("partner_id", "=", partner.id)] if partner else []
        if product:
             # Try to find a project related to this service/product if possible
             pass
             
        project = self.env["project.project"].search(domain, limit=1, order="write_date desc")
        
        if not project:
            # Fallback: create a new project if none exists
            project = self.action_create_project(message, product, ai_data)

        stages = self.env["project.task"]._ai_ensure_project_task_stages(
            project,
            stage_names=ai_data.get("stage_names"),
        )
        deadline_days = int(ai_data.get("deadline_days") or 3)

        task = self.env["project.task"].create({
            "name": ai_data.get("rationale") or f"Task from {partner.name if partner else 'Customer'}",
            "project_id": project.id,
            "partner_id": partner.id if partner else False,
            "stage_id": stages[:1].id if stages else False,
            "description": message.body,
            "date_deadline": fields.Date.today() + timedelta(days=deadline_days),
        })
        
        # Link back
        message.write({
            "linked_model": "project.task",
            "linked_res_id": task.id,
        })
        
        return task

    def _find_partner_from_message(self, message):
        if not message.mobile_number:
            return False
        return self.env["res.partner"].search([
            "|", ("mobile", "=", message.mobile_number), ("phone", "=", message.mobile_number)
        ], limit=1)

    def action_follow_up_project(self, message):
        partner = message.partner_id or self._find_partner_from_message(message)
        domain = []
        if partner:
            domain = [("partner_id", "=", partner.id)]

        # Find latest projects for this contact; fall back to latest global records if no partner is linked.
        projects = self.env["project.project"].search(domain, limit=5, order="write_date desc")
        
        if not projects:
            msg_body = "I couldn't find any active projects under your name."
            if message.wa_account_id:
                self.action_reply_to_user(message, msg_body)
            return msg_body

        summary_lines = ["Here is the status of your projects:"]
        for p in projects:
            open_task_count = self.env["project.task"].search_count([
                ("project_id", "=", p.id),
                ("is_closed", "=", False)
            ])
            latest_tasks = self.env["project.task"].search([("project_id", "=", p.id)], limit=3, order="write_date desc")
            if latest_tasks:
                latest_summary = ", ".join(
                    f"{t.name} ({t.stage_id.name if t.stage_id else 'In Progress'})"
                    for t in latest_tasks
                )
            else:
                latest_summary = "No tasks yet"
            summary_lines.append(f"- {p.name}: {open_task_count} open tasks. Latest: {latest_summary}.")

        msg_body = "\n".join(summary_lines)
        if message.wa_account_id:
            self.action_reply_to_user(message, msg_body)
        return msg_body

    def action_follow_up_task(self, message):
        partner = message.partner_id or self._find_partner_from_message(message)
        if not partner:
            msg_body = "I couldn't find tasks without a linked contact. Please share the task name."
            if message.wa_account_id:
                self.action_reply_to_user(message, msg_body)
            return msg_body

        tasks = self.env["project.task"].search([
            ("partner_id", "=", partner.id),
        ], limit=5, order="write_date desc")

        if not tasks:
            msg_body = "I couldn't find recent tasks linked to this contact. Please share the task name."
            if message.wa_account_id:
                self.action_reply_to_user(message, msg_body)
            return msg_body

        lines = ["Here are the latest task statuses:"]
        for task in tasks:
            status = task.stage_id.name if task.stage_id else "In Progress"
            project_name = task.project_id.display_name if task.project_id else "No Project"
            lines.append(f"- {task.name} ({project_name}): {status}")

        msg_body = "\n".join(lines)
        if message.wa_account_id:
            self.action_reply_to_user(message, msg_body)
        return msg_body

    def action_reply_to_user(self, message, msg_body):
        """Send a WhatsApp reply for a given inbound message."""
        if not message.wa_account_id:
            return msg_body

        if message.ai_replied:
            message.write({"ai_reply_skipped_reason": "already_replied"})
            return False

        if self._reply_throttled(message, minutes=2):
            _logger.info(
                "AI: Reply throttled for %s (message %s)",
                message.mobile_number,
                message.id,
            )
            message.write({"ai_reply_skipped_reason": "sender_throttle_2m"})
            return False

        if not msg_body:
            msg_body = "Thanks for your message! Could you share a few more details?"

        wa_msg = self.env["whatsapp_evaluation.message"].create({
            "body": msg_body,
            "mobile_number": message.mobile_number,
            "message_type": "outbound",
            "wa_account_id": message.wa_account_id.id,
            "partner_id": message.partner_id.id,
        })
        wa_msg._send_message()
        message.write({
            "ai_replied": True,
            "ai_replied_at": fields.Datetime.now(),
        })
        return wa_msg

    def _reply_throttled(self, message, minutes=2):
        if not message.mobile_number:
            return False

        since = fields.Datetime.now() - timedelta(minutes=minutes)
        recent = self.env["whatsapp_evaluation.message"].search_count([
            ("message_type", "=", "outbound"),
            ("mobile_number", "=", message.mobile_number),
            ("create_date", ">=", since),
        ])
        return recent > 0
