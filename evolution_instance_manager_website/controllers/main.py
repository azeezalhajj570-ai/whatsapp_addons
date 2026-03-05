# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import AccessError, UserError
from odoo.http import request


class EvolutionWebsiteController(http.Controller):

    @staticmethod
    def _check_internal_user():
        if not request.env.user.has_group('base.group_user'):
            raise Forbidden()

    @http.route('/evolution/instances', type='http', auth='user', website=True)
    def evolution_instances_page(self, success=None, error=None, show_qr_id=None, **kwargs):
        self._check_internal_user()

        try:
            records = request.env['evolution.instance.account'].search([], order='id desc')
        except AccessError:
            raise Forbidden()

        return request.render('evolution_instance_manager_website.evolution_instances_website_page', {
            'records': records,
            'success': success,
            'error': error,
            'show_qr_id': int(show_qr_id) if show_qr_id else False,
            'csrf_token': request.csrf_token(),
        })

    @http.route('/evolution/instances/create', type='http', auth='user', website=True, methods=['POST'])
    def evolution_instances_create(self, **post):
        self._check_internal_user()

        vals = {
            'name': (post.get('name') or '').strip(),
            'pairing_phone': (post.get('pairing_phone') or '').strip(),
        }

        if not vals['name'] or not vals['pairing_phone']:
            return request.redirect('/evolution/instances?error=Please fill all required fields.')

        try:
            account = request.env['evolution.instance.account'].create(vals)
            account.action_create_evolution_instance()
            return request.redirect('/evolution/instances?success=Instance created successfully.')
        except (UserError, AccessError) as exc:
            msg = str(exc) or 'Failed to create instance.'
            return request.redirect('/evolution/instances?error=%s' % msg)

    @http.route('/evolution/instances/delete/<int:record_id>', type='http', auth='user', website=True, methods=['POST'])
    def evolution_instances_delete(self, record_id, **post):
        self._check_internal_user()
        try:
            account = request.env['evolution.instance.account'].browse(record_id)
            if not account.exists():
                return request.redirect('/evolution/instances?error=Instance not found.')
            account.action_delete_evolution_instance()
            return request.redirect('/evolution/instances?success=Instance deleted successfully.')
        except (UserError, AccessError) as exc:
            msg = str(exc) or 'Failed to delete instance.'
            return request.redirect('/evolution/instances?error=%s' % msg)

    @http.route('/evolution/instances/qr/<int:record_id>', type='http', auth='user', website=True, methods=['POST'])
    def evolution_instances_qr(self, record_id, **post):
        self._check_internal_user()
        try:
            account = request.env['evolution.instance.account'].browse(record_id)
            if not account.exists():
                return request.redirect('/evolution/instances?error=Instance not found.')
            account.action_get_qr_code()
            return request.redirect('/evolution/instances?show_qr_id=%s' % account.id)
        except (UserError, AccessError) as exc:
            msg = str(exc) or 'Failed to fetch QR code.'
            return request.redirect('/evolution/instances?error=%s' % msg)

    @http.route('/evolution/instances/qr/fetch', type='json', auth='user', website=True, methods=['POST'])
    def evolution_instances_qr_fetch(self, record_id):
        self._check_internal_user()
        account = request.env['evolution.instance.account'].browse(int(record_id))
        if not account.exists():
            return {'ok': False, 'error': 'Instance not found.'}
        try:
            account.action_get_qr_code()
            qr_value = account.qr_code_image or ''
            if isinstance(qr_value, bytes):
                qr_value = qr_value.decode('utf-8')
            # Defensive cleanup for values serialized as b'...'
            if isinstance(qr_value, str) and qr_value.startswith("b'") and qr_value.endswith("'"):
                qr_value = qr_value[2:-1]
            return {'ok': True, 'record_id': account.id, 'qr_code_image': qr_value}
        except (UserError, AccessError) as exc:
            return {'ok': False, 'error': str(exc) or 'Failed to fetch QR code.'}
