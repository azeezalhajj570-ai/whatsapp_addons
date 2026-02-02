from odoo import models, fields, api

class WhatsAppMessage(models.Model):
    _inherit = 'whatsapp_evaluation.message'

    ai_intent = fields.Selection([
        ('new_service', 'New Service'),
        ('support', 'Support'),
        ('inquiry', 'Inquiry'),
        ('noise', 'Noise'),
    ], string="AI Intent")
    
    ai_confidence = fields.Float(string="AI Confidence")
    ai_rationale = fields.Text(string="AI Rationale")
    is_ai_processed = fields.Boolean(string="AI Processed", default=False)
    
    # Links to created records
    linked_model = fields.Char(string="Linked Model")
    linked_res_id = fields.Integer(string="Linked Record ID")

    # Override Tags to use Project Tags directly
    tag_ids = fields.Many2many('project.tags', string="Tags")

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record in records:
            # Code-based Trigger: Safe, Always-on (unless disabled via context)
            if (
                record.message_type == 'inbound' 
                and not record.is_ai_processed 
                and self.env.context.get('ai_auto_process', True)
            ):
                self.env['whatsapp.project.ai.orchestrator'].process_incoming_message(record)
        return records

    def action_reprocess_ai(self):
        """Manual trigger for AI processing"""
        for record in self:
            self.with_context(ai_auto_process=True).env['whatsapp.project.ai.orchestrator'].process_incoming_message(record)
