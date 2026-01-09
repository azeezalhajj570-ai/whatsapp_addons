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
        Data structure usually mirrors Baileys event:
        {
          "messages": [
            {
              "key": { "remoteJid": "...", "fromMe": false, "id": "..." },
              "message": { "conversation": "..." },
              ...
            }
          ],
          "type": "notify"
        }
        """
        messages = data.get('messages', [])
        for msg in messages:
            key = msg.get('key', {})
            if key.get('fromMe', False):
                continue # Skip own messages
            
            remote_jid = key.get('remoteJid')
            if not remote_jid:
                continue

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
                
            _logger.info("Processing message from %s: %s", remote_jid, body)
            
            # TODO: Integrate with Odoo mail.thread or other logic
            # For now, just logging content.
            # account.message_post(...) 
