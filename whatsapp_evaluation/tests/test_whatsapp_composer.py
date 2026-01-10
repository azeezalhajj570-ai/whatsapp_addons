# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.whatsapp_evaluation.tests.common import WhatsAppEvaluationCommon

class TestWhatsAppComposer(WhatsAppEvaluationCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Customer', 'mobile': '+1234567890'})
        cls.sale_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'name': 'SO/FLOW/001'
        })

    def test_composer_default_get(self):
        """ Test that composer opens with correct default values """
        context = {
            'active_model': 'sale.order',
            'active_id': self.sale_order.id,
            'active_ids': [self.sale_order.id],
        }
        composer_defaults = self.env['whatsapp_evaluation.composer'].with_context(context).default_get(
            ['res_model', 'res_id', 'wa_account_id', 'mobile_number', 'body']
        )
        
        self.assertEqual(composer_defaults['res_model'], 'sale.order')
        self.assertEqual(composer_defaults['res_id'], self.sale_order.id)
        self.assertEqual(composer_defaults['wa_account_id'], self.wa_account.id)
        self.assertEqual(composer_defaults['mobile_number'], '+1234567890')

    def test_send_message_flow(self):
        """ Test sending a message via composer """
        composer = self.env['whatsapp_evaluation.composer'].create({
            'res_model': 'sale.order',
            'res_id': self.sale_order.id,
            'wa_account_id': self.wa_account.id,
            'mobile_number': '+1234567890',
            'body': 'Test Message content'
        })
        
        # Action send WhatsApp should trigger the API call (mocked in common)
        composer.action_send_whatsapp()
        
        # Check that api.send_whatsapp_text was called
        self.mock_api_instance.send_whatsapp_text.assert_called_once()
        
        # Verify message created in DB
        message = self.env['whatsapp_evaluation.message'].search([
            ('res_model', '=', 'sale.order'), 
            ('res_id', '=', self.sale_order.id)
        ], limit=1)
        
        self.assertTrue(message, "Message record should be created")
        self.assertEqual(message.body, 'Test Message content')
        self.assertEqual(message.state, 'sent')
