
import logging
import requests
import base64
from odoo import models, fields, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class WhatsAppConnectorWizard(models.TransientModel):
    _name = 'whatsapp.connector.wizard'
    _description = 'WhatsApp Connector Wizard'

    def _default_base_url(self):
        return ''

    def _default_api_key(self):
        return ''

    base_url = fields.Char(string='API Base URL', required=True, default=_default_base_url,
                          help="e.g., https://api.yoursite.com")
    api_key = fields.Char(string='Global API Key', required=True, default=_default_api_key)
    
    instance_name = fields.Char(string='Instance Name', required=True, default="MyInstance")
    phone_number = fields.Char(string='Phone Number', help="Phone number involved in this connection")
    instance_token = fields.Char(string='Instance Token', readonly=True)
    
    qr_code = fields.Binary(string='QR Code', readonly=True)
    connection_status = fields.Char(string='Status', default='draft', readonly=True)
    
    setup_step = fields.Selection([
        ('create', 'Create Instance'),
        ('scan', 'Scan QR'),
        ('done', 'Done')
    ], default='create', string="Step")

    def action_create_instance(self):
        """ Creates the instance on Evolution API """
        self.ensure_one()
        url = f"{self.base_url.rstrip('/')}/instance/create"
        headers = {
            'apikey': self.api_key,
            'Content-Type': 'application/json'
        }
        # Evolution API v2 typically handles 'number' in create payload if provided? 
        # Usually it's just instanceName. We'll send it if specific version supports it, 
        # but mostly this is for user reference or custom naming.
        # We will NOT use it as instance name unless user duplicates it, keeping them separate.
        
        payload = {
            "instanceName": self.instance_name,
            "token": "", 
            "qrcode": False,
            "webhook_by_events": False,
        }
        
        try:
            _logger.info("Creating Instance at %s", url)
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            
            if response.status_code in [200, 201]:
                data = response.json()
                
                instance_data = data.get('instance') or data
                if isinstance(instance_data, dict):
                    token = instance_data.get('token')
                    if not token and 'auth' in data: 
                        token = data['auth'].get('token')
                else: 
                     token = data.get('token')

                if not token:
                     # Attempt to fetch if it already exists logic could go here
                     raise UserError(_("Instance created but token not found in response: %s") % str(data))

                self.instance_token = token
                self.setup_step = 'scan'
                
                # Auto-fetch QR
                self.action_fetch_qr()
                
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': self._name,
                    'res_id': self.id,
                    'view_mode': 'form',
                    'target': 'new',
                }
            elif response.status_code == 403: 
                 raise UserError(_("Instance Name already exists. Please choose a different name."))
            else:
                raise UserError(_("Failed to create instance. Status: %s. Body: %s") % (response.status_code, response.text))

        except requests.exceptions.RequestException as e:
            raise UserError(_("Connection Error: %s") % str(e))

    def action_fetch_qr(self):
        """ Fetches the QR code for connection """
        self.ensure_one()
        url = f"{self.base_url.rstrip('/')}/instance/connect/{self.instance_name}"
        headers = {
            'apikey': self.api_key
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                b64_img = data.get('base64')
                if b64_img:
                    if 'base64,' in b64_img:
                        b64_img = b64_img.split('base64,')[1]
                    self.qr_code = b64_img
                    self.connection_status = 'waiting_scan'
                else:
                    if 'instance' in data and data['instance'].get('state') == 'open':
                         self.connection_status = 'connected'
                         self.setup_step = 'done'
            else:
                 _logger.error("Failed to fetch QR: %s", response.text)
        except Exception as e:
            _logger.error("Error fetching QR: %s", str(e))

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_check_status(self):
        """ Checks status and shows credentials if connected """
        self.ensure_one()
        url = f"{self.base_url.rstrip('/')}/instance/connectionState/{self.instance_name}"
        headers = {
            'apikey': self.api_key
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                state = data.get('instance', {}).get('state')
                
                if state == 'open':
                    self.connection_status = 'connected'
                    self.setup_step = 'done'
                    
                    # STANDALONE MODE: Do not create account record.
                    # Just show success message.
                    
                    return {
                        'type': 'ir.actions.act_window', # Stay on form to show Done step with info
                        'res_model': self._name,
                        'res_id': self.id,
                        'view_mode': 'form',
                        'target': 'new',
                    }
                else:
                     self.connection_status = state
                     return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'title': _("Status"),
                            'message': _("Current State: %s. Scan the QR code if visible.") % state,
                            'type': 'warning',
                            'sticky': False,
                        }
                    }
            
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
            
        except Exception as e:
            raise UserError(_("Error checking status: %s") % str(e))
