{
    'name': 'WhatsApp Evaluation Connector',
    'version': '17.0.1.0.0',
    'category': 'Tools',
    'summary': 'Simplified Connection Wizard for Evolution API',
    'description': """
        This module provides a simplified wizard to connect Odoo to the Evolution API.
        Features:
        - Auto-create Instance
        - Display QR Code
        - Check Connection Status
    """,
    'depends': ['base', 'web'],
    'data': [
        'security/ir.model.access.csv',
        'views/whatsapp_connector_wizard_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'OPL-1',
}
