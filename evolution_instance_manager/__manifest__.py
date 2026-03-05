# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Evolution API Instance Manager for Odoo',
    'summary': 'Create, connect, monitor, and delete Evolution API instances from Odoo',
    'version': '1.0.0',
    'category': 'Marketing Automation',
    'description': """
Evolution API Instance Manager provides a standalone control panel inside Odoo
to manage Evolution API instances lifecycle.

Features:
- Global Evolution API settings in Odoo configuration
- Create Evolution instances and store identifiers/keys
- Refresh and sync connection state
- QR code wizard for WhatsApp connection
- Pairing code request support
- Delete instances directly from Odoo
- Multi-company isolation with ACL and record rules
- Scheduled background status synchronization
""",
    'author': 'Azeez',
    'maintainer': 'Azeez',
    'support': 'mekhlafi98@gmail.com',
    'website': 'https://github.com/mekhlafi98',
    'license': 'OPL-1',
    'depends': [
        'base',
        'web',
        'mail',
        'website',
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'views/res_config_settings_views.xml',
        'views/evolution_instance_account_views.xml',
        'views/evolution_instance_qr_wizard_views.xml',
        'views/evolution_website_views.xml',
        'data/ir_cron.xml',
    ],
    'images': ['static/description/main_screenshot.png'],
    'external_dependencies': {
        'python': ['requests'],
    },
    'installable': True,
    'application': True,
    'price': 15.00,
    'currency': 'EUR',
}
