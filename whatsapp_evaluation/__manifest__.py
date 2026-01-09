# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WhatsApp Evaluation Messaging',
    'category': 'Marketing/WhatsApp',
    'summary': 'Text your Contacts on WhatsApp via Evaluation API',
    'version': '1.0',
    'description': """This module integrates Odoo with WhatsApp via the Evaluation API""",
    'depends': ['base', 'web', 'mail', 'phone_validation', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/whatsapp_account_views.xml',
        'views/whatsapp_message_views.xml',
        'views/whatsapp_template_views.xml',
        'wizard/whatsapp_composer_views.xml',
        'data/whatsapp_evaluation_demo.xml',
        'data/whatsapp_template_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'whatsapp_evaluation/static/src/core/common/**/*',
            'whatsapp_evaluation/static/src/core/web/**/*',
            'whatsapp_evaluation/static/src/core/public_web/**/*',
            'whatsapp_evaluation/static/src/chatter/web/**/*',
        ],
    },
    'external_dependencies': {
        'python': ['phonenumbers'],
    },
    'license': 'OEEL-1',
    'application': True,
    'installable': True,
}
