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
        'views/whatsapp_message_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'whatsapp_evaluation/static/src/core/common/store_service_patch.js',
            'whatsapp_evaluation/static/src/core/common/thread_model_patch.js',
            'whatsapp_evaluation/static/src/core/public_web/discuss_app_model_patch.js',
            'whatsapp_evaluation/static/src/core/web/channel_member_list_patch.js',
            'whatsapp_evaluation/static/src/core/web/channel_selector_patch.js',
            'whatsapp_evaluation/static/src/core/web/discuss_app_category_model_patch.js',
            'whatsapp_evaluation/static/src/core/web/discuss_sidebar_category_item_patch.xml',
            'whatsapp_evaluation/static/src/core/web/messaging_menu_patch.xml',
        ],
    },
    'external_dependencies': {
        'python': ['phonenumbers'],
    },
    'license': 'OEEL-1',
    'application': True,
    'installable': True,
}
