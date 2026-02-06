from odoo import api, models


class IrModelData(models.Model):
    _inherit = "ir.model.data"

    @api.model
    def _wa_ai_cleanup_legacy_xmlids(self):
        names = [
            "action_ai_create_lead",
            "action_ai_create_project",
            "action_ai_create_task",
            "action_ai_reply_to_user",
            "action_ai_follow_up_project",
            "action_ai_follow_up_task",
            "action_ai_reply_task_status_unavailable",
            "action_ai_execute_decision",
            "wa_ai_auto_reply_low_confidence",
            "wa_ai_auto_classify_inbound",
            "wa_ai_auto_execute_decision",
            "wa_ai_action_classify_inbound",
            "wa_ai_action_reply_low_confidence",
            "wa_ai_action_execute_decision",
        ]
        xmlids = self.search([
            ("module", "=", "whatsapp_project_ai"),
            ("name", "in", names),
        ])
        if xmlids:
            xmlids.unlink()
        return True
