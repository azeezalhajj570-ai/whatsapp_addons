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
    def evolution_instances_page(self, success=None, error=None, **kwargs):
        self._check_internal_user()

        try:
            records = request.env['evolution.instance.account'].search([], order='id desc')
        except AccessError:
            raise Forbidden()

        return request.render('evolution_instance_manager_website.evolution_instances_website_page', {
            'records': records,
            'success': success,
            'error': error,
            'csrf_token': request.csrf_token(),
        })

    @http.route('/evolution/instances/create', type='http', auth='user', website=True, methods=['POST'])
    def evolution_instances_create(self, **post):
        self._check_internal_user()

        vals = {
            'name': (post.get('name') or '').strip(),
            'evo_instance_name': (post.get('evo_instance_name') or '').strip(),
            'pairing_phone': (post.get('pairing_phone') or '').strip(),
            'integration': (post.get('integration') or 'WHATSAPP-BAILEYS').strip(),
        }

        if not vals['name'] or not vals['evo_instance_name'] or not vals['pairing_phone']:
            return request.redirect('/evolution/instances?error=Please fill all required fields.')

        try:
            account = request.env['evolution.instance.account'].create(vals)
            account.action_create_evolution_instance()
            return request.redirect('/evolution/instances?success=Instance created successfully.')
        except (UserError, AccessError) as exc:
            msg = str(exc) or 'Failed to create instance.'
            return request.redirect('/evolution/instances?error=%s' % msg)
