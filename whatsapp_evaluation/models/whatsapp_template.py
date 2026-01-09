# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class WhatsAppTemplate(models.Model):
    _name = 'whatsapp_evaluation.template'
    _description = 'WhatsApp Template'

    name = fields.Char(string="Name", required=True)
    body = fields.Text(string="Body", required=True)
    model_id = fields.Many2one('ir.model', string="Applies to", required=True, ondelete='cascade')
    model = fields.Char(related='model_id.model', string="Related Document Model", store=True)
