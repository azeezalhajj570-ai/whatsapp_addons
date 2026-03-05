# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Evolution Instance Manager Website',
    'summary': 'Website access for Evolution Instance Manager',
    'version': '1.0.0',
    'category': 'Website',
    'author': 'Azeez',
    'website': 'https://github.com/mekhlafi98',
    'license': 'OPL-1',
    'depends': [
        'website',
        'evolution_instance_manager',
    ],
    'data': [
        'views/evolution_website_views.xml',
    ],
    'installable': True,
    'application': False,
}
