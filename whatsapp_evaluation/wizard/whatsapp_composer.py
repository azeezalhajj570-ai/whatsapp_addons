# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _, tools
from odoo.exceptions import UserError
import re

class WhatsAppComposer(models.TransientModel):
    _name = 'whatsapp_evaluation.composer'
    _description = 'Send WhatsApp Wizard'

    res_model = fields.Char('Document Model Name', required=True)
    res_id = fields.Integer('Document ID', required=True)
    
    phone = fields.Char(string="Phone Number", required=True)
    wa_account_id = fields.Many2one('whatsapp_evaluation.account', string="WhatsApp Account", required=True)
    
    body = fields.Text(string="Message", required=True)
    attachment_ids = fields.Many2many('ir.attachment', string="Attachments")
    
    @api.model
    def default_get(self, fields):
        result = super().default_get(fields)
        if self.env.context.get('active_model') and self.env.context.get('active_id'):
            result['res_model'] = self.env.context['active_model']
            result['res_id'] = self.env.context['active_id']
            
            record = self.env[result['res_model']].browse(result['res_id'])
            if 'mobile' in record:
                result['phone'] = record.mobile
            elif 'phone' in record:
                result['phone'] = record.phone
            elif 'partner_id' in record and record.partner_id.mobile:
                result['phone'] = record.partner_id.mobile
            elif 'partner_id' in record and record.partner_id.phone:
                result['phone'] = record.partner_id.phone
                
            # Default Account
            account = self.env['whatsapp_evaluation.account'].search([], limit=1)
            if account:
                result['wa_account_id'] = account.id
            
            # Determine Language
            lang_code = 'en'
            if result.get('res_model') == 'res.partner':
                partner = record
            elif 'partner_id' in record:
                partner = record.partner_id
            else:
                partner = False
            
            if partner and partner.lang:
                # Map Odoo lang (ar_SY) to WhatsApp lang (ar) if needed
                # For now, simplistic mapping or direct usage if key matches
                if partner.lang.startswith('ar'):
                    lang_code = 'ar'
                elif partner.lang.startswith('fr'):
                    lang_code = 'fr'
                elif partner.lang.startswith('es'):
                    lang_code = 'es'
                # Add more mappings as needed or implement robust mapping
            
            # Template logic
            template = self.env['whatsapp_evaluation.template']._find_default_for_model(result['res_model'], lang_code=lang_code)
            if template:
                var_values = template.variable_ids._get_variables_value(record)
                result['body'] = template._get_formatted_body(variable_values=var_values)
                
                # Attachment handling
                attachments = template._generate_attachment_from_report(record)
                if template.header_attachment_ids:
                     attachments |= template.header_attachment_ids
                if attachments:
                     result['attachment_ids'] = [(4, att.id) for att in attachments]

            # Fallback for Sale Order body if no template (legacy support if desired, or remove)
            if result['res_model'] == 'sale.order' and not result.get('body'):
                 currency = record.currency_id.symbol
                 amount = record.amount_total
                 result['body'] = _("Here is your quotation *%s* amounting to *%s %s*.") % (record.name, amount, currency)

        return result

    def action_send_whatsapp(self):
        self.ensure_one()
        
        # Format body for Odoo Chatter (HTML)
        # 1. Convert newlines to <br/> and linkify URLs
        body_html = tools.plaintext2html(self.body)
        
        # 2. Basic Markdown to HTML conversion
        # Format *bold*
        body_html = re.sub(r'\*([^*]+)\*', r'<b>\1</b>', body_html)
        # Format _italics_
        body_html = re.sub(r'_([^_]+)_', r'<i>\1</i>', body_html)
        
        # Create message linked to the document
        mail_message = self.env['mail.message'].create({
            'model': self.res_model,
            'res_id': self.res_id,
            'body': body_html,
            'message_type': 'comment',
            'subtype_id': self.env.ref('mail.mt_comment').id,
            'attachment_ids': [(6, 0, self.attachment_ids.ids)]
        })
        
        wa_msg = self.env['whatsapp_evaluation.message'].create({
            'body': self.body,
            'mobile_number': self.phone,
            'wa_account_id': self.wa_account_id.id,
            'mail_message_id': mail_message.id,
            'message_type': 'outbound',
            'state': 'outgoing',
            'attachment_ids': [(6, 0, self.attachment_ids.ids)]
        })
        
        wa_msg._send_message()
        
        return {'type': 'ir.actions.act_window_close'}
