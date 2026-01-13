# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import json
import base64
from odoo import http
from odoo.http import request, Response
from odoo.addons.whatsapp_evaluation.tools.whatsapp_api import WhatsAppApi

_logger = logging.getLogger(__name__)

class WebhookEvaluation(http.Controller):

    @http.route('/whatsapp_evaluation/webhook/', methods=['POST'], type="json", auth="public", csrf=False)
    def webhookpost(self):
        """
        Handler for Evolution API Webhooks.
        """
        data = request.get_json_data()
        # _logger.info("Evolution API Webhook received: %s", json.dumps(data, indent=2)) # Redacted for GDPR

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

        if not account:
            _logger.warning("No WhatsApp Evaluation Account found for instance: %s", instance_name)
            return 'OK'

        # Normalize event type: "messages.upsert" -> "MESSAGES_UPSERT"
        if event_type:
            event_type = event_type.upper().replace('.', '_')
        
        # Process specific events
        if event_type == 'MESSAGES_UPSERT':
            self._handle_messages_upsert(account, data.get('data', {}))
        elif event_type == 'MESSAGES_UPDATE':
            self._handle_messages_update(account, data.get('data', {}))
        elif event_type == 'SEND_MESSAGE':
            # Optional: Log or handle outgoing message ack if distinct from MESSAGES_UPDATE
            pass
        
        return 'OK'

    def _handle_messages_upsert(self, account, data):
        """
        Process incoming messages.
        """
        messages = data.get('messages', [])
        if not messages and 'key' in data:
            messages = [data]
        
        _logger.info("WhatsApp Upsert: Found %s messages to process", len(messages))

        for msg in messages:
            key = msg.get('key', {})
            if key.get('fromMe', False):
                continue # Skip own messages
            
            remote_jid = key.get('remoteJid')
            msg_uid = key.get('id')
            if not remote_jid or not msg_uid:
                continue
            
            # Deduplication: Check if we already processed this message ID
            existing_msg = request.env['whatsapp_evaluation.message'].sudo().search([
                ('msg_uid', '=', msg_uid)
            ], limit=1)
            
            if existing_msg:
                _logger.info("WhatsApp Upsert: Duplicate message ID %s (State: %s), skipping.", msg_uid, existing_msg.state)
                continue

            # remoteJid is usually "123456789@s.whatsapp.net"
            mobile_number = remote_jid.split('@')[0]

            # Extract message content
            message_content = msg.get('message', {})
            body = (
                message_content.get('conversation') or 
                message_content.get('extendedTextMessage', {}).get('text') or
                message_content.get('imageMessage', {}).get('caption') or
                message_content.get('videoMessage', {}).get('caption') or
                message_content.get('documentMessage', {}).get('caption') or
                message_content.get('templateMessage', {}).get('hydratedTemplate', {}).get('hydratedContentText') or
                
                # Media fallbacks (if no caption, use filename or type)
                ('🎥 Video Message' if 'videoMessage' in message_content else '') or
                ('🎤 Audio Message' if 'audioMessage' in message_content else '') or
                ('📄 Document Message' if 'documentMessage' in message_content else '') or
                ('📷 Image Message' if 'imageMessage' in message_content else '') or
                
                ''
            )
            
            _logger.info("WhatsApp Upsert: Extracted Body length: %s", len(body) if body else 0)

            # Extract base64 content (Evolution v2 often puts it inside 'message')
            file_content = msg.get('base64') or msg.get('message', {}).get('base64')

            if not body and not file_content:
                _logger.info("WhatsApp Upsert: No body and no base64. Skipping.")
                continue
            
            # Find or create channel
            _logger.info("WhatsApp Inbound: Finding Channel for %s", mobile_number)
            
            channel = request.env['discuss.channel'].sudo()._get_whatsapp_channel(
                mobile_number, account, create_if_not_found=True
            )
            
            if not channel:
                 _logger.error("WhatsApp Inbound: Failed to create/find channel for %s", mobile_number)
                 continue

            _logger.info("WhatsApp Inbound: Posting to Channel %s (ID: %s)", channel.name, channel.id)
            
            # Handle Attachments
            attachments_list = []
            # file_content already extracted above
            if file_content:
                # Sanitize Base64: Remove 'data:image/png;base64,' header if present
                if ',' in file_content and ';base64' in file_content[:50]:
                    file_content = file_content.split(',')[1]

                # Determine filename and mimetype
                # Default fallback
                filename = "whatsapp_media"
                mimetype = "application/octet-stream"
                
                # Use messageType as fallback or primary indicator
                msg_type = msg.get('messageType')
                
                if 'audioMessage' in message_content or msg_type == 'audioMessage':
                    mimetype = message_content.get('audioMessage', {}).get('mimetype', 'audio/ogg')
                    filename = "voice_message.ogg"
                elif 'imageMessage' in message_content or msg_type == 'imageMessage':
                    mimetype = message_content.get('imageMessage', {}).get('mimetype', 'image/jpeg')
                    filename = "image.jpg"
                elif 'videoMessage' in message_content or msg_type == 'videoMessage':
                    mimetype = message_content.get('videoMessage', {}).get('mimetype', 'video/mp4')
                    filename = "video.mp4"
                elif 'documentMessage' in message_content or msg_type == 'documentMessage':
                    mimetype = message_content.get('documentMessage', {}).get('mimetype', 'application/pdf')
                    filename = message_content.get('documentMessage', {}).get('fileName', 'document')

                # Odoo message_post expects (name, content) or (name, content, info_dict)
                # Content must be raw bytes, not base64 string.
                decoded_content = base64.b64decode(file_content)
                attachments_list.append((filename, decoded_content))
                _logger.info("WhatsApp Inbound: Prepared attachment %s", filename)

            # Post message to channel
            # We use a custom context or kwarg to signal this is inbound to avoid loops if needed,
            # though our logic checks 'whatsapp_inbound_msg_uid' or similar.
            
            # Determine Author (Partner)
            author_partner = request.env['res.partner'].sudo().search([
                ('mobile', '=', mobile_number)
            ], limit=1)
            author_id = author_partner.id if author_partner else None

            # Format body (Convert *Bold*, _Italic_, Newlines to HTML)
            from markupsafe import Markup
            formatted_body = Markup(WhatsAppApi.format_whatsapp_to_html(body))
            
            # Create the Odoo message
            # Use message_type='comment' to ensure it appears in Discuss and creating notifications/unread counts.
            # Enterprise Pattern: Pass attachments as list of tuples (name, content, mimetype)
            new_msg = channel.with_context(whatsapp_inbound_msg_uid=key.get('id')).message_post(
                body=formatted_body,
                author_id=author_id,
                message_type='comment', 
                subtype_xmlid='mail.mt_comment',
                attachments=attachments_list
            )
            
            # Also create the whatsapp_evaluation.message record linked to it
            request.env['whatsapp_evaluation.message'].sudo().create({
                'body': formatted_body,  # Store HTML so list view renders formatting (Bold/Italic)
                'mobile_number': mobile_number,
                'wa_account_id': account.id,
                'mail_message_id': new_msg.id,
                'message_type': 'inbound',
                'state': 'received',
                'msg_uid': key.get('id'),
                'attachment_ids': [(6, 0, new_msg.attachment_ids.ids)] if new_msg.attachment_ids else False
            })
             
            # Notify users explicitly (Toast) - REMOVED per user request
            # for user in account.notify_user_ids:
            #     _logger.info("WhatsApp Inbound: Sending Toast notification to User %s", user.name)
            #     user.partner_id._bus_send('simple_notification', {
            #        'type': 'info',
            #        'title': f"New WhatsApp from {mobile_number}",
            #        'message': body[:100] + ("..." if len(body) > 100 else ""),
            #        'sticky': False
            #     }) 

    def _handle_messages_update(self, account, data):
        """
        Handle message status updates (e.g. READ, DELIVERED)
        """
        # data usually contains: { "key": { "id": "..." }, "status": "READ", ... }
        # Or sometimes directly: { "keyId": "...", "status": "READ" } depending on Evolution version.
        # Based on user logs:
        # { "keyId": "...", "remoteJid": "...", "status": "READ", "messageId": "..." }
        
        msg_uid = data.get('keyId') or data.get('key', {}).get('id')
        status = data.get('status')
        
        if not msg_uid or not status:
            return

        # Map Evolution status to Odoo status
        # Evolution: PENDING, SERVER_ACK, DELIVERY_ACK, READ, PLAYED
        # Odoo: outgoing, sent, delivered, read, error
        
        odoo_state = False
        if status == 'SERVER_ACK':
            odoo_state = 'sent'
        elif status == 'DELIVERY_ACK':
            odoo_state = 'delivered'
        elif status in ['READ', 'PLAYED']:
            odoo_state = 'read'
            
        if odoo_state:
            message = request.env['whatsapp_evaluation.message'].sudo().search([
                ('msg_uid', '=', msg_uid)
            ], limit=1)
            
            if message:
                message.write({'state': odoo_state})
                _logger.info("Updated message %s status to %s", msg_uid, odoo_state)

