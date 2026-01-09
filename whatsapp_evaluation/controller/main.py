# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import json
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)

class WebhookEvaluation(http.Controller):

    @http.route('/whatsapp_evaluation/webhook/', methods=['POST'], type="json", auth="public", csrf=False)
    def webhookpost(self):
        """
        Handler for Evolution API Webhooks.
        """
        data = request.get_json_data()
        _logger.info("Evolution API Webhook received: %s", json.dumps(data, indent=2))

        # Evolution API typically sends { "event": "...", "instance": "...", "data": { ... } }
        event_type = data.get('event')
        instance_name = data.get('instance')

        if not instance_name:
             # Some versions might structure differently, check 'instance' inside data??
             # Fallback to broad search if needed or just return 200
             return 'OK'

        # Find the account based on instance name
        account = request.env['whatsapp_evaluation.account'].sudo().search(
            [('instance_name', '=', instance_name)], limit=1
        )
        
        if not account:
            _logger.warning("No WhatsApp Evaluation Account found for instance: %s", instance_name)
            return 'OK'

        # Process specific events
        if event_type == 'MESSAGES_UPSERT':
            self._handle_messages_upsert(account, data.get('data', {}))
        
        return 'OK'

    def _handle_messages_upsert(self, account, data):
        """
        Process incoming messages.
        """
        messages = data.get('messages', [])
        for msg in messages:
            key = msg.get('key', {})
            if key.get('fromMe', False):
                continue # Skip own messages
            
            remote_jid = key.get('remoteJid')
            if not remote_jid:
                continue

            # remoteJid is usually "123456789@s.whatsapp.net"
            mobile_number = remote_jid.split('@')[0]

            # Extract message content
            message_content = msg.get('message', {})
            body = (
                message_content.get('conversation') or 
                message_content.get('extendedTextMessage', {}).get('text') or
                message_content.get('imageMessage', {}).get('caption') or
                ''
            )
            
            if not body:
                continue
            
            # Find or create channel
            channel = request.env['discuss.channel'].sudo()._get_whatsapp_channel(
                mobile_number, account, create_if_not_found=True
            )
            
            # Post message to channel
            # We use a custom context or kwarg to signal this is inbound to avoid loops if needed,
            # though our logic checks 'whatsapp_inbound_msg_uid' or similar.
            
            # Create the Odoo message
            channel.message_post(
                body=body,
                message_type='whatsapp_message', # Use custom type or 'comment'
                subtype_xmlid='mail.mt_comment',
                whatsapp_inbound_msg_uid=key.get('id')
            )
            
            # Also create the whatsapp_evaluation.message record linked to it
            # Note: discuss.channel.message_post in our model override needs to handle this
            # OR we handle it here explicitly if the override is for outbound only.
            
            # Let's do it explicitly here for clarity and robust linking
            # Actually, standard whatsapp model does it in notify_thread or similar. 
            # For simplicity:
            last_msg = channel.message_ids[0] # The one we just posted
            
            request.env['whatsapp_evaluation.message'].sudo().create({
                 'body': body,
                 'mobile_number': mobile_number,
                 'wa_account_id': account.id,
                 'mail_message_id': last_msg.id,
                 'message_type': 'inbound',
                 'state': 'received',
                 'msg_uid': key.get('id')
            }) 
