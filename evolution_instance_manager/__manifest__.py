# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Evolution API Instance Manager',
    'summary': 'Manage Evolution API instances from Odoo',
    'version': '1.0.0',
    'category': 'Technical',
    'author': 'Azeez',
    'website': 'https://github.com/mekhlafi98',
    'license': 'OPL-1',
    'depends': [
        'base',
        'mail',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'views/res_config_settings_views.xml',
        'views/evolution_instance_account_views.xml',
        'views/evolution_instance_qr_wizard_views.xml',
        'data/ir_cron.xml',
    ],
    'installable': True,
    'application': True,
}
