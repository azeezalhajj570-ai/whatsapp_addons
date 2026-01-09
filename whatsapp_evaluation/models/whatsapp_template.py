# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class WhatsAppTemplate(models.Model):
    _name = 'whatsapp_evaluation.template'
    _description = 'WhatsApp Template'

    name = fields.Char(string="Name", required=True)
    body = fields.Text(string="Body", required=True)
    model_id = fields.Many2one('ir.model', string="Applies to", required=True, ondelete='cascade')
    model = fields.Char(related='model_id.model', string="Related Document Model", store=True)

    @api.model
    def _can_use_whatsapp(self, model_name):
        """Check if the model can use WhatsApp (has templates or logic allowed)."""
        # Simplified logic: Allow if any template exists for the model, or if it's sale.order (since we hardcoded the button there too).
        # For now, let's just check if there's a template, or return True for known models to enable the button.
        # Actually, let's mimimick the original: find if a template exists.
        return len(self._find_default_for_model(model_name)) > 0

    @api.model
    def _find_default_for_model(self, model_name):
        return self.search([('model', '=', model_name)], limit=1)
