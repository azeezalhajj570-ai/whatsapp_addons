# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.whatsapp_evaluation.tools.whatsapp_api import WhatsAppApi

class ExtendedWhatsAppApi(WhatsAppApi):
    """
    Subclass of WhatsAppApi to support dynamic delay in message sending.
    This allows the AI module to simulate typing behavior without modifying the core driver.
    """

    def _send_whatsapp(self, number, message_body, delay=1200):
        """ Send a text message with custom delay """
        endpoint = f"/message/sendText/{self.instance_name}"
        
        payload = {
            "number": number,
            "text": message_body,
            "options": {
                "delay": delay,
                "presence": "composing"
            }
        }
        
        # We access the private __api_requests of the parent. 
        # Since it is name-mangled (__api_requests -> _WhatsAppApi__api_requests), we need to use the mangled name 
        # OR better: Python inheritance rules for double underscore are tricky.
        # Ideally, we should check if `_WhatsAppApi__api_requests` is accessible.
        
        # Actually, double underscore methods are not easily overridden or called from subclasses if they are intended to be private.
        # However, checking the parent code, `__api_requests` is used internally.
        
        # Let's see if we can just re-implement a simple request wrapper or if we can access the parent's method using the mangled name.
        return self._WhatsAppApi__api_requests("POST", endpoint, data=payload)
