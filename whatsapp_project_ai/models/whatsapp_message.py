from odoo import models, fields

class WhatsAppMessage(models.Model):
    _inherit = 'whatsapp_evaluation.message'

    # ai_intent field removed in favor of Project Tags
    
    ai_confidence = fields.Float(string="AI Confidence")
    ai_rationale = fields.Text(string="AI Rationale")
    is_ai_processed = fields.Boolean(string="AI Processed", default=False)
    
    # Links to created records
    linked_model = fields.Char(string="Linked Model")
    linked_res_id = fields.Integer(string="Linked Record ID")

    # Override Tags to use Project Tags directly
    tag_ids = fields.Many2many('project.tags', string="Tags")

    def action_ai_classify(self):
        """Automation/UI entry point for AI processing."""
        for record in self:
            if record.is_ai_processed:
                continue
            self.env["whatsapp.project.ai.orchestrator"].process_incoming_message(
                record
            )

    def action_reprocess_ai(self):
        """Manual trigger for AI processing"""
        for record in self:
            record.write({"is_ai_processed": False})
            record.action_ai_classify()
