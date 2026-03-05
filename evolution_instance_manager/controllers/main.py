# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import AccessError
from odoo.http import request


class EvolutionWebsiteController(http.Controller):

    @http.route('/evolution/instances', type='http', auth='user', website=True)
    def evolution_instances_page(self, **kwargs):
        if not request.env.user.has_group('base.group_user'):
            raise Forbidden()

        try:
            records = request.env['evolution.instance.account'].search([], order='id desc')
        except AccessError:
            raise Forbidden()

        return request.render('evolution_instance_manager.evolution_instances_website_page', {
            'records': records,
        })
