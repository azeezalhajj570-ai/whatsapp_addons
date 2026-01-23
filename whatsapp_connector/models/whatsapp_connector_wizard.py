
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
        # Try to find an existing account to pre-fill
        last_account = self.env['whatsapp_evaluation.account'].search([], limit=1, order='id desc')
        return last_account.base_url if last_account else ''

    def _default_api_key(self):
        last_account = self.env['whatsapp_evaluation.account'].search([], limit=1, order='id desc')
        return last_account.api_key if last_account else ''

    base_url = fields.Char(string='API Base URL', required=True, default=_default_base_url,
                          help="e.g., https://api.yoursite.com")
    api_key = fields.Char(string='Global API Key', required=True, default=_default_api_key)
    
    instance_name = fields.Char(string='Instance Name', required=True, default="MyInstance")
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
        payload = {
            "instanceName": self.instance_name,
            "token": "", # Let it auto-generate or user specific? Evolution generates if empty usually.
            "qrcode": False, # We fetch separately
            "webhook_by_events": False,
        }
        
        try:
            _logger.info("Creating Instance at %s", url)
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            
            if response.status_code in [200, 201]:
                data = response.json()
                # Evolution v2 response structure: 
                # { "instance": { "instanceName": "...", "token": "..." }, "hash": {...} }
                # OR sometimes directly { "instance": "name", "token": "token" } depending on version.
                
                instance_data = data.get('instance') or data
                # If 'instance' is nested object
                if isinstance(instance_data, dict):
                    token = instance_data.get('token')
                    # Fallback check
                    if not token and 'auth' in data: # v1 sometimes
                        token = data['auth'].get('token')
                else: 
                     # If data is flat? unlikely in v2
                     token = data.get('token')

                if not token:
                     # Attempt to fetch if it already exists?
                     # Sometimes create fails if exists, but we might want to just connect.
                     raise UserError(_("Instance might already exist or response format unexpected: %s") % str(data))

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
            elif response.status_code == 403: # Already exists usually
                 raise UserError(_("Instance Name already exists. Please choose a different name or delete the old one."))
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
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                # Evolution v2: { "base64": "data:image/png;base64,..." }
                # Or { "code": "..." } for pairing code (not handled here yet)
                b64_img = data.get('base64')
                if b64_img:
                    # Strip header if present
                    if 'base64,' in b64_img:
                        b64_img = b64_img.split('base64,')[1]
                    self.qr_code = b64_img
                    self.connection_status = 'waiting_scan'
                else:
                    # Might be already connected
                    if 'instance' in data and data['instance'].get('state') == 'open':
                         self.connection_status = 'connected'
                         self.setup_step = 'done'
            else:
                 _logger.error("Failed to fetch QR: %s", response.text)
                 # Don't raise, just log, user can retry
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
        """ Checks status and creates account if connected """
        self.ensure_one()
        url = f"{self.base_url.rstrip('/')}/instance/connectionState/{self.instance_name}"
        headers = {
            'apikey': self.api_key
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                state = data.get('instance', {}).get('state')
                
                if state == 'open':
                    self.connection_status = 'connected'
                    self.setup_step = 'done'
                    
                    # Create/Update the Odoo Account
                    Account = self.env['whatsapp_evaluation.account']
                    existing = Account.search([('instance_name', '=', self.instance_name)], limit=1)
                    
                    vals = {
                        'name': self.instance_name,
                        'base_url': self.base_url,
                        'instance_name': self.instance_name,
                        'api_key': self.api_key,
                        'instance_token': self.instance_token, # Saved from create step
                        'active': True
                    }
                    
                    if existing:
                        existing.write(vals)
                        account_id = existing.id
                    else:
                        account_id = Account.create(vals).id
                    
                    # Optional: Configure webhook automatically?
                    # needed to be done via button on account usually.
                    
                    return {
                        'type': 'ir.actions.act_window_close', # Close wizard
                        # Or redirect to the new account?
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
            
            # Refresh View
            return {
                'type': 'ir.actions.act_window',
                'res_model': self._name,
                'res_id': self.id,
                'view_mode': 'form',
                'target': 'new',
            }
            
        except Exception as e:
            raise UserError(_("Error checking status: %s") % str(e))
