# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'WhatsApp Evaluation Messaging',
    'category': 'Marketing/WhatsApp',
    'summary': 'Text your Contacts on WhatsApp via Evaluation API',
    'version': '1.0',
    'description': """This module integrates Odoo with WhatsApp via the Evaluation API""",
    'depends': ['mail', 'phone_validation'],
    'data': [
        'security/ir.model.access.csv',
        'views/whatsapp_account_views.xml',
    ],
    'external_dependencies': {
        'python': ['phonenumbers'],
    },
    'license': 'OEEL-1',
    'application': True,
    'installable': True,
}
