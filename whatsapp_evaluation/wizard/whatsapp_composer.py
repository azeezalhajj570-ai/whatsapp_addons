# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError

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
            
            # Sale Order Specific Logic
            if result['res_model'] == 'sale.order':
                # Pre-fill body
                currency = record.currency_id.symbol
                amount = record.amount_total
                result['body'] = _("Here is your quotation *%s* amounting to *%s %s*.") % (record.name, amount, currency)
                
                # Attach PDF
                try:
                    report = self.env.ref('sale.action_report_saleorder')
                    if report:
                        pdf_content, __ = report._render_qweb_pdf(record.id)
                        attachment = self.env['ir.attachment'].create({
                            'name': f"{record.name}.pdf",
                            'type': 'binary',
                            'datas': self.env['ir.attachment']._encode_datas(pdf_content),
                            'res_model': 'sale.order',
                            'res_id': record.id,
                            'mimetype': 'application/pdf'
                        })
                        result['attachment_ids'] = [(4, attachment.id)]
                except Exception:
                    pass
                
        return result

    def action_send_whatsapp(self):
        self.ensure_one()
        
        # Create message linked to the document
        mail_message = self.env['mail.message'].create({
            'model': self.res_model,
            'res_id': self.res_id,
            'body': self.body,
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
