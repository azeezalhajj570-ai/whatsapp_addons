# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import UserError


class EvolutionInstanceQRWizard(models.TransientModel):
    _name = 'evolution.instance.qr.wizard'
    _description = 'Evolution Instance QR Wizard'

    account_id = fields.Many2one('evolution.instance.account', required=True, readonly=True)
    status = fields.Char(readonly=True)
    qr_code_image = fields.Binary(string='QR Code', readonly=True)
    qr_code_text = fields.Text(string='QR Payload', readonly=True)
    pairing_phone = fields.Char(string='Pairing Phone')
    pairing_code = fields.Char(string='Pairing Code', readonly=True)
    fetched_at = fields.Datetime(string='Fetched At', readonly=True)

    def action_refresh_qr(self):
        self.ensure_one()
        client = self.env['evolution.instance.client']
        account = self.account_id
        now = fields.Datetime.now()

        try:
            response = client.fetch_qr(account.evo_instance_name)
            base64_qr, qr_text, status = account._extract_qr_data(response)
            qr_image = account._to_binary_image(base64_qr)
            account.write({
                'qr_code_image': qr_image,
                'qr_code_text': qr_text or account.qr_code_text,
                'status': status or account.status,
                'last_error': False,
                'qr_last_fetched_at': now,
            })
            self.write({
                'status': account.status,
                'qr_code_image': qr_image,
                'qr_code_text': qr_text or account.qr_code_text,
                'fetched_at': now,
            })
        except Exception as exc:
            account.write({'last_error': str(exc), 'qr_last_fetched_at': now})
            raise UserError(str(exc)) from exc

        return {
            'type': 'ir.actions.act_window',
            'name': _('Scan QR Code'),
            'res_model': 'evolution.instance.qr.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def action_get_pairing_code(self):
        self.ensure_one()
        if not self.pairing_phone:
            raise UserError(_('Set Pairing Phone first.'))

        client = self.env['evolution.instance.client']
        account = self.account_id
        now = fields.Datetime.now()

        try:
            response = client.fetch_pairing_code(account.evo_instance_name, self.pairing_phone)
            pairing_code = account._extract_pairing_code(response)
            if not pairing_code:
                raise UserError(_('No pairing code returned by Evolution API.'))
            account.write({
                'pairing_phone': self.pairing_phone,
                'pairing_code': pairing_code,
                'last_error': False,
                'qr_last_fetched_at': now,
            })
            self.write({'pairing_code': pairing_code, 'fetched_at': now})
        except Exception as exc:
            account.write({'last_error': str(exc), 'qr_last_fetched_at': now})
            raise UserError(str(exc)) from exc

        return {
            'type': 'ir.actions.act_window',
            'name': _('Scan QR Code'),
            'res_model': 'evolution.instance.qr.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
