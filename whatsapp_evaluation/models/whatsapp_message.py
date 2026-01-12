# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from odoo import models, fields, api, _
from odoo.addons.whatsapp_evaluation.tools.whatsapp_api import WhatsAppApi
from odoo.addons.whatsapp_evaluation.tools.whatsapp_exception import WhatsAppError
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

class WhatsAppMessage(models.Model):
    _name = 'whatsapp_evaluation.message'
    _description = 'WhatsApp Evaluation Messages'
    _order = 'id desc'
    _rec_name = 'mobile_number'

    body = fields.Html(string="Body")
    mobile_number = fields.Char(string="Phone Number", required=True)
    msg_uid = fields.Char(string="WhatsApp Message ID")
    
    state = fields.Selection([
        ('outgoing', 'In Queue'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('read', 'Read'),
        ('received', 'Received'),
        ('error', 'Failed'),
    ], string="State", default='outgoing')

    message_type = fields.Selection([
        ('outbound', 'Outbound'),
        ('inbound', 'Inbound')
    ], string="Message Type", default='outbound')

    wa_account_id = fields.Many2one('whatsapp_evaluation.account', string="WhatsApp Account", required=True)
    mail_message_id = fields.Many2one('mail.message', string="Related Mail Message")
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments")
    failure_reason = fields.Char(string="Failure Reason")

    _SUPPORTED_ATTACHMENT_TYPE = {
        'audio': ('audio/aac', 'audio/mp4', 'audio/mpeg', 'audio/amr', 'audio/ogg'),
        'document': (
            'text/plain', 'application/pdf', 'application/vnd.ms-powerpoint', 'application/msword',
            'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        ),
        'image': ('image/jpeg', 'image/png'),
        'video': ('video/mp4',),
    }

    def _send_message(self):
        """ Send the message via API """
        for record in self:
            if record.state != 'outgoing' or record.message_type != 'outbound':
                continue
            
            # Use sudo() because api_key/token are restricted to System Users
            api = record.wa_account_id.sudo()._get_api_client()
            response = {}
            
            try:
                # Handle Media
                if record.attachment_ids:
                    attachment = record.attachment_ids[0] # Send first attachment for now
                    whatsapp_media_type = next((
                        media_type
                        for media_type, mimetypes
                        in self._SUPPORTED_ATTACHMENT_TYPE.items()
                        if attachment.mimetype in mimetypes),
                        False
                    )
                    if not whatsapp_media_type:
                         raise WhatsAppError(_("Attachment mimetype is not supported by WhatsApp: %s.", attachment.mimetype))
                    
                    # Ensure we send plain text for caption
                    caption = html2plaintext(record.body) if record.body else ''
                    response = api._send_whatsapp_media(record.mobile_number, attachment, caption)
                else:
                    # Ensure we send plain text, even if stored as HTML
                    text_body = html2plaintext(record.body) if record.body else ''
                    response = api._send_whatsapp(record.mobile_number, text_body)
                
                msg_id = False
                if isinstance(response, dict):
                    if 'key' in response:
                        msg_id = response['key'].get('id')
                    elif 'id' in response:
                        msg_id = response['id']
                
                record.write({
                    'state': 'sent',
                    'msg_uid': msg_id,
                    'failure_reason': False
                })
            except WhatsAppError as e:
                record.write({
                    'state': 'error',
                    'failure_reason': str(e)
                })
            except Exception as e:
                _logger.exception("Error sending WhatsApp message")
                record.write({
                    'state': 'error',
                    'failure_reason': str(e)
                })

    def button_resend(self):
        """ Retry sending a failed message """
        for record in self:
            if record.state == 'error':
                 record.state = 'outgoing'
                 record._send_message()
