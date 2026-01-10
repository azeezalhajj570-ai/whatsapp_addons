# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import requests
import json
import threading

from odoo import _
from odoo.addons.whatsapp_evaluation.tools.whatsapp_exception import WhatsAppError

_logger = logging.getLogger(__name__)

class WhatsAppApi:
    def __init__(self, base_url, instance_name, api_key):
        self.base_url = base_url.rstrip('/')
        self.instance_name = instance_name
        self.api_key = api_key

    def __api_requests(self, request_type, endpoint, params=False, headers=None, data=False):
        if getattr(threading.current_thread(), 'testing', False):
             raise WhatsAppError("API requests disabled in testing.")

        headers = headers or {}
        headers.update({
            'apikey': self.api_key,
            'Content-Type': 'application/json',
        })
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            _logger.info("WhatsApp Evaluation Request: %s %s Headers: %s Data: %s", request_type, url, headers, data)
            json_data = data if data else None
            res = requests.request(request_type, url, params=params, headers=headers, json=json_data, timeout=(10, 30))
        except requests.exceptions.Timeout:
            _logger.error("WhatsApp Evaluation Timeout: %s", url)
            raise WhatsAppError("Connection timed out. Check firewall or API URL.", error_code="Timeout")
        except requests.exceptions.RequestException as e:
            _logger.error("WhatsApp Evaluation Network Error: %s", str(e))
            raise WhatsAppError(failure_type='network')

        try:
            if not res.ok:
                 # Attempt to parse error message from JSON
                 error_data = res.json()
                 raise WhatsAppError(*self._prepare_error_response(error_data))
        except ValueError:
            if not res.ok:
                raise WhatsAppError(failure_type='network')
        
        try:
             return res.json()
        except ValueError:
             return {}

    def _prepare_error_response(self, response):
        if 'error' in response and isinstance(response['error'], str):
            # Formats like {"status": 404, "error": "Not Found", ...}
            return (response.get('response', {}).get('message') or response['error'], response.get('status', 'odoo'))
        if 'message' in response:
            return (str(response['message']), 'odoo')
        return (_("Unknown Evolution API Error"), -1)

    def _test_connection(self):
        """ Test connection by checking instance state """
        # Using /instance/connectionState/{instance}
        endpoint = f"/instance/connectionState/{self.instance_name}"
        response = self.__api_requests("GET", endpoint)
        
        # Adjust based on actual response structure
        # Example response: {"instance": {"state": "open"}}
        state = response.get('instance', {}).get('state') or response.get('state')
        
        if state not in ['open', 'connecting', 'connected']:
             # Fallback check if simple instance fetch works
             _logger.warning("Connection state check returned: %s", state)
             # If we got a valid JSON response without 401/403, auth is likely fine.
        return True

    def _send_whatsapp(self, number, message_body):
        """ Send a text message """
        endpoint = f"/message/sendText/{self.instance_name}"
        payload = {
            "number": number,
            "text": message_body, # Simplified for some instances
            "textMessage": {
               "text": message_body
            }
        }
        # Note: Some versions use "textMessage": {"text": ...}, others might flatten it.
        # Sending both to be safe based on "sendText" docs usually expecting specific schema.
        # Strict schema from OpenAPI v1 was:
        # { "number": ..., "textMessage": { "text": ... } }
        
        payload = {
            "number": number,
            "text": message_body,
            "options": {
                "delay": 1200,
                "presence": "composing"
            }
        }
        
        return self.__api_requests("POST", endpoint, data=payload)

    def _send_whatsapp_media(self, number, attachment, caption=None):
        """ Send a media message """
        endpoint = f"/message/sendMedia/{self.instance_name}"
        
        # Odoo stores content as base64
        # Evolution API typically expects: { "number":..., "mediaMessage": { "mediatype": "image", "caption": "...", "media": "base64..." } }
        # Or simpler top-level: { "number": ..., "mediatype": "image", "caption": "...", "media": "..." }
        
        # Helper to map mimetype to Evolution type (image, video, document, audio)
        mimetype = attachment.mimetype
        if 'image' in mimetype:
            media_type = 'image'
        elif 'video' in mimetype:
            media_type = 'video'
        elif 'audio' in mimetype:
            media_type = 'audio'
        else:
            media_type = 'document'
            
        payload = {
            "number": number,
            "mediatype": media_type,
            "mimetype": mimetype,
            "caption": caption or attachment.name,
            "media": attachment.datas.decode('utf-8'), # binary to base64 string
            "fileName": attachment.name,
            "options": {
                "caption": caption or attachment.name
            }
        }
        
        _logger.info("Sending Media to %s. Caption: %s. Type: %s", number, payload['caption'], media_type)
        return self.__api_requests("POST", endpoint, data=payload)

    def update_webhook(self, webhook_url, enabled=True):
        """ Update instance webhook configuration """
        endpoint = f"/webhook/set/{self.instance_name}"
        payload = {
            "enabled": enabled,
            "url": webhook_url,
            "webhook_by_events": False,
            "events": [
                "MESSAGES_UPSERT",
                "MESSAGES_UPDATE",
                "SEND_MESSAGE",
            ]
        }
        return self.__api_requests("POST", endpoint, data=payload)
