# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WhatsApp Messaging for Odoo (Evaluation API)',
    'category': 'Marketing Automation',
    'summary': 'Send WhatsApp messages, templates, and notifications directly from Odoo',
    'version': '1.0.0',
    'description': """
WhatsApp Messaging for Odoo allows you to communicate with your customers directly from Odoo using WhatsApp.

🚀 Key Features:
- Send WhatsApp messages to contacts and customers
- Use WhatsApp message templates
- Integrated WhatsApp composer inside Odoo
- Phone number validation before sending
- Chatter & messaging menu integration
- Multi-company support
- Secure access control and audit-friendly logging

🎯 Use Cases:
- Sales follow-ups
- Order confirmations
- Customer notifications
- Marketing campaigns
- Lead engagement

⚠️ This module uses the WhatsApp Evaluation API and is intended for testing, demos, and controlled usage scenarios.

Fully integrated with Odoo’s messaging and contact management system.
""",
    'depends': [
        'base',
        'web',
        'mail',
        'phone_validation',
        'sale',
        'account',
        'point_of_sale',
    ],
    'data': [
        'security/whatsapp_security.xml',
        'security/ir.model.access.csv',
        'security/ir_rules.xml',
        'views/whatsapp_account_views.xml',
        'views/whatsapp_message_views.xml',
        'views/whatsapp_template_views.xml',
        'wizard/whatsapp_composer_views.xml',
        'views/whatsapp_menus.xml',
        'data/whatsapp_evaluation_demo.xml',
        'data/whatsapp_template_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'whatsapp_evaluation/static/src/core/common/**/*',
            'whatsapp_evaluation/static/src/core/web/messaging_menu_patch.xml',
            'whatsapp_evaluation/static/src/core/common/message_patch.js',
            'whatsapp_evaluation/static/src/core/common/message_patch.xml',
            'whatsapp_evaluation/static/src/core/public_web/**/*',
            'whatsapp_evaluation/static/src/chatter/web/**/*',
        ],
    },
    'images': ['static/description/main_screenshot.png'],
    'external_dependencies': {
        'python': ['phonenumbers'],
    },
    'author': 'Azeez',
    'website': 'https://github.com/mekhlafi98',
    'license': 'OPL-1',
    'application': True,
    'installable': True,
    'price': 99.00,
    'currency': 'EUR',
}
