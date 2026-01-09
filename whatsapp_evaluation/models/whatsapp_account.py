# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import secrets
import string

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.addons.whatsapp_evaluation.tools.whatsapp_api import WhatsAppApi
from odoo.addons.whatsapp_evaluation.tools.whatsapp_exception import WhatsAppError

_logger = logging.getLogger(__name__)


class WhatsAppAccount(models.Model):
    _name = 'whatsapp_evaluation.account'
    _inherit = ['mail.thread']
    _description = 'WhatsApp Evaluation Account'

    name = fields.Char(string="Name", tracking=1)
    active = fields.Boolean(default=True, tracking=6)

    app_uid = fields.Char(string="App ID", required=True, tracking=2)
    app_secret = fields.Char(string="App Secret", groups='base.group_system', required=True)
    account_uid = fields.Char(string="Account ID", required=True, tracking=3)
    phone_uid = fields.Char(string="Phone Number ID", required=True, tracking=4)
    token = fields.Char(string="Access Token", required=True, groups='base.group_system')
    webhook_verify_token = fields.Char(string="Webhook Verify Token", compute='_compute_verify_token',
                                       groups='base.group_system', store=True)
    callback_url = fields.Char(string="Callback URL", compute='_compute_callback_url', readonly=True, copy=False)

    allowed_company_ids = fields.Many2many(
        comodel_name='res.company', string="Allowed Company",
        default=lambda self: self.env.company)
    notify_user_ids = fields.Many2many(
        comodel_name='res.users', default=lambda self: self.env.user,
        domain=[('share', '=', False)], required=True, tracking=5,
        help="Users to notify when a message is received")

    _sql_constraints = [
        ('phone_uid_unique', 'unique(phone_uid)', "The same phone number ID already exists")]

    @api.constrains('notify_user_ids')
    def _check_notify_user_ids(self):
        for phone in self:
            if len(phone.notify_user_ids) < 1:
                raise ValidationError(_("Users to notify is required"))

    def _compute_callback_url(self):
        for account in self:
            account.callback_url = self.get_base_url() + '/whatsapp_evaluation/webhook'

    @api.model
    def _get_api_client(self):
        self.ensure_one()
        return WhatsAppApi(self.base_url, self.instance_name, self.api_key)

    def button_test_connection(self):
        for account in self:
            api = account._get_api_client()
            try:
                # Test connection logic will be implemented in WhatsAppApi
                api._test_connection()
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'title': _("Connection Successful"),
                        'message': _("Successfully connected to Evolution API instance."),
                        'type': 'success',
                        'sticky': False,
                    }
                }
            except WhatsAppError as e:
                raise UserError(_("Connection Failed: %s") % str(e))
            except Exception as e:
                _logger.error("WhatsApp Connection Error: %s", str(e))
                raise UserError(_("Connection Failed. Check logs for details."))
