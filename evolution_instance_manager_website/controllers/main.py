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
            records = request.env['evolution.instance.account'].search([('active', '=', True)], order='id desc')
        except AccessError:
            raise Forbidden()
        evolution_base_url = request.env['ir.config_parameter'].sudo().get_param(
            'evolution_instance_manager.base_url',
            default='',
        )

        return request.render('evolution_instance_manager_website.evolution_instances_website_page', {
            'records': records,
            'success': success,
            'error': error,
            'show_qr_id': int(show_qr_id) if show_qr_id else False,
            'evolution_base_url': evolution_base_url,
            'csrf_token': request.csrf_token(),
        })

    @http.route('/evolution/instances/create', type='http', auth='user', website=True, methods=['POST'])
    def evolution_instances_create(self, **post):
        self._check_internal_user()

        raw_name = (post.get('name') or '').strip()
        vals = {
            'name': raw_name,
            'pairing_phone': (post.get('pairing_phone') or '').strip(),
        }

        if not vals['name'] or not vals['pairing_phone']:
            return request.redirect('/evolution/instances?error=Please fill all required fields.')

        try:
            model = request.env['evolution.instance.account'].with_context(active_test=False)
            account = model.search([
                ('company_id', '=', request.env.company.id),
                ('evo_instance_name', '=', raw_name),
            ], limit=1)
            if account:
                account.write({
                    'active': True,
                    'name': raw_name,
                    'pairing_phone': vals['pairing_phone'],
                })
            else:
                account = model.create(vals)
            account.action_create_evolution_instance()
            return request.redirect('/evolution/instances?success=Instance created successfully.')
        except (UserError, AccessError) as exc:
            msg = str(exc) or 'Failed to create instance.'
            return request.redirect('/evolution/instances?error=%s' % msg)

    @http.route('/evolution/instances/create_ajax', type='json', auth='user', website=True, methods=['POST'])
    def evolution_instances_create_ajax(self, name=None, pairing_phone=None):
        self._check_internal_user()

        raw_name = (name or '').strip()
        raw_phone = (pairing_phone or '').strip()
        if not raw_name or not raw_phone:
            return {'ok': False, 'error': 'Please fill all required fields.'}

        try:
            model = request.env['evolution.instance.account'].with_context(active_test=False)
            account = model.search([
                ('company_id', '=', request.env.company.id),
                ('evo_instance_name', '=', raw_name),
            ], limit=1)
            if account:
                account.write({
                    'active': True,
                    'name': raw_name,
                    'pairing_phone': raw_phone,
                })
            else:
                account = model.create({
                    'name': raw_name,
                    'pairing_phone': raw_phone,
                })
            account.action_create_evolution_instance()
            return {
                'ok': True,
                'message': 'Instance created successfully.',
                'record': {
                    'id': account.id,
                    'name': account.name or '',
                    'pairing_phone': account.pairing_phone or '',
                    'status': account.status or '',
                    'last_status_sync_at': str(account.last_status_sync_at or ''),
                }
            }
        except (UserError, AccessError) as exc:
            return {'ok': False, 'error': str(exc) or 'Failed to create instance.'}
        except Exception as exc:
            return {'ok': False, 'error': str(exc) or 'Failed to create instance.'}

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

    @http.route('/evolution/instances/test/<int:record_id>', type='http', auth='user', website=True, methods=['POST'])
    def evolution_instances_test(self, record_id, **post):
        self._check_internal_user()
        try:
            account = request.env['evolution.instance.account'].browse(record_id)
            if not account.exists():
                return request.redirect('/evolution/instances?error=Instance not found.')
            account.action_send_test_message()
            return request.redirect('/evolution/instances?success=Test message sent successfully.')
        except (UserError, AccessError) as exc:
            msg = str(exc) or 'Failed to send test message.'
            return request.redirect('/evolution/instances?error=%s' % msg)

    @http.route('/evolution/instances/test_ajax', type='json', auth='user', website=True, methods=['POST'])
    def evolution_instances_test_ajax(self, record_id):
        self._check_internal_user()
        try:
            account = request.env['evolution.instance.account'].browse(int(record_id))
            if not account.exists():
                return {'ok': False, 'error': 'Instance not found.'}
            account.action_send_test_message()
            return {'ok': True, 'message': 'Test message sent successfully.'}
        except (UserError, AccessError) as exc:
            return {'ok': False, 'error': str(exc) or 'Failed to send test message.'}
        except Exception as exc:
            return {'ok': False, 'error': str(exc) or 'Failed to send test message.'}

    @http.route('/evolution/instances/status_check_ajax', type='json', auth='user', website=True, methods=['POST'])
    def evolution_instances_status_check_ajax(self, record_id):
        self._check_internal_user()
        try:
            account = request.env['evolution.instance.account'].browse(int(record_id))
            if not account.exists():
                return {'ok': False, 'error': 'Instance not found.'}
            account.action_refresh_evolution_status()
            return {
                'ok': True,
                'message': 'Instance status refreshed successfully.',
                'status': account.status or '',
                'last_status_sync_at': str(account.last_status_sync_at or ''),
            }
        except (UserError, AccessError) as exc:
            return {'ok': False, 'error': str(exc) or 'Failed to refresh status.'}
        except Exception as exc:
            return {'ok': False, 'error': str(exc) or 'Failed to refresh status.'}

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
            qr_text = account.qr_code_text or ''
            if isinstance(qr_text, bytes):
                qr_text = qr_text.decode('utf-8')
            if not qr_value and not qr_text:
                return {'ok': False, 'error': 'No QR data returned by Evolution API for this instance.'}
            return {
                'ok': True,
                'record_id': account.id,
                'qr_code_image': qr_value,
                'qr_code_text': qr_text,
            }
        except (UserError, AccessError) as exc:
            return {'ok': False, 'error': str(exc) or 'Failed to fetch QR code.'}
        except Exception as exc:
            return {'ok': False, 'error': str(exc) or 'Failed to fetch QR code.'}
