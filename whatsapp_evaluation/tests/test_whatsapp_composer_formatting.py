# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.whatsapp_evaluation.tests.common import WhatsAppEvaluationCommon
from odoo import Command

class TestWhatsAppComposerFormatting(WhatsAppEvaluationCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env['res.partner'].create({'name': 'Test Partner', 'mobile': '+1234567890'})
        cls.wa_account = cls.env['whatsapp_evaluation.account'].create({'name': 'Test Account'})
        
    def test_composer_formatting(self):
        """ Test that the composer correctly formats newlines and markdown for Odoo Chatter """
        
        raw_body = "Hello World\nThis is a *bold* statement.\nAnd this is _italics_."
        
        composer = cls.env['whatsapp_evaluation.composer'].create({
            'res_model': 'res.partner',
            'res_id': cls.partner.id,
            'phone': cls.partner.mobile,
            'wa_account_id': cls.wa_account.id,
            'body': raw_body,
        })
        
        composer.action_send_whatsapp()
        
        # Check the last message on the partner
        message = cls.partner.message_ids[0]
        
        # Verify HTML formatting
        self.assertIn('Hello World<br>', message.body) # plaintext2html usually adds <br> or <br/>
        self.assertIn('<b>bold</b>', message.body)
        self.assertIn('<i>italics</i>', message.body)
        
        # Verify plain text preserved for WhatsApp message
        wa_msg = cls.env['whatsapp_evaluation.message'].search([('mail_message_id', '=', message.id)])
        self.assertEqual(wa_msg.body, raw_body)
