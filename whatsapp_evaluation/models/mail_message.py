# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields

class MailMessage(models.Model):
    _inherit = 'mail.message'

    message_type = fields.Selection(
        selection_add=[('whatsapp_message', 'WhatsApp')],
        ondelete={'whatsapp_message': lambda recs: recs.write({'message_type': 'comment'})},
    )
    wa_message_ids = fields.One2many('whatsapp_evaluation.message', 'mail_message_id', string='Related WhatsApp Messages')
