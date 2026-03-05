# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import re

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class EvolutionInstanceAccount(models.Model):
    _name = 'evolution.instance.account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Evolution API Instance Account'

    name = fields.Char(string='Name', required=True, tracking=True)
    active = fields.Boolean(default=True, tracking=True)
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company,
        index=True,
    )

    evo_instance_name = fields.Char(
        string='Evolution Instance Name',
        tracking=True,
        required=True,
        help='Evolution instance identifier used in API paths.',
    )
    evo_instance_id = fields.Char(
        string='Evolution Instance ID',
        tracking=True,
        copy=False,
        readonly=True,
    )
    evo_remote_exists = fields.Boolean(
        string='Evolution Instance Exists',
        copy=False,
        readonly=True,
    )
    evo_instance_key = fields.Char(
        string='Evolution Instance Key',
        groups='base.group_system',
        copy=False,
        readonly=True,
    )
    integration = fields.Char(
        string='Integration',
        tracking=True,
        default='WHATSAPP-BAILEYS',
        help='Integration value sent during instance creation.',
    )
    status = fields.Char(
        string='Evolution Status',
        tracking=True,
        copy=False,
    )
    last_status_sync_at = fields.Datetime(
        string='Last Status Sync At',
        copy=False,
        readonly=True,
    )
    last_error = fields.Text(
        string='Last Error',
        copy=False,
        readonly=True,
    )
    qr_code_text = fields.Text(
        string='QR Payload',
        copy=False,
        readonly=True,
    )
    qr_code_image = fields.Binary(
        string='QR Code Image',
        copy=False,
        readonly=True,
        attachment=True,
    )
    pairing_phone = fields.Char(
        string='Phone',
        required=True,
        help='Phone number used to request a pairing code (international format).',
    )
    pairing_code = fields.Char(
        string='Pairing Code',
        copy=False,
        readonly=True,
    )
    qr_last_fetched_at = fields.Datetime(
        string='Last QR/Pairing Fetch At',
        copy=False,
        readonly=True,
    )

    _sql_constraints = [
        (
            'evolution_instance_name_company_uniq',
            'unique(company_id, evo_instance_name)',
            'Evolution instance name must be unique per company.',
        ),
        (
            'evolution_instance_id_uniq',
            'unique(evo_instance_id)',
            'Evolution instance ID must be unique.',
        ),
    ]

    @api.constrains('evo_instance_name')
    def _check_evo_instance_name(self):
        for account in self:
            if account.evo_instance_name and ' ' in account.evo_instance_name:
                raise ValidationError(_('Evolution instance name must not contain spaces.'))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name'):
                vals['evo_instance_name'] = vals['name']
            vals.setdefault('integration', 'WHATSAPP-BAILEYS')
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('name'):
            vals['evo_instance_name'] = vals['name']
        return super().write(vals)

    @staticmethod
    def _as_dict(value):
        return value if isinstance(value, dict) else {}

    @staticmethod
    def _is_already_exists_error(exc):
        text = str(exc).lower()
        return 'already in use' in text or 'already exists' in text

    @staticmethod
    def _is_remote_not_found_error(exc):
        text = str(exc).lower()
        return '(404)' in text or 'does not exist' in text or 'not found' in text

    @staticmethod
    def _extract_instance_key(data, instance_data):
        # Common create response shape (v2 docs):
        # {"hash": {"apikey": "..."}, "instance": {...}}
        hash_value = data.get('hash')
        if isinstance(hash_value, dict):
            key = hash_value.get('apikey') or hash_value.get('apiKey')
            if key:
                return key
        elif isinstance(hash_value, str) and hash_value.strip():
            return hash_value.strip()

        # Fallbacks found in some deployments/custom builds.
        return (
            data.get('apikey')
            or data.get('apiKey')
            or instance_data.get('apikey')
            or instance_data.get('apiKey')
        )

    @staticmethod
    def _normalize_phone_for_evolution(phone):
        phone = (phone or '').strip()
        if not phone:
            return phone
        # Evolution create endpoint validates against ^\d+[\.@\w-]+
        # Strip leading '+' and non-digit separators for common phone input.
        if '@' in phone:
            return phone.lstrip('+')
        digits = re.sub(r'\D+', '', phone)
        return digits

    def action_create_evolution_instance(self):
        client = self.env['evolution.instance.client']
        for account in self:
            payload = {
                'instanceName': account.evo_instance_name,
                'integration': account.integration or 'WHATSAPP-BAILEYS',
                'qrcode': True,
                'number': self._normalize_phone_for_evolution(account.pairing_phone),
            }

            try:
                response = client.create_instance(payload)
                data = self._as_dict(response)
                instance_data = self._as_dict(data.get('instance'))
                instance_key = self._extract_instance_key(data, instance_data)

                account.write({
                    'evo_instance_id': instance_data.get('instanceId') or instance_data.get('id') or account.evo_instance_id,
                    'evo_instance_key': instance_key or account.evo_instance_key,
                    'status': instance_data.get('status') or instance_data.get('state') or account.status,
                    'evo_remote_exists': True,
                    'last_error': False,
                })
                # Ensure pairing is initialized with the provided phone on fresh create.
                # Some Evolution setups only bind/display the phone after connect call with `number`.
                try:
                    response_pair = client.fetch_pairing_code(
                        account.evo_instance_name,
                        self._normalize_phone_for_evolution(account.pairing_phone),
                    )
                    pairing_code = self._extract_pairing_code(response_pair)
                    if pairing_code:
                        account.write({'pairing_code': pairing_code})
                except Exception:
                    # Do not fail instance creation if pairing bootstrap fails.
                    pass
                account.message_post(body=_('Evolution instance created or confirmed successfully.'))
            except Exception as exc:
                values = {'last_error': str(exc)}
                if self._is_already_exists_error(exc):
                    values['evo_remote_exists'] = True
                account.write(values)
                account.message_post(body=_('Evolution instance creation failed: %s') % exc)
                raise UserError(str(exc)) from exc

    def action_refresh_evolution_status(self):
        client = self.env['evolution.instance.client']
        now = fields.Datetime.now()

        for account in self:
            try:
                response = client.connection_state(account.evo_instance_name)
                data = self._as_dict(response)
                instance_data = self._as_dict(data.get('instance'))
                new_status = instance_data.get('state') or data.get('state') or data.get('status')

                account.write({
                    'status': new_status or account.status,
                    'last_status_sync_at': now,
                    'last_error': False,
                })
                account.message_post(body=_('Evolution status refreshed successfully.'))
            except Exception as exc:
                account.write({
                    'last_status_sync_at': now,
                    'last_error': str(exc),
                })
                account.message_post(body=_('Evolution status refresh failed: %s') % exc)
                raise UserError(str(exc)) from exc

    @staticmethod
    def _extract_qr_data(response):
        data = EvolutionInstanceAccount._as_dict(response)
        qr_container = EvolutionInstanceAccount._as_dict(data.get('qrcode') or data.get('qr'))
        instance = EvolutionInstanceAccount._as_dict(data.get('instance'))

        base64_qr = (
            qr_container.get('base64')
            or data.get('base64')
            or data.get('qrBase64')
            or instance.get('base64')
        )
        qr_text = (
            qr_container.get('code')
            or data.get('code')
            or data.get('pairingCode')
            or instance.get('code')
        )
        status = (
            data.get('status')
            or instance.get('status')
            or instance.get('state')
        )
        return base64_qr, qr_text, status

    @staticmethod
    def _to_binary_image(base64_qr):
        if not base64_qr:
            return False
        if base64_qr.startswith('data:image'):
            _, _, payload = base64_qr.partition(',')
            return payload or False
        try:
            base64.b64decode(base64_qr, validate=True)
            return base64_qr
        except Exception:
            return False

    @staticmethod
    def _extract_pairing_code(response):
        data = EvolutionInstanceAccount._as_dict(response)
        instance = EvolutionInstanceAccount._as_dict(data.get('instance'))
        return (
            data.get('pairingCode')
            or data.get('code')
            or instance.get('pairingCode')
            or instance.get('code')
        )

    def action_get_qr_code(self):
        self.ensure_one()
        client = self.env['evolution.instance.client']
        now = fields.Datetime.now()
        account = self
        try:
            response = client.fetch_qr(account.evo_instance_name)
            base64_qr, qr_text, status = self._extract_qr_data(response)
            qr_image = self._to_binary_image(base64_qr)
            account.write({
                'qr_code_image': qr_image,
                'qr_code_text': qr_text or account.qr_code_text,
                'status': status or account.status,
                'last_error': False,
                'qr_last_fetched_at': now,
            })
            account.message_post(body=_('QR code fetched successfully.'))
            wizard = self.env['evolution.instance.qr.wizard'].create({
                'account_id': account.id,
                'status': account.status,
                'qr_code_image': qr_image,
                'qr_code_text': qr_text or account.qr_code_text,
                'pairing_phone': account.pairing_phone,
                'pairing_code': account.pairing_code,
                'fetched_at': now,
            })
            return {
                'type': 'ir.actions.act_window',
                'name': _('Scan QR Code'),
                'res_model': 'evolution.instance.qr.wizard',
                'view_mode': 'form',
                'res_id': wizard.id,
                'target': 'new',
            }
        except Exception as exc:
            account.write({
                'last_error': str(exc),
                'qr_last_fetched_at': now,
            })
            account.message_post(body=_('QR code fetch failed: %s') % exc)
            raise UserError(str(exc)) from exc

    def action_get_pairing_code(self):
        client = self.env['evolution.instance.client']
        now = fields.Datetime.now()
        for account in self:
            if not account.pairing_phone:
                raise UserError(_('Set Phone first.'))
            try:
                response = client.fetch_pairing_code(
                    account.evo_instance_name,
                    self._normalize_phone_for_evolution(account.pairing_phone),
                )
                pairing_code = self._extract_pairing_code(response)
                if not pairing_code:
                    raise UserError(_('No pairing code returned by Evolution API.'))
                account.write({
                    'pairing_code': pairing_code,
                    'last_error': False,
                    'qr_last_fetched_at': now,
                })
                account.message_post(body=_('Pairing code fetched successfully.'))
            except Exception as exc:
                account.write({
                    'last_error': str(exc),
                    'qr_last_fetched_at': now,
                })
                account.message_post(body=_('Pairing code fetch failed: %s') % exc)
                raise UserError(str(exc)) from exc

    def action_delete_evolution_instance(self):
        client = self.env['evolution.instance.client']
        for account in self:
            if not account.evo_instance_name:
                raise UserError(_('Set Evolution Instance Name first.'))
            old_instance_name = account.evo_instance_name
            clear_vals = {
                'active': False,
                # Keep archived rows unique so same instance name can be recreated later.
                'name': '%s__archived__%s' % (account.name or old_instance_name, account.id),
                'evo_instance_name': '%s__archived__%s' % (old_instance_name, account.id),
                'evo_instance_id': False,
                'evo_remote_exists': False,
                'evo_instance_key': False,
                'status': False,
                'last_status_sync_at': False,
                'pairing_code': False,
                'qr_code_text': False,
                'qr_code_image': False,
                'qr_last_fetched_at': False,
                'last_error': False,
            }
            try:
                client.delete_instance(account.evo_instance_name)
                account.write(clear_vals)
                account.message_post(body=_('Evolution instance deleted successfully.'))
            except Exception as exc:
                if self._is_remote_not_found_error(exc):
                    account.write(clear_vals)
                    account.message_post(body=_('Evolution instance was already deleted remotely. Local data cleared.'))
                    continue
                account.write({'last_error': str(exc)})
                account.message_post(body=_('Evolution instance delete failed: %s') % exc)
                raise UserError(str(exc)) from exc

    def action_logout_evolution_instance(self):
        client = self.env['evolution.instance.client']
        for account in self:
            if not account.evo_instance_name:
                raise UserError(_('Set Evolution Instance Name first.'))
            try:
                client.logout_instance(account.evo_instance_name)
                account.write({
                    'status': 'close',
                    'last_status_sync_at': fields.Datetime.now(),
                    'pairing_code': False,
                    'qr_code_text': False,
                    'qr_code_image': False,
                    'qr_last_fetched_at': False,
                    'last_error': False,
                })
                account.message_post(body=_('Evolution instance disconnected successfully.'))
            except Exception as exc:
                account.write({'last_error': str(exc)})
                account.message_post(body=_('Evolution instance disconnect failed: %s') % exc)
                raise UserError(str(exc)) from exc

    def action_send_test_message(self):
        client = self.env['evolution.instance.client']
        for account in self:
            if account.status != 'open':
                raise UserError(_('Connection must be open to send a test message.'))
            if not account.pairing_phone:
                raise UserError(_('Set Phone first.'))
            if not account.evo_instance_id or not account.evo_instance_key:
                raise UserError(_('Instance ID and Instance Key are required to send test message.'))

            number = self._normalize_phone_for_evolution(account.pairing_phone)
            text = _('Test message from Odoo. Instance ID: %s') % account.evo_instance_id
            try:
                client.send_test_message(
                    account.evo_instance_name,
                    number,
                    text,
                    account.evo_instance_key,
                )
                account.write({'last_error': False})
                account.message_post(body=_('Test message sent successfully.'))
            except Exception as exc:
                account.write({'last_error': str(exc)})
                account.message_post(body=_('Test message failed: %s') % exc)
                raise UserError(str(exc)) from exc

    @api.model
    def _cron_sync_evolution_status(self):
        accounts = self.search([('evo_instance_name', '!=', False), ('active', '=', True)])
        for account in accounts:
            try:
                account.action_refresh_evolution_status()
            except Exception:
                continue
