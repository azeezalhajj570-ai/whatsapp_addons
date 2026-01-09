# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_whatsapp_composer(self):
        self.ensure_one()
        
        # Pre-fill body
        currency = self.currency_id.symbol
        amount = self.amount_total
        body = _("Here is your quotation *%s* amounting to *%s %s*.") % (self.name, amount, currency)
        
        # Get PDF
        # We try to use the 'sale.action_report_saleorder' to generate the PDF
        attachment = False
        try:
             # This is a bit complex in Odoo versions, usually we render qweb pdf.
             # Ideally one would check for existing attachment or generate new.
             # For simplicity, we just look for existing quotation PDF or generate one contextually in Composer if needed.
             # Let's try to generate it here to pass to composer.
             
            report = self.env.ref('sale.action_report_saleorder')
            if report:
                pdf_content, _ = report._render_qweb_pdf(self.id)
                attachment = self.env['ir.attachment'].create({
                    'name': f"{self.name}.pdf",
                    'type': 'binary',
                    'datas': self.env['ir.attachment']._encode_datas(pdf_content),
                    'res_model': 'sale.order',
                    'res_id': self.id,
                    'mimetype': 'application/pdf'
                })
        except Exception:
            pass
            
        ctx = dict(self.env.context or {})
        ctx.update({
            'default_body': body,
            'active_model': 'sale.order',
            'active_id': self.id,
        })
        
        if attachment:
            ctx['default_attachment_ids'] = [(4, attachment.id)]

        return {
            'name': _('Send WhatsApp'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'whatsapp_evaluation.composer',
            'target': 'new',
            'context': ctx,
        }
