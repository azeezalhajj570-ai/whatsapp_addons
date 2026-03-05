# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    evolution_base_url = fields.Char(
        string='Evolution Base URL',
        config_parameter='evolution_instance_manager.base_url',
        help='Base URL for your Evolution API server, for example https://api.example.com',
    )
    evolution_server_api_key = fields.Char(
        string='Evolution Server API Key',
        config_parameter='evolution_instance_manager.server_api_key',
        groups='base.group_system',
        help='Server-level apikey used for instance management endpoints.',
    )
    evolution_max_instances_per_user = fields.Integer(
        string='Max Instances Per User',
        config_parameter='evolution_instance_manager.max_instances_per_user',
        default=0,
        help='Maximum number of active connected instances allowed per user. Set 0 for unlimited.',
    )
