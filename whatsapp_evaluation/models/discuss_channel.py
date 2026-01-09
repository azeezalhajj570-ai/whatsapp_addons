# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from odoo.tools import html2plaintext

class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    channel_type = fields.Selection(
        selection_add=[('whatsapp', 'WhatsApp Conversation')],
        ondelete={'whatsapp': 'cascade'}
    )
    whatsapp_number = fields.Char(string="WhatsApp Number")
    wa_account_id = fields.Many2one('whatsapp_evaluation.account', string="WhatsApp Account")
    
    @api.model
    def _get_whatsapp_channel(self, whatsapp_number, wa_account_id, create_if_not_found=False):
        """ Find or create a WhatsApp channel for the given number """
        domain = [
            ('channel_type', '=', 'whatsapp'),
            ('whatsapp_number', '=', whatsapp_number),
            ('wa_account_id', '=', wa_account_id.id)
        ]
        channel = self.sudo().search(domain, limit=1)
        
        if not channel and create_if_not_found:
            partner = self.env['res.partner'].sudo().search([('mobile', '=', whatsapp_number)], limit=1)
            name = whatsapp_number
            if partner:
                name = partner.name

            channel = self.sudo().create({
                'channel_type': 'whatsapp',
                'name': name,
                'whatsapp_number': whatsapp_number,
                'wa_account_id': wa_account_id.id,
            })
            if partner:
                 channel.add_members(partner.ids)
                 
        return channel

    def message_post(self, *args, **kwargs):
        """ Override to capture messages posted in WhatsApp channels """
        message = super().message_post(*args, **kwargs)
        
        if self.channel_type == 'whatsapp' and not kwargs.get('whatsapp_inbound_msg_uid'):
            # This is an outbound message from Odoo to WhatsApp
            self._create_whatsapp_message(message)
            
        return message

    def _create_whatsapp_message(self, message):
        """ Create linked WhatsApp message and send it """
        if not message.body:
            return

        body_text = html2plaintext(message.body)
        
        wa_msg = self.env['whatsapp_evaluation.message'].create({
            'body': body_text,
            'mobile_number': self.whatsapp_number,
            'wa_account_id': self.wa_account_id.id,
            'mail_message_id': message.id,
            'message_type': 'outbound',
            'state': 'outgoing',
        })
        wa_msg._send_message()
